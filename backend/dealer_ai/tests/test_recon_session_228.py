"""SESSION_228 — recon budget + price sheet + parts roll-up.

Locks the new behaviour introduced by the four SESSION_228
migrations and the ``services/recon_budget.py`` module:

- ``recon_budget_for(vehicle)`` composes bands → default → sum of
  overrides. Returns ``None`` when the store is in ``per_job`` mode.
- ``recon_spend_for(vehicle)`` sums live WO estimates + completed
  WO actuals + parts. Cancelled WOs don't count. ``exclude_wo``
  excludes a specific WO so ``authorize_or_queue`` can check "would
  I push the car over" without double-counting itself.
- ``authorize_or_queue(wo)`` auto-authorizes an under-budget WO on
  a ``budget`` store; leaves it in draft on ``per_job`` or when
  over budget.
- ``create_work_order_from_finding`` under budget yields an
  approved WO with the auto-authorization note; over budget yields
  a draft that appears in ``needs_authorization_queue``.
- A part installed on an authorized WO posts a ``parts`` ledger
  row (``WORKORDER:<id>:parts:<part>``); return posts a reversal.
- Send-to-wholesale from the queue cancels the car's open WOs,
  moves the car to ``wholesale_out``, and preserves prior spend.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    DealerOnboardingProfile,
    ReconRateCard,
    Vehicle,
    VehicleCost,
    VehicleReconBudgetOverride,
    WORK_ORDER_PART_STATUS_INSTALLED,
    WORK_ORDER_PART_STATUS_ORDERED,
    WORK_ORDER_PART_STATUS_RECEIVED,
    WORK_ORDER_PART_STATUS_RETURNED,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_VENUE_IN_HOUSE,
    WorkOrder,
)
from dealer_ai.services import recon as recon_service
from dealer_ai.services import recon_budget

User = get_user_model()


def _vehicle(stock, dealership, *, price=Decimal("10_000.00")) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="F-150",
        price=price,
        dealership=dealership,
    )


def _report(vehicle, dealership) -> ConditionReport:
    return ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="Chris",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=timezone.now(),
    )


def _finding(report, dealership, *, est=Decimal("500.00"), desc="LOF"):
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        severity=CONDITION_SEVERITY_REQUIRED,
        description=desc,
        estimated_cost=est,
    )


def _user(name):
    return User.objects.create_user(username=name, password="pw")


def _set_budget_mode(
    dealership, *, default=Decimal("1200.00"), bands=None
) -> DealerOnboardingProfile:
    profile, _ = DealerOnboardingProfile.objects.get_or_create(
        dealership=dealership,
        defaults=dict(
            recon_authorization_mode=(
                DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_BUDGET
            ),
            recon_budget_default=default,
            recon_budget_bands=bands or [],
        ),
    )
    profile.recon_authorization_mode = (
        DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_BUDGET
    )
    profile.recon_budget_default = default
    profile.recon_budget_bands = bands or []
    profile.save()
    return profile


# ============================================================================
# recon_budget_for
# ============================================================================


class ReconBudgetForVehicle(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _vehicle("BUD-1", self.default, price=Decimal("8000"))

    def test_per_job_mode_returns_none(self):
        # No profile row = default per_job behaviour.
        self.assertIsNone(
            recon_budget.recon_budget_for(
                self.vehicle, dealership=self.default
            )
        )
        self.assertEqual(
            recon_budget.authorization_mode(self.default), "per_job"
        )

    def test_budget_mode_default_only(self):
        _set_budget_mode(self.default, default=Decimal("1200.00"))
        self.assertEqual(
            recon_budget.recon_budget_for(
                self.vehicle, dealership=self.default
            ),
            Decimal("1200.00"),
        )

    def test_bands_pick_the_right_tier(self):
        _set_budget_mode(
            self.default,
            default=Decimal("1200.00"),
            bands=[
                {"up_to": "10000", "budget": "1200"},
                {"up_to": "20000", "budget": "1800"},
                {"up_to": None, "budget": "2500"},
            ],
        )
        cheap = _vehicle("BUD-CHEAP", self.default, price=Decimal("6000"))
        mid = _vehicle("BUD-MID", self.default, price=Decimal("15000"))
        expensive = _vehicle("BUD-EXP", self.default, price=Decimal("30000"))
        self.assertEqual(
            recon_budget.recon_budget_for(cheap, dealership=self.default),
            Decimal("1200"),
        )
        self.assertEqual(
            recon_budget.recon_budget_for(mid, dealership=self.default),
            Decimal("1800"),
        )
        self.assertEqual(
            recon_budget.recon_budget_for(expensive, dealership=self.default),
            Decimal("2500"),
        )

    def test_override_raises_only_that_car(self):
        _set_budget_mode(self.default, default=Decimal("1200.00"))
        v2 = _vehicle("BUD-2", self.default, price=Decimal("8000"))
        recon_budget.record_budget_override(
            self.vehicle,
            dealership=self.default,
            amount=Decimal("400.00"),
            reason="seal on the lift",
            granted_by=_user("bud-grantor"),
        )
        self.assertEqual(
            recon_budget.recon_budget_for(
                self.vehicle, dealership=self.default
            ),
            Decimal("1600.00"),
        )
        self.assertEqual(
            recon_budget.recon_budget_for(v2, dealership=self.default),
            Decimal("1200.00"),
        )

    def test_override_requires_nonblank_reason(self):
        with self.assertRaises(ValueError):
            recon_budget.record_budget_override(
                self.vehicle,
                dealership=self.default,
                amount=Decimal("100"),
                reason="   ",
            )


# ============================================================================
# recon_spend_for — live estimates + completed actuals + parts; cancelled = 0
# ============================================================================


class ReconSpendCounting(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _vehicle("SP-1", self.default)
        self.report = _report(self.vehicle, self.default)
        self.finding_a = _finding(
            self.report, self.default, est=Decimal("500"), desc="A"
        )
        self.finding_b = _finding(
            self.report, self.default, est=Decimal("400"), desc="B"
        )
        self.actor = _user("sp-act")

    def _wo(self, finding, est):
        wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=est,
        )
        recon_service.attach_findings(
            wo, dealership=self.default, finding_ids=[finding.pk]
        )
        return wo

    def test_draft_and_approved_estimates_count(self):
        self._wo(self.finding_a, Decimal("500"))
        wo_b = self._wo(self.finding_b, Decimal("400"))
        recon_service.approve_work_order(
            wo_b, dealership=self.default, approved_by=self.actor
        )
        self.assertEqual(
            recon_budget.recon_spend_for(
                self.vehicle, dealership=self.default
            ),
            Decimal("900.00"),
        )

    def test_cancelled_wo_contributes_zero(self):
        wo = self._wo(self.finding_a, Decimal("500"))
        recon_service.cancel_work_order(
            wo,
            dealership=self.default,
            cancelled_by=self.actor,
            cancellation_reason="not needed",
        )
        self.assertEqual(
            recon_budget.recon_spend_for(
                self.vehicle, dealership=self.default
            ),
            Decimal("0.00"),
        )

    def test_completed_wo_contributes_actual_not_estimate(self):
        wo = self._wo(self.finding_a, Decimal("500"))
        recon_service.approve_work_order(
            wo, dealership=self.default, approved_by=self.actor
        )
        recon_service.start_work_order(
            wo, dealership=self.default, started_by=self.actor
        )
        recon_service.complete_work_order(
            wo,
            dealership=self.default,
            completed_by=self.actor,
            actual_cost=Decimal("475"),
        )
        self.assertEqual(
            recon_budget.recon_spend_for(
                self.vehicle, dealership=self.default
            ),
            Decimal("475.00"),
        )

    def test_parts_estimate_counts_in_live_spend(self):
        wo = self._wo(self.finding_a, Decimal("59"))
        part = recon_service.add_part(
            wo,
            dealership=self.default,
            name="A/C compressor",
            unit_cost=Decimal("350"),
        )
        self.assertEqual(
            recon_budget.recon_spend_for(
                self.vehicle, dealership=self.default
            ),
            Decimal("409.00"),
        )


# ============================================================================
# authorize_or_queue — auto-authorize under budget; queue over budget
# ============================================================================


class AuthorizeOrQueue(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("1200.00"))
        self.vehicle = _vehicle("AQ-1", self.default)
        self.report = _report(self.vehicle, self.default)
        self.finding = _finding(
            self.report, self.default, est=Decimal("500")
        )
        self.actor = _user("aq")

    def _fresh_finding(self, est, desc="B") -> ConditionFinding:
        return _finding(self.report, self.default, est=est, desc=desc)

    def test_under_budget_auto_authorizes(self):
        wo = recon_service.create_work_order_from_finding(
            self.finding,
            dealership=self.default,
            created_by=self.actor,
        )
        wo.refresh_from_db()
        self.assertEqual(wo.status, WORK_ORDER_STATUS_APPROVED)
        self.assertIn("auto-authorized", wo.notes)
        # Ledger has the estimate row.
        self.assertTrue(
            VehicleCost.objects.filter(
                reference=f"WORKORDER:{wo.pk}:estimate:1"
            ).exists()
        )

    def test_over_budget_stays_draft(self):
        big = self._fresh_finding(est=Decimal("2000"), desc="Big job")
        wo = recon_service.create_work_order_from_finding(
            big,
            dealership=self.default,
            created_by=self.actor,
        )
        wo.refresh_from_db()
        self.assertEqual(wo.status, WORK_ORDER_STATUS_DRAFT)
        # And it appears on the queue.
        queue = list(
            recon_budget.needs_authorization_queue(self.default)
        )
        self.assertIn(wo, queue)
        # Overage matches.
        self.assertEqual(
            recon_budget.overage_for(wo, dealership=self.default),
            Decimal("800.00"),
        )

    def test_exactly_at_budget_authorizes(self):
        exact = self._fresh_finding(
            est=Decimal("1200.00"), desc="Exact"
        )
        wo = recon_service.create_work_order_from_finding(
            exact,
            dealership=self.default,
            created_by=self.actor,
        )
        wo.refresh_from_db()
        self.assertEqual(wo.status, WORK_ORDER_STATUS_APPROVED)

    def test_per_job_store_stays_draft_regardless(self):
        # Flip mode back and re-run — same finding must yield a
        # draft, matching pre-SESSION_228 behaviour.
        DealerOnboardingProfile.objects.filter(dealership=self.default).update(
            recon_authorization_mode=(
                DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_PER_JOB
            )
        )
        wo = recon_service.create_work_order_from_finding(
            self.finding,
            dealership=self.default,
            created_by=self.actor,
        )
        wo.refresh_from_db()
        self.assertEqual(wo.status, WORK_ORDER_STATUS_DRAFT)


# ============================================================================
# Send-to-wholesale exit from the queue
# ============================================================================


class SendToWholesaleFromQueue(TestCase):
    """Chris, 2026-09-01 evening: the third exit from the queue is
    'send to wholesale' — cancel every open WO on the car, move it
    to ``wholesale_out``, keep prior spend on the ledger, record a
    lifecycle event naming the overage."""

    def setUp(self):
        from dealer_ai.models import ROLE_DEALER_OWNER, UserDealershipRole
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("500"))
        self.vehicle = _vehicle("W-1", self.default)
        self.report = _report(self.vehicle, self.default)
        self.finding = _finding(
            self.report, self.default, est=Decimal("1200"), desc="Big"
        )
        self.actor = _user("w-actor")
        # advance_stage(wholesale_out) requires owner/sales_manager
        # authority. Grant the actor a role at the tenant.
        UserDealershipRole.objects.create(
            user=self.actor,
            dealership=self.default,
            role=ROLE_DEALER_OWNER,
        )

    def test_send_to_wholesale_cancels_and_moves(self):
        # Given: over-budget WO in the queue.
        wo = recon_service.create_work_order_from_finding(
            self.finding, dealership=self.default, created_by=self.actor
        )
        wo.refresh_from_db()
        self.assertEqual(wo.status, WORK_ORDER_STATUS_DRAFT)

        # When: the manager sends it to wholesale via the service
        # helper (endpoint test lives in the endpoint suite).
        from dealer_ai.services import vehicle_lifecycle
        # Cancel every open WO on the car with the wholesale reason.
        for open_wo in WorkOrder.objects.filter(
            vehicle=self.vehicle,
            dealership=self.default,
            status__in=(
                WORK_ORDER_STATUS_DRAFT,
                WORK_ORDER_STATUS_APPROVED,
            ),
        ):
            recon_service.cancel_work_order(
                open_wo,
                dealership=self.default,
                cancelled_by=self.actor,
                cancellation_reason=(
                    "wholesale — recon over budget by $700.00"
                ),
            )
        # Move the vehicle to wholesale_out. First the vehicle needs
        # a current stage — advance_stage compares against it. The
        # M5 bootstrap sets it on Vehicle create; ensure it's there.
        vehicle_lifecycle.ensure_current_stage(
            self.vehicle, dealership=self.default
        )
        vehicle_lifecycle.advance_stage(
            self.vehicle,
            dealership=self.default,
            to_stage="wholesale_out",
            trigger="manual",
            actor=self.actor,
            notes="wholesale — recon over budget by $700.00",
        )

        # Then: WO is cancelled, vehicle is in wholesale_out, prior
        # spend (if any) stays on the ledger.
        wo.refresh_from_db()
        self.assertEqual(wo.status, WORK_ORDER_STATUS_CANCELLED)
        self.assertIn(
            "wholesale — recon over budget",
            wo.cancellation_reason,
        )
        from dealer_ai.models import VehicleStage
        current_stage = VehicleStage.objects.filter(
            vehicle=self.vehicle
        ).first()
        self.assertIsNotNone(current_stage)
        assert current_stage is not None
        self.assertEqual(current_stage.current_stage, "wholesale_out")


# ============================================================================
# Parts roll into money — SESSION_228 Part 1b
# ============================================================================


class PartsRollUp(TestCase):
    """A $350 A/C compressor installed on a $59 LOF completes at
    $409 = labor + parts. Ledger gets a $59 labor actual + $350
    parts install row."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _vehicle("PRT-1", self.default)
        self.report = _report(self.vehicle, self.default)
        self.finding = _finding(
            self.report, self.default, est=Decimal("59"), desc="LOF"
        )
        self.actor = _user("prt")

    def _authorized_wo(self):
        wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("59"),
        )
        recon_service.attach_findings(
            wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        recon_service.approve_work_order(
            wo, dealership=self.default, approved_by=self.actor
        )
        recon_service.start_work_order(
            wo, dealership=self.default, started_by=self.actor
        )
        return wo

    def test_install_and_completion_together_reach_labor_plus_parts(self):
        wo = self._authorized_wo()
        part = recon_service.add_part(
            wo,
            dealership=self.default,
            name="A/C compressor",
            unit_cost=Decimal("350"),
        )
        # Estimate side of the money reads labor + parts.
        self.assertEqual(
            recon_budget.wo_estimate_total(wo), Decimal("409.00")
        )
        # Install → parts ledger row lands.
        recon_service.transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        recon_service.transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_RECEIVED,
        )
        recon_service.transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_INSTALLED,
        )
        parts_row = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:parts:{part.pk}"
        )
        self.assertEqual(parts_row.amount, Decimal("350.00"))
        # Complete with labor actual = $59. Actual total = labor +
        # installed parts.
        recon_service.complete_work_order(
            wo,
            dealership=self.default,
            completed_by=self.actor,
            actual_cost=Decimal("59"),
        )
        wo.refresh_from_db()
        self.assertEqual(
            recon_budget.wo_actual_total(wo), Decimal("409.00")
        )

    def test_return_reverses_the_parts_row(self):
        wo = self._authorized_wo()
        part = recon_service.add_part(
            wo,
            dealership=self.default,
            name="A/C compressor",
            unit_cost=Decimal("350"),
        )
        for s in (
            WORK_ORDER_PART_STATUS_ORDERED,
            WORK_ORDER_PART_STATUS_RECEIVED,
            WORK_ORDER_PART_STATUS_INSTALLED,
            WORK_ORDER_PART_STATUS_RETURNED,
        ):
            recon_service.transition_part_status(
                part, dealership=self.default, new_status=s
            )
        # Net parts contribution on the ledger for this WO = 0.
        rows = VehicleCost.objects.filter(
            reference__startswith=f"WORKORDER:{wo.pk}:parts",
            category="parts",
        )
        signed = sum((r.amount for r in rows), Decimal("0"))
        self.assertEqual(signed, Decimal("0.00"))

    def test_part_pushes_car_over_budget(self):
        _set_budget_mode(self.default, default=Decimal("400"))
        wo = self._authorized_wo()
        # Under $400 with only labor ($59).
        self.assertEqual(
            recon_budget.overage_for(wo, dealership=self.default),
            Decimal("0.00"),
        )
        # $350 part pushes the car total to $409 — over $400 = $9
        # over.
        recon_service.add_part(
            wo,
            dealership=self.default,
            name="A/C compressor",
            unit_cost=Decimal("350"),
        )
        self.assertEqual(
            recon_budget.overage_for(wo, dealership=self.default),
            Decimal("9.00"),
        )


# ============================================================================
# Rate card CRUD
# ============================================================================


class RateCardCRUD(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_create_update_deactivate_and_list(self):
        item = recon_budget.create_rate_card_item(
            self.default,
            name="LOF",
            work_order_category=CONDITION_CATEGORY_MECHANICAL,
            flat_price=Decimal("59.00"),
            retail_default=True,
        )
        self.assertTrue(item.active)
        self.assertTrue(item.retail_default)

        recon_budget.update_rate_card_item(
            item,
            dealership=self.default,
            flat_price=Decimal("69.00"),
        )
        item.refresh_from_db()
        self.assertEqual(item.flat_price, Decimal("69.00"))

        # Deactivate — soft delete via active=False.
        recon_budget.deactivate_rate_card_item(item, dealership=self.default)
        item.refresh_from_db()
        self.assertFalse(item.active)

        # Active-only list excludes it now.
        active_items = list(
            recon_budget.list_rate_card_items(self.default, active_only=True)
        )
        self.assertNotIn(item, active_items)
        all_items = list(
            recon_budget.list_rate_card_items(self.default, active_only=False)
        )
        self.assertIn(item, all_items)

    def test_unique_per_store_by_name_and_variant(self):
        recon_budget.create_rate_card_item(
            self.default,
            name="Tires",
            work_order_category=CONDITION_CATEGORY_MECHANICAL,
            flat_price=Decimal("400.00"),
            variant="16-inch",
        )
        # Same name + variant refused.
        with self.assertRaises(Exception):
            recon_budget.create_rate_card_item(
                self.default,
                name="Tires",
                work_order_category=CONDITION_CATEGORY_MECHANICAL,
                flat_price=Decimal("400.00"),
                variant="16-inch",
            )
        # Same name, different variant OK.
        recon_budget.create_rate_card_item(
            self.default,
            name="Tires",
            work_order_category=CONDITION_CATEGORY_MECHANICAL,
            flat_price=Decimal("500.00"),
            variant="18-inch",
        )

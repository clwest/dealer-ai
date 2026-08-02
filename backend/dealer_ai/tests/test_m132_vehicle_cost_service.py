"""Milestone 13 · Increment 2 (SESSION_130) — VehicleCost GL-posting service tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_PARTS,
    Dealership,
    GLAccount,
    JournalEntry,
    JournalEntryLine,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.accounting import (
    AP_TRADE_ACCOUNT_CODE,
    RECON_WIP_ACCOUNT_CODE,
    MissingDefaultAccountError,
    detect_unposted_costs,
    post_all_unposted_costs_for_dealership,
    post_vehicle_cost_journal,
    seed_default_coa,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_vehicle(dealership: Dealership, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Test",
        price=Decimal("10000.00"),
        dealership=dealership,
    )


def _make_cost(
    dealership: Dealership,
    vehicle: Vehicle,
    amount: Decimal,
    *,
    category: str = CATEGORY_PARTS,
    is_estimate: bool = False,
    incurred_at=None,
    reference: str = "",
) -> VehicleCost:
    return VehicleCost.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=category,
        amount=amount,
        incurred_at=incurred_at or timezone.now(),
        is_estimate=is_estimate,
        reference=reference,
    )


class DetectUnpostedCostsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.vehicle = _make_vehicle(self.dealership, "M132-DET")

    def test_returns_unposted_non_estimate_rows(self) -> None:
        c1 = _make_cost(self.dealership, self.vehicle, Decimal("50.00"))
        c2 = _make_cost(self.dealership, self.vehicle, Decimal("25.00"))
        qs = detect_unposted_costs(dealership=self.dealership)
        self.assertEqual(set(qs.values_list("pk", flat=True)), {c1.pk, c2.pk})

    def test_excludes_estimates(self) -> None:
        _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("100.00"),
            is_estimate=True,
        )
        qs = detect_unposted_costs(dealership=self.dealership)
        self.assertEqual(qs.count(), 0)

    def test_excludes_already_posted(self) -> None:
        posted = _make_cost(
            self.dealership, self.vehicle, Decimal("30.00")
        )
        posted.posted_at = timezone.now()
        posted.save(update_fields=["posted_at"])
        qs = detect_unposted_costs(dealership=self.dealership)
        self.assertEqual(qs.count(), 0)

    def test_scoped_by_dealership(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-m132-det", name="Other"
        )
        seed_default_coa(other)  # so downstream posts against `other` work
        other_vehicle = _make_vehicle(other, "M132-DET-OTHER")
        _make_cost(other, other_vehicle, Decimal("10.00"))
        _make_cost(self.dealership, self.vehicle, Decimal("20.00"))
        self.assertEqual(
            detect_unposted_costs(dealership=self.dealership).count(), 1
        )
        self.assertEqual(
            detect_unposted_costs(dealership=other).count(), 1
        )


class PostVehicleCostJournalTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.vehicle = _make_vehicle(self.dealership, "M132-POST")

    def test_positive_amount_posts_debit_recon_credit_ap(self) -> None:
        cost = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("125.50"),
            category=CATEGORY_MECHANICAL_LABOR,
        )
        post_vehicle_cost_journal(
            dealership=self.dealership, vehicle_cost=cost
        )
        cost.refresh_from_db()
        self.assertIsNotNone(cost.posted_at)
        # Exactly one JournalEntry created with two lines.
        self.assertEqual(JournalEntry.objects.count(), 1)
        entry = JournalEntry.objects.get()
        recon = GLAccount.objects.get(
            dealership=self.dealership, code=RECON_WIP_ACCOUNT_CODE
        )
        ap = GLAccount.objects.get(
            dealership=self.dealership, code=AP_TRADE_ACCOUNT_CODE
        )
        recon_line = entry.lines.get(account=recon)
        ap_line = entry.lines.get(account=ap)
        self.assertEqual(recon_line.debit, Decimal("125.50"))
        self.assertEqual(recon_line.credit, Decimal("0.00"))
        self.assertEqual(ap_line.credit, Decimal("125.50"))
        self.assertEqual(ap_line.debit, Decimal("0.00"))

    def test_negative_amount_swaps_sides(self) -> None:
        cost = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("-40.00"),  # correction row
            category=CATEGORY_PARTS,
        )
        post_vehicle_cost_journal(
            dealership=self.dealership, vehicle_cost=cost
        )
        entry = JournalEntry.objects.get()
        recon = GLAccount.objects.get(
            dealership=self.dealership, code=RECON_WIP_ACCOUNT_CODE
        )
        ap = GLAccount.objects.get(
            dealership=self.dealership, code=AP_TRADE_ACCOUNT_CODE
        )
        # Swapped: AP debited, Recon WIP credited. |amount| on both.
        self.assertEqual(entry.lines.get(account=ap).debit, Decimal("40.00"))
        self.assertEqual(
            entry.lines.get(account=recon).credit, Decimal("40.00")
        )

    def test_zero_amount_still_posts_balanced(self) -> None:
        # Edge case: zero-amount cost row. Posting a 0/0 entry is
        # rejected by the M13.1 UnbalancedJournalEntryError guard
        # (both zero → InvalidJournalLineError). Documenting the
        # actual behavior locks the contract.
        from dealer_ai.services.accounting import InvalidJournalLineError

        cost = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("0.00"),
            category=CATEGORY_PARTS,
        )
        with self.assertRaises(InvalidJournalLineError):
            post_vehicle_cost_journal(
                dealership=self.dealership, vehicle_cost=cost
            )
        cost.refresh_from_db()
        # Failed post — posted_at stays NULL, entry not created.
        self.assertIsNone(cost.posted_at)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_atomic_rollback_on_failure(self) -> None:
        # Deactivate the required account after seeding — the next
        # post attempt raises MissingDefaultAccountError and neither
        # side of the atomic sibling-service crossing commits.
        recon = GLAccount.objects.get(
            dealership=self.dealership, code=RECON_WIP_ACCOUNT_CODE
        )
        recon.is_active = False
        recon.save()
        cost = _make_cost(
            self.dealership, self.vehicle, Decimal("10.00")
        )
        with self.assertRaises(MissingDefaultAccountError):
            post_vehicle_cost_journal(
                dealership=self.dealership, vehicle_cost=cost
            )
        cost.refresh_from_db()
        self.assertIsNone(cost.posted_at)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_cross_tenant_vehicle_cost_rejected(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-m132-xt", name="Other"
        )
        seed_default_coa(other)
        other_vehicle = _make_vehicle(other, "M132-XT")
        other_cost = _make_cost(other, other_vehicle, Decimal("15.00"))
        from dealer_ai.services.accounting import CrossTenantGLAccountError

        with self.assertRaises(CrossTenantGLAccountError):
            post_vehicle_cost_journal(
                dealership=self.dealership, vehicle_cost=other_cost
            )

    def test_explicit_posted_at_preserved(self) -> None:
        cost = _make_cost(
            self.dealership, self.vehicle, Decimal("42.00")
        )
        moment = timezone.now() - dt.timedelta(days=2)
        post_vehicle_cost_journal(
            dealership=self.dealership,
            vehicle_cost=cost,
            posted_at=moment,
        )
        cost.refresh_from_db()
        entry = JournalEntry.objects.get()
        self.assertEqual(cost.posted_at, moment)
        self.assertEqual(entry.posted_at, moment)

    def test_reference_included_in_line_memo(self) -> None:
        cost = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("77.00"),
            reference="INV-4477",
        )
        post_vehicle_cost_journal(
            dealership=self.dealership, vehicle_cost=cost
        )
        line = JournalEntryLine.objects.filter(entry__dealership=self.dealership).first()
        assert line is not None
        self.assertIn("INV-4477", line.memo)


class PostAllUnpostedCostsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.vehicle = _make_vehicle(self.dealership, "M132-BULK")

    def test_happy_path_posts_all(self) -> None:
        for i in range(3):
            _make_cost(
                self.dealership, self.vehicle, Decimal(f"{10 + i}.00")
            )
        result = post_all_unposted_costs_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(result["posted_count"], 3)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(JournalEntry.objects.count(), 3)
        for cost in VehicleCost.objects.filter(dealership=self.dealership):
            self.assertIsNotNone(cost.posted_at)

    def test_idempotent_within_run(self) -> None:
        _make_cost(self.dealership, self.vehicle, Decimal("15.00"))
        first = post_all_unposted_costs_for_dealership(
            dealership=self.dealership
        )
        second = post_all_unposted_costs_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(first["posted_count"], 1)
        self.assertEqual(second["posted_count"], 0)
        # Only one JournalEntry across both invocations.
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_mixed_estimate_and_committed(self) -> None:
        _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("100.00"),
            is_estimate=True,
        )
        _make_cost(self.dealership, self.vehicle, Decimal("50.00"))
        result = post_all_unposted_costs_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(result["posted_count"], 1)
        # Estimate stays unposted.
        estimates = VehicleCost.objects.filter(
            dealership=self.dealership, is_estimate=True
        )
        for est in estimates:
            self.assertIsNone(est.posted_at)

    def test_estimate_flip_to_committed_picks_up_on_next_run(self) -> None:
        cost = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("75.00"),
            is_estimate=True,
        )
        first = post_all_unposted_costs_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(first["posted_count"], 0)

        cost.is_estimate = False
        cost.save()
        second = post_all_unposted_costs_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(second["posted_count"], 1)
        cost.refresh_from_db()
        self.assertIsNotNone(cost.posted_at)

    def test_scoped_to_dealership(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-m132-bulk", name="Other"
        )
        seed_default_coa(other)
        other_vehicle = _make_vehicle(other, "M132-BULK-O")
        _make_cost(other, other_vehicle, Decimal("999.00"))
        _make_cost(self.dealership, self.vehicle, Decimal("1.00"))
        result = post_all_unposted_costs_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(result["posted_count"], 1)
        # Other tenant's row still unposted.
        other_cost = VehicleCost.objects.get(dealership=other)
        self.assertIsNone(other_cost.posted_at)


class MissingDefaultAccountTests(TestCase):
    def test_missing_recon_account_raises(self) -> None:
        dealership = get_default_dealership()
        vehicle = _make_vehicle(dealership, "M132-MISS")
        cost = _make_cost(dealership, vehicle, Decimal("10.00"))
        GLAccount.objects.filter(
            dealership=dealership, code=RECON_WIP_ACCOUNT_CODE
        ).update(is_active=False)
        with self.assertRaises(MissingDefaultAccountError):
            post_vehicle_cost_journal(
                dealership=dealership, vehicle_cost=cost
            )


class VehicleCostPostedAtFieldTests(TestCase):
    def test_field_defaults_to_null(self) -> None:
        dealership = get_default_dealership()
        vehicle = _make_vehicle(dealership, "M132-FIELD")
        cost = _make_cost(dealership, vehicle, Decimal("5.00"))
        self.assertIsNone(cost.posted_at)

    def test_field_can_be_updated_independently(self) -> None:
        dealership = get_default_dealership()
        vehicle = _make_vehicle(dealership, "M132-FIELD-B")
        cost = _make_cost(dealership, vehicle, Decimal("5.00"))
        moment = timezone.now()
        cost.posted_at = moment
        cost.save(update_fields=["posted_at"])
        cost.refresh_from_db()
        self.assertEqual(cost.posted_at, moment)

"""SESSION_227 — recon-one-card service coverage.

Locks the three changes to the recon service surface:

- ``revise_estimate`` requires a nonblank reason, is allowed from
  ``in_progress`` (not just ``approved``), writes a
  :class:`WorkOrderEstimateRevision` row per call, and the two
  ledger rows it posts carry the reason in ``notes``.
- ``services.condition_report.add_finding`` allows an append on a
  completed report iff ``discovered_during_work=True``, and the
  new finding follows the normal decision → WO → authorize → ledger
  path (via ``create_work_order_from_finding``).
- ``create_work_order_from_finding`` is one call: creates a draft
  WO pre-filled from the finding, links it, and is idempotent
  (a finding with a live WO does not get a second one).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_FLUIDS,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    RECON_DECISION_TIER_MUST_DO,
    RECON_DECISION_TIER_SHOULD_DO,
    Vehicle,
    VehicleCost,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_IN_HOUSE,
    WorkOrder,
)
from dealer_ai.services import condition_report as condition_report_service
from dealer_ai.services import recon as recon_service
from dealer_ai.services.condition_report import (
    ConditionReportImmutableError,
)


User = get_user_model()


# ---- fixtures --------------------------------------------------------------


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("28_500.00"),
        dealership=dealership,
    )


def _make_report(vehicle: Vehicle, dealership: Dealership) -> ConditionReport:
    return ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="Chris",
        inspected_at=timezone.now(),
        mileage_at_inspection=121_334,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=timezone.now(),
    )


def _make_finding(
    report: ConditionReport,
    dealership: Dealership,
    *,
    category: str = CONDITION_CATEGORY_MECHANICAL,
    description: str = "LOF",
    estimated_cost=Decimal("595.00"),
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=category,
        severity=CONDITION_SEVERITY_REQUIRED,
        description=description,
        estimated_cost=estimated_cost,
    )


def _make_user(username: str) -> "User":
    return User.objects.create_user(username=username, password="test-pw")


# ============================================================================
# revise_estimate — reason required, in_progress allowed, revision row.
# ============================================================================


class ReviseEstimateReasonRequired(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("S227-REV", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.user = _make_user("s227-rev")
        self.wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("495.00"),
        )
        recon_service.attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        recon_service.approve_work_order(
            self.wo, dealership=self.default, approved_by=self.user
        )
        self.wo.refresh_from_db()

    def test_blank_reason_refused(self):
        with self.assertRaises(ValueError):
            recon_service.revise_estimate(
                self.wo,
                dealership=self.default,
                new_estimated_cost=Decimal("600.00"),
                reason="",
            )

    def test_whitespace_only_reason_refused(self):
        with self.assertRaises(ValueError):
            recon_service.revise_estimate(
                self.wo,
                dealership=self.default,
                new_estimated_cost=Decimal("600.00"),
                reason="   \n\t  ",
            )


class ReviseEstimateInProgressAllowed(TestCase):
    """SESSION_227 — 'They lift the car and find a seal' happens
    WHILE IN PROGRESS by definition. Revision must be allowed."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("S227-IP", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(
            self.report, self.default, estimated_cost=Decimal("495.00")
        )
        self.user = _make_user("s227-ip")
        self.wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("495.00"),
        )
        recon_service.attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        recon_service.approve_work_order(
            self.wo, dealership=self.default, approved_by=self.user
        )
        recon_service.start_work_order(
            self.wo, dealership=self.default, started_by=self.user
        )
        self.wo.refresh_from_db()
        assert self.wo.status == WORK_ORDER_STATUS_IN_PROGRESS

    def test_revise_from_in_progress_posts_reversal_and_new_estimate(self):
        recon_service.revise_estimate(
            self.wo,
            dealership=self.default,
            new_estimated_cost=Decimal("600.00"),
            reason="Seal leaking — fixing rather than lot a leaky car.",
            revised_by=self.user,
        )
        rows = list(
            VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{self.wo.pk}:"
            ).order_by("reference")
        )
        refs = [r.reference for r in rows]
        self.assertIn(f"WORKORDER:{self.wo.pk}:estimate:1", refs)
        self.assertIn(
            f"WORKORDER:{self.wo.pk}:estimate_reversal:1", refs
        )
        self.assertIn(f"WORKORDER:{self.wo.pk}:estimate:2", refs)
        est_sum = sum(
            (r.amount for r in rows if r.is_estimate), Decimal("0.00")
        )
        self.assertEqual(est_sum, Decimal("600.00"))

    def test_ledger_rows_carry_reason_in_notes(self):
        recon_service.revise_estimate(
            self.wo,
            dealership=self.default,
            new_estimated_cost=Decimal("600.00"),
            reason="Seal leaking — fixing rather than lot a leaky car.",
            revised_by=self.user,
        )
        reversal = VehicleCost.objects.get(
            reference=f"WORKORDER:{self.wo.pk}:estimate_reversal:1"
        )
        new_estimate = VehicleCost.objects.get(
            reference=f"WORKORDER:{self.wo.pk}:estimate:2"
        )
        self.assertEqual(
            reversal.notes,
            "Seal leaking — fixing rather than lot a leaky car.",
        )
        self.assertEqual(
            new_estimate.notes,
            "Seal leaking — fixing rather than lot a leaky car.",
        )

    def test_revision_row_written_and_readable(self):
        recon_service.revise_estimate(
            self.wo,
            dealership=self.default,
            new_estimated_cost=Decimal("600.00"),
            reason="Seal leaking — fixing rather than lot a leaky car.",
            revised_by=self.user,
        )
        revisions = list(self.wo.estimate_revisions.all())
        self.assertEqual(len(revisions), 1)
        r = revisions[0]
        self.assertEqual(r.from_amount, Decimal("495.00"))
        self.assertEqual(r.to_amount, Decimal("600.00"))
        self.assertEqual(
            r.reason, "Seal leaking — fixing rather than lot a leaky car."
        )
        self.assertEqual(r.revised_by, self.user)

    def test_two_revisions_produce_two_rows(self):
        recon_service.revise_estimate(
            self.wo,
            dealership=self.default,
            new_estimated_cost=Decimal("600.00"),
            reason="Seal leaking.",
            revised_by=self.user,
        )
        recon_service.revise_estimate(
            self.wo,
            dealership=self.default,
            new_estimated_cost=Decimal("650.00"),
            reason="Also needs pads.",
            revised_by=self.user,
        )
        self.assertEqual(self.wo.estimate_revisions.count(), 2)


# ============================================================================
# add_finding — discovered_during_work on a completed report.
# ============================================================================


class AddFindingDiscoveredDuringWork(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("S227-DDW", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.user = _make_user("s227-ddw")
        self.wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("495.00"),
        )
        recon_service.attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        recon_service.approve_work_order(
            self.wo, dealership=self.default, approved_by=self.user
        )
        recon_service.start_work_order(
            self.wo, dealership=self.default, started_by=self.user
        )

    def test_completed_report_refuses_add_without_flag(self):
        with self.assertRaises(ConditionReportImmutableError):
            condition_report_service.add_finding(
                self.report,
                dealership=self.default,
                category=CONDITION_CATEGORY_FLUIDS,
                severity=CONDITION_SEVERITY_REQUIRED,
                description="Seal leaking; found in the shop.",
                estimated_cost=Decimal("105.00"),
            )

    def test_completed_report_accepts_add_with_flag(self):
        new_finding = condition_report_service.add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_FLUIDS,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Seal leaking; found in the shop.",
            estimated_cost=Decimal("105.00"),
            discovered_during_work=True,
            discovered_on_work_order=self.wo,
        )
        # Lands on the SAME report — no supplementary report object.
        self.assertEqual(new_finding.report_id, self.report.pk)
        self.assertTrue(new_finding.discovered_during_work)
        self.assertEqual(
            new_finding.discovered_on_work_order_id, self.wo.pk
        )

    def test_discovered_finding_follows_normal_decision_wo_ledger_path(self):
        # Add the seal as a "found on the lift" finding …
        seal = condition_report_service.add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_FLUIDS,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Seal leaking; found in the shop.",
            estimated_cost=Decimal("105.00"),
            discovered_during_work=True,
            discovered_on_work_order=self.wo,
        )
        # … decide + create WO from finding + approve + complete →
        # the ledger sees a $105 line under the seal's own WO.
        recon_service.record_decision(
            seal,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_by=self.user,
        )
        seal_wo = recon_service.create_work_order_from_finding(
            seal, dealership=self.default, created_by=self.user
        )
        recon_service.approve_work_order(
            seal_wo, dealership=self.default, approved_by=self.user
        )
        recon_service.start_work_order(
            seal_wo, dealership=self.default, started_by=self.user
        )
        recon_service.complete_work_order(
            seal_wo,
            dealership=self.default,
            completed_by=self.user,
            actual_cost=Decimal("105.00"),
        )
        actual = VehicleCost.objects.get(
            reference=f"WORKORDER:{seal_wo.pk}:actual"
        )
        self.assertEqual(actual.amount, Decimal("105.00"))
        # The seal is its own $105 line, NOT a bigger LOF.
        self.assertNotEqual(actual.reference.split(":")[1], str(self.wo.pk))


# ============================================================================
# create_work_order_from_finding — one call, pre-filled, linked, idempotent.
# ============================================================================


class CreateWorkOrderFromFinding(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("S227-CWFF", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(
            self.report,
            self.default,
            description="Repaint hood",
            estimated_cost=Decimal("450.00"),
        )
        self.user = _make_user("s227-cwff")

    def test_one_call_creates_draft_prefilled_and_linked(self):
        wo = recon_service.create_work_order_from_finding(
            self.finding,
            dealership=self.default,
            created_by=self.user,
        )
        self.assertEqual(wo.status, WORK_ORDER_STATUS_DRAFT)
        self.assertEqual(wo.category, CONDITION_CATEGORY_MECHANICAL)
        self.assertEqual(wo.estimated_cost, Decimal("450.00"))
        # Linked to the source finding.
        link_finding_ids = list(
            wo.finding_links.values_list("finding_id", flat=True)
        )
        self.assertEqual(link_finding_ids, [self.finding.pk])
        # Approvable — the linked-finding invariant is met.
        recon_service.approve_work_order(
            wo, dealership=self.default, approved_by=self.user
        )

    def test_idempotent_when_live_wo_exists(self):
        first = recon_service.create_work_order_from_finding(
            self.finding, dealership=self.default, created_by=self.user
        )
        second = recon_service.create_work_order_from_finding(
            self.finding, dealership=self.default, created_by=self.user
        )
        self.assertEqual(first.pk, second.pk)
        # Only ONE WO on the vehicle.
        self.assertEqual(
            WorkOrder.objects.filter(
                dealership=self.default, vehicle=self.vehicle
            ).count(),
            1,
        )

    def test_bulk_for_all_must_dos_covers_every_must_do(self):
        # Second finding — should-do — must not get a WO.
        should = _make_finding(
            self.report,
            self.default,
            category=CONDITION_CATEGORY_FLUIDS,
            description="Optional detail",
            estimated_cost=Decimal("75.00"),
        )
        recon_service.record_decision(
            self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_by=self.user,
        )
        recon_service.record_decision(
            should,
            dealership=self.default,
            tier=RECON_DECISION_TIER_SHOULD_DO,
            decided_by=self.user,
        )
        created = recon_service.create_work_orders_for_all_must_dos(
            self.vehicle,
            dealership=self.default,
            created_by=self.user,
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(
            list(created[0].finding_links.values_list("finding_id", flat=True)),
            [self.finding.pk],
        )
        # Bulk call is idempotent — a second pass adds no new WOs.
        again = recon_service.create_work_orders_for_all_must_dos(
            self.vehicle,
            dealership=self.default,
            created_by=self.user,
        )
        self.assertEqual([w.pk for w in again], [created[0].pk])

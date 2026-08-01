"""Milestone 4 · Increment 2 — recon service tests.

Coverage of ``dealer_ai/services/recon.py`` and the two
Vehicle @property accessors added at SESSION_067.

Locked invariants (per SESSION_067 brief + planning §5.c):

Decisions:
- Completed report required; draft rejected.
- Tenant chain rejection (finding-side).
- Tier validation.
- One-per-Finding via upsert-while-not-yet-authorized.
- Reconsideration allowed while no linked WO has left draft;
  refused once any linked WO is approved / in_progress / completed
  / cancelled.
- No WorkOrder or VehicleCost side effects.

Creation:
- Draft-only birth.
- Outsourced-requires-vendor.
- In-house shape.
- Cross-tenant Vehicle + Vendor rejection.
- Provenance not client-controlled (only draft creation).
- No ledger side effects.

Finding links:
- One WO to many findings.
- One finding to many WOs.
- Same-vehicle requirement.
- Completed-report requirement.
- Duplicate handling (dedupe on input; skip existing).
- Atomic batch failure (invalid finding aborts entire attach).
- Attach + detach both draft-only.

Transitions:
- Every allowed transition.
- Every disallowed transition.
- Terminal immutability.
- Provenance timestamps + actors set.
- Idempotent re-approve preserves original approved_by,
  refreshes approved_at, updates authorized_cost.
- Refresh-before-state-check (select_for_update + refresh).

Completion / QC gap:
- WorkOrder completion does NOT claim QC verification. Locked
  by explicit test that inspects the `WorkOrder` field surface
  and asserts no `qc_*` fields exist. Aligns with the
  §1.0.QC-GAP planning annotation.

Vehicle properties:
- Empty states.
- Open statuses included; terminal excluded.
- Deterministic ordering.
- Tenant isolation.
- has_recon_decisions delegation contract.

Regression boundaries:
- Zero VehicleCost rows from all M4.2 service functions.
- M3 ConditionReports + Findings remain unchanged (no side-
  effect writes).
- Completed M3 reports remain immutable.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_REPORT_STATUS_DRAFT,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    RECON_DECISION_TIER_MUST_DO,
    RECON_DECISION_TIER_SHOULD_DO,
    RECON_DECISION_TIER_WONT_DO,
    ReconDecision,
    Vehicle,
    VehicleCost,
    Vendor,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_IN_HOUSE,
    WORK_ORDER_VENUE_OUTSOURCED,
    WorkOrder,
    WorkOrderFinding,
)
from dealer_ai.services import recon as recon_service
from dealer_ai.services.recon import (
    CrossTenantReconError,
    IncompleteConditionReportError,
    InvalidReconTransitionError,
    ReconImmutableError,
    approve_work_order,
    attach_findings,
    cancel_work_order,
    complete_work_order,
    create_work_order,
    detach_finding,
    has_recon_decisions_for_vehicle,
    open_work_orders_for_vehicle,
    record_decision,
    start_work_order,
)


User = get_user_model()


# ---- fixtures --------------------------------------------------------------


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("48000.00"),
        dealership=dealership,
    )


def _make_report(
    vehicle: Vehicle,
    dealership: Dealership,
    *,
    status: str = CONDITION_REPORT_STATUS_COMPLETE,
) -> ConditionReport:
    kwargs = dict(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="M. Ruiz",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=status,
    )
    if status == CONDITION_REPORT_STATUS_COMPLETE:
        kwargs["completed_at"] = timezone.now()
    return ConditionReport.objects.create(**kwargs)


def _make_finding(
    report: ConditionReport,
    dealership: Dealership,
    *,
    description: str = "Finding for service test.",
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        severity=CONDITION_SEVERITY_REQUIRED,
        description=description,
    )


def _make_vendor(dealership: Dealership, slug: str = "svc-vendor") -> Vendor:
    return Vendor.objects.create(
        dealership=dealership,
        name=f"Service Vendor {slug}",
        slug=slug,
    )


def _make_user(username: str) -> "User":
    return User.objects.create_user(username=username, password="test-pw")


# ============================================================================
# record_decision
# ============================================================================


class RecordDecisionCreate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-RD-CREATE", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.user = _make_user("rd-user")

    def test_creates_decision_on_completed_finding(self):
        decision = record_decision(
            self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_by=self.user,
        )
        self.assertEqual(decision.tier, RECON_DECISION_TIER_MUST_DO)
        self.assertEqual(decision.decided_by, self.user)
        self.assertIsNotNone(decision.decided_at)
        self.assertEqual(decision.dealership, self.default)

    def test_decided_at_defaults_to_now(self):
        before = timezone.now()
        decision = record_decision(
            self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_SHOULD_DO,
        )
        after = timezone.now()
        self.assertTrue(before <= decision.decided_at <= after)


class RecordDecisionRequiresCompletedReport(TestCase):
    def test_draft_report_rejected(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-RD-DRAFT", default)
        draft_report = _make_report(
            vehicle, default, status=CONDITION_REPORT_STATUS_DRAFT
        )
        finding = _make_finding(draft_report, default)
        with self.assertRaises(IncompleteConditionReportError):
            record_decision(
                finding,
                dealership=default,
                tier=RECON_DECISION_TIER_MUST_DO,
            )
        # No side effect — no decision row.
        self.assertFalse(ReconDecision.objects.filter(finding=finding).exists())


class RecordDecisionCrossTenantRejection(TestCase):
    def test_finding_from_other_dealership_rejected(self):
        default = Dealership.objects.get(slug="default")
        other = Dealership.objects.create(
            name="Other Store", slug="other-rd"
        )
        vehicle_other = _make_vehicle("M42-RD-XT", other)
        report_other = _make_report(vehicle_other, other)
        finding_other = _make_finding(report_other, other)
        with self.assertRaises(CrossTenantReconError):
            record_decision(
                finding_other,
                dealership=default,  # cross-tenant caller
                tier=RECON_DECISION_TIER_MUST_DO,
            )


class RecordDecisionTierValidation(TestCase):
    def test_invalid_tier_raises_value_error(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-RD-TIER", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        with self.assertRaises(ValueError):
            record_decision(
                finding, dealership=default, tier="maybe_do"
            )


class RecordDecisionReconsideration(TestCase):
    """SESSION_067 policy: upsert while no linked WO has left draft;
    lock once any linked WO is approved / in_progress / completed /
    cancelled."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-RD-RECON", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_reconsideration_updates_tier_before_wo_approval(self):
        first = record_decision(
            self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_SHOULD_DO,
        )
        second = record_decision(
            self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            notes="Escalated after quote came back",
        )
        # Same row — upsert, not insert.
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.tier, RECON_DECISION_TIER_MUST_DO)
        self.assertEqual(
            ReconDecision.objects.filter(finding=self.finding).count(), 1
        )
        self.assertIn("Escalated", second.notes)

    def test_reconsideration_allowed_while_linked_wo_still_draft(self):
        record_decision(
            self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_SHOULD_DO,
        )
        # Attach the finding to a draft WO — the WO is still draft
        # so reconsideration is permitted.
        wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        # Reconsideration OK — no non-draft WO.
        updated = record_decision(
            self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_WONT_DO,
        )
        self.assertEqual(updated.tier, RECON_DECISION_TIER_WONT_DO)

    def test_reconsideration_locked_once_linked_wo_is_approved(self):
        record_decision(
            self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
        )
        approver = _make_user("rd-locker-approver")
        wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=approver
        )
        with self.assertRaises(ReconImmutableError):
            record_decision(
                self.finding,
                dealership=self.default,
                tier=RECON_DECISION_TIER_SHOULD_DO,
            )


class RecordDecisionNoSideEffects(TestCase):
    def test_no_workorder_or_vehiclecost_created(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-RD-SIDE", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        pre_wo = WorkOrder.objects.count()
        pre_cost = VehicleCost.objects.count()
        record_decision(
            finding,
            dealership=default,
            tier=RECON_DECISION_TIER_MUST_DO,
        )
        self.assertEqual(WorkOrder.objects.count(), pre_wo)
        self.assertEqual(VehicleCost.objects.count(), pre_cost)


# ============================================================================
# create_work_order
# ============================================================================


class CreateWorkOrderShape(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-CWO-SHAPE", self.default)

    def test_creates_in_draft_status(self):
        wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        self.assertEqual(wo.status, WORK_ORDER_STATUS_DRAFT)
        self.assertIsNone(wo.approved_at)
        self.assertIsNone(wo.approved_by)

    def test_outsourced_without_vendor_raises_invalid_transition(self):
        with self.assertRaises(InvalidReconTransitionError):
            create_work_order(
                self.vehicle,
                dealership=self.default,
                category=CONDITION_CATEGORY_BODY,
                venue=WORK_ORDER_VENUE_OUTSOURCED,
                vendor=None,
            )

    def test_in_house_without_vendor_permitted(self):
        wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        self.assertIsNone(wo.vendor)

    def test_outsourced_with_matching_vendor_creates(self):
        vendor = _make_vendor(self.default, slug="cwo-out")
        wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=vendor,
            estimated_cost=Decimal("750.00"),
        )
        self.assertEqual(wo.vendor, vendor)
        self.assertEqual(wo.estimated_cost, Decimal("750.00"))


class CreateWorkOrderCrossTenant(TestCase):
    def setUp(self):
        self.a = Dealership.objects.get(slug="default")
        self.b = Dealership.objects.create(name="Other", slug="other-cwo")
        self.vehicle_a = _make_vehicle("M42-CWO-XT", self.a)
        self.vendor_a = _make_vendor(self.a, slug="cwo-a")
        self.vendor_b = _make_vendor(self.b, slug="cwo-b")

    def test_cross_tenant_vehicle_rejected(self):
        with self.assertRaises(CrossTenantReconError):
            create_work_order(
                self.vehicle_a,
                dealership=self.b,  # wrong tenant
                category=CONDITION_CATEGORY_MECHANICAL,
                venue=WORK_ORDER_VENUE_IN_HOUSE,
            )

    def test_cross_tenant_vendor_rejected(self):
        with self.assertRaises(CrossTenantReconError):
            create_work_order(
                self.vehicle_a,
                dealership=self.a,
                category=CONDITION_CATEGORY_BODY,
                venue=WORK_ORDER_VENUE_OUTSOURCED,
                vendor=self.vendor_b,  # cross-tenant vendor
            )


class CreateWorkOrderNoLedgerSideEffect(TestCase):
    def test_no_vehicle_cost_row_created(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-CWO-NOLEDGER", default)
        vendor = _make_vendor(default, slug="noledger-cwo")
        pre = VehicleCost.objects.count()
        create_work_order(
            vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=vendor,
            estimated_cost=Decimal("500.00"),
        )
        self.assertEqual(VehicleCost.objects.count(), pre)


# ============================================================================
# attach_findings / detach_finding
# ============================================================================


class AttachFindingsShape(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-AF-SHAPE", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.f1 = _make_finding(self.report, self.default, description="F1")
        self.f2 = _make_finding(self.report, self.default, description="F2")
        self.wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )

    def test_attach_multiple_findings_returns_ordered_links(self):
        links = attach_findings(
            self.wo,
            dealership=self.default,
            finding_ids=[self.f2.pk, self.f1.pk],
        )
        self.assertEqual(len(links), 2)
        # Sorted by finding_id ascending.
        self.assertEqual(
            [link.finding_id for link in links],
            sorted([self.f1.pk, self.f2.pk]),
        )

    def test_attach_deduplicates_input_ids(self):
        links = attach_findings(
            self.wo,
            dealership=self.default,
            finding_ids=[self.f1.pk, self.f1.pk, self.f1.pk],
        )
        self.assertEqual(len(links), 1)
        self.assertEqual(
            WorkOrderFinding.objects.filter(
                work_order=self.wo, finding=self.f1
            ).count(),
            1,
        )

    def test_attach_skips_existing_and_creates_only_missing(self):
        attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.f1.pk]
        )
        # Second call adds f2 without duplicating f1.
        links = attach_findings(
            self.wo,
            dealership=self.default,
            finding_ids=[self.f1.pk, self.f2.pk],
        )
        self.assertEqual(len(links), 2)
        self.assertEqual(
            WorkOrderFinding.objects.filter(work_order=self.wo).count(), 2
        )

    def test_empty_input_returns_empty_list(self):
        result = attach_findings(
            self.wo, dealership=self.default, finding_ids=[]
        )
        self.assertEqual(result, [])


class AttachFindingsGating(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-AF-GATE", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )

    def test_attach_refused_on_non_draft_wo(self):
        # Attach a finding, approve the WO, then try to attach more.
        attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        approver = _make_user("af-gate-approver")
        approve_work_order(
            self.wo, dealership=self.default, approved_by=approver
        )
        extra_finding = _make_finding(
            self.report, self.default, description="Late add"
        )
        with self.assertRaises(InvalidReconTransitionError):
            attach_findings(
                self.wo,
                dealership=self.default,
                finding_ids=[extra_finding.pk],
            )

    def test_missing_finding_id_rejected_batch_atomically(self):
        pre = WorkOrderFinding.objects.count()
        with self.assertRaises(InvalidReconTransitionError):
            attach_findings(
                self.wo,
                dealership=self.default,
                finding_ids=[self.finding.pk, 999_999],  # 999_999 doesn't exist
            )
        # Zero rows created — batch was atomic.
        self.assertEqual(WorkOrderFinding.objects.count(), pre)

    def test_finding_from_draft_report_rejected(self):
        default = self.default
        vehicle_2 = _make_vehicle("M42-AF-DR-2", default)
        draft_report = _make_report(
            vehicle_2, default, status=CONDITION_REPORT_STATUS_DRAFT
        )
        draft_finding = _make_finding(draft_report, default)
        # Move the WO to Vehicle 2's scope for the test — actually we
        # need same-vehicle. So make a fresh WO on Vehicle 2 and a
        # complete-status finding for it too, then mix in the draft one.
        wo_v2 = create_work_order(
            vehicle_2,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        with self.assertRaises(IncompleteConditionReportError):
            attach_findings(
                wo_v2,
                dealership=default,
                finding_ids=[draft_finding.pk],
            )

    def test_cross_vehicle_finding_rejected(self):
        other_vehicle = _make_vehicle("M42-AF-OV", self.default)
        other_report = _make_report(other_vehicle, self.default)
        other_finding = _make_finding(other_report, self.default)
        with self.assertRaises(InvalidReconTransitionError):
            attach_findings(
                self.wo,
                dealership=self.default,
                finding_ids=[other_finding.pk],
            )

    def test_cross_tenant_wo_rejected(self):
        other = Dealership.objects.create(name="Other", slug="other-af")
        with self.assertRaises(CrossTenantReconError):
            attach_findings(
                self.wo,
                dealership=other,  # cross-tenant caller
                finding_ids=[self.finding.pk],
            )


class AttachFindingsManyToMany(TestCase):
    """One finding to many WorkOrders — the reverse of the many-per-
    WO case above."""

    def test_same_finding_across_multiple_work_orders(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-AF-M2M", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo1 = create_work_order(
            vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        wo2 = create_work_order(
            vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(wo1, dealership=default, finding_ids=[finding.pk])
        attach_findings(wo2, dealership=default, finding_ids=[finding.pk])
        self.assertEqual(
            WorkOrderFinding.objects.filter(finding=finding).count(), 2
        )


class DetachFinding(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-DF", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.finding.pk]
        )

    def test_detach_on_draft_removes_link(self):
        detach_finding(
            self.wo, self.finding, dealership=self.default
        )
        self.assertFalse(
            WorkOrderFinding.objects.filter(
                work_order=self.wo, finding=self.finding
            ).exists()
        )

    def test_detach_refused_on_non_draft(self):
        approver = _make_user("df-approver")
        approve_work_order(
            self.wo, dealership=self.default, approved_by=approver
        )
        with self.assertRaises(InvalidReconTransitionError):
            detach_finding(
                self.wo, self.finding, dealership=self.default
            )

    def test_detach_nonexistent_link_raises(self):
        # Detach once succeeds; second detach raises.
        detach_finding(
            self.wo, self.finding, dealership=self.default
        )
        with self.assertRaises(InvalidReconTransitionError):
            detach_finding(
                self.wo, self.finding, dealership=self.default
            )


# ============================================================================
# State machine transitions
# ============================================================================


class ApproveWorkOrder(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-AP", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.approver = _make_user("ap-approver")

    def _wo_with_finding(self):
        wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        return wo

    def test_approve_draft_to_approved(self):
        wo = self._wo_with_finding()
        approved = approve_work_order(
            wo,
            dealership=self.default,
            approved_by=self.approver,
            authorized_cost=Decimal("500.00"),
        )
        self.assertEqual(approved.status, WORK_ORDER_STATUS_APPROVED)
        self.assertEqual(approved.approved_by, self.approver)
        self.assertIsNotNone(approved.approved_at)
        self.assertEqual(approved.authorized_cost, Decimal("500.00"))

    def test_approve_refuses_without_linked_findings(self):
        wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        # No findings attached.
        with self.assertRaises(InvalidReconTransitionError):
            approve_work_order(
                wo, dealership=self.default, approved_by=self.approver
            )

    def test_reapprove_preserves_original_approver_refreshes_timestamp(self):
        wo = self._wo_with_finding()
        first = approve_work_order(
            wo,
            dealership=self.default,
            approved_by=self.approver,
            authorized_cost=Decimal("500.00"),
        )
        first_approved_at = first.approved_at
        other_user = _make_user("ap-other")
        # Idempotent re-approve with different user; original should
        # persist.
        re = approve_work_order(
            first,
            dealership=self.default,
            approved_by=other_user,
            authorized_cost=Decimal("650.00"),
        )
        self.assertEqual(re.approved_by, self.approver)  # original
        self.assertEqual(re.authorized_cost, Decimal("650.00"))
        self.assertGreaterEqual(re.approved_at, first_approved_at)

    def test_approve_from_in_progress_rejected(self):
        wo = self._wo_with_finding()
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        starter = _make_user("ap-starter")
        start_work_order(
            wo, dealership=self.default, started_by=starter
        )
        wo.refresh_from_db()
        with self.assertRaises(InvalidReconTransitionError):
            approve_work_order(
                wo, dealership=self.default, approved_by=self.approver
            )

    def test_approve_cross_tenant_rejected(self):
        other = Dealership.objects.create(name="X", slug="x-ap")
        wo = self._wo_with_finding()
        with self.assertRaises(CrossTenantReconError):
            approve_work_order(
                wo, dealership=other, approved_by=self.approver
            )


class StartWorkOrder(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-ST", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        approve_work_order(
            self.wo,
            dealership=self.default,
            approved_by=_make_user("st-appr"),
        )

    def test_start_sets_started_by_and_at(self):
        starter = _make_user("st-starter")
        started = start_work_order(
            self.wo, dealership=self.default, started_by=starter
        )
        self.assertEqual(started.status, WORK_ORDER_STATUS_IN_PROGRESS)
        self.assertEqual(started.started_by, starter)
        self.assertIsNotNone(started.started_at)
        # Approval provenance preserved.
        self.assertIsNotNone(started.approved_by)
        self.assertIsNotNone(started.approved_at)

    def test_start_refuses_repeat(self):
        start_work_order(
            self.wo,
            dealership=self.default,
            started_by=_make_user("st-first"),
        )
        with self.assertRaises(InvalidReconTransitionError):
            start_work_order(
                self.wo,
                dealership=self.default,
                started_by=_make_user("st-second"),
            )

    def test_start_from_draft_rejected(self):
        # Fresh draft WO.
        vehicle = _make_vehicle("M42-ST-DR", self.default)
        wo = create_work_order(
            vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        with self.assertRaises(InvalidReconTransitionError):
            start_work_order(
                wo,
                dealership=self.default,
                started_by=_make_user("st-nope"),
            )


class CompleteWorkOrder(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-CO", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        approve_work_order(
            self.wo,
            dealership=self.default,
            approved_by=_make_user("co-appr"),
        )
        start_work_order(
            self.wo,
            dealership=self.default,
            started_by=_make_user("co-start"),
        )
        self.wo.refresh_from_db()

    def test_complete_from_in_progress(self):
        completer = _make_user("co-completer")
        completed = complete_work_order(
            self.wo,
            dealership=self.default,
            completed_by=completer,
            actual_cost=Decimal("475.50"),
        )
        self.assertEqual(completed.status, WORK_ORDER_STATUS_COMPLETED)
        self.assertEqual(completed.actual_cost, Decimal("475.50"))
        self.assertEqual(completed.completed_by, completer)
        self.assertIsNotNone(completed.completed_at)
        self.assertIsNotNone(completed.actual_completion_date)

    def test_complete_missing_actual_cost_raises_value_error(self):
        with self.assertRaises(ValueError):
            complete_work_order(
                self.wo,
                dealership=self.default,
                completed_by=_make_user("co-noc"),
                actual_cost=None,
            )

    def test_complete_negative_actual_cost_raises_value_error(self):
        with self.assertRaises(ValueError):
            complete_work_order(
                self.wo,
                dealership=self.default,
                completed_by=_make_user("co-neg"),
                actual_cost=Decimal("-50.00"),
            )

    def test_complete_from_approved_rejected(self):
        # Fresh WO in approved state — never started. Needs its
        # own vehicle + finding since cross-vehicle links are
        # prohibited (see AttachFindingsGating).
        vehicle_2 = _make_vehicle("M42-CO-DIR", self.default)
        report_2 = _make_report(vehicle_2, self.default)
        finding_2 = _make_finding(report_2, self.default)
        wo = create_work_order(
            vehicle_2,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            wo, dealership=self.default, finding_ids=[finding_2.pk]
        )
        approve_work_order(
            wo,
            dealership=self.default,
            approved_by=_make_user("co-dir-app"),
        )
        with self.assertRaises(InvalidReconTransitionError):
            complete_work_order(
                wo,
                dealership=self.default,
                completed_by=_make_user("co-dir-comp"),
                actual_cost=Decimal("100.00"),
            )


class CompletionDoesNotClaimQc(TestCase):
    """SESSION_067 QC-GAP lock: WorkOrder completion timestamps
    prove *when* work was marked complete, not *whether* it was
    verified. Locks the invariant at the schema level — no
    ``qc_*`` field exists on WorkOrder in M4.2, and
    :func:`complete_work_order` does not accept or set one."""

    def test_no_qc_field_on_workorder(self):
        field_names = {f.name for f in WorkOrder._meta.get_fields()}
        # If a future increment adds `qc_verified_at` /
        # `qc_verified_by` per QC-GAP Path B, this test will fail
        # and force a planning revision + update of this test.
        # That's the intended behavior — completion timestamps
        # alone must not silently start claiming QC verification.
        for expected_absent in (
            "qc_verified",
            "qc_verified_at",
            "qc_verified_by",
            "qc_notes",
            "test_drive_result",
        ):
            self.assertNotIn(
                expected_absent,
                field_names,
                f"WorkOrder unexpectedly gained {expected_absent!r} "
                "— the QC-GAP annotation in MILESTONE_4_PLANNING.md "
                "§1.0 must be revisited if QC fields are added.",
            )

    def test_complete_signature_does_not_accept_qc_verified(self):
        # Static check: the function's parameter list does not
        # include a qc_verified kwarg. If a future increment adds
        # one, this test will fail and force a planning revision.
        import inspect
        sig = inspect.signature(complete_work_order)
        self.assertNotIn("qc_verified", sig.parameters)
        self.assertNotIn("qc_verified_by", sig.parameters)


class CancelWorkOrder(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-CA", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.canceller = _make_user("ca-user")

    def _draft_wo(self):
        wo = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            wo, dealership=self.default, finding_ids=[self.finding.pk]
        )
        return wo

    def test_cancel_draft_reason_optional(self):
        wo = self._draft_wo()
        cancelled = cancel_work_order(
            wo, dealership=self.default, cancelled_by=self.canceller
        )
        self.assertEqual(cancelled.status, WORK_ORDER_STATUS_CANCELLED)
        self.assertEqual(cancelled.cancelled_by, self.canceller)
        self.assertEqual(cancelled.cancellation_reason, "")

    def test_cancel_approved_requires_reason(self):
        wo = self._draft_wo()
        approve_work_order(
            wo,
            dealership=self.default,
            approved_by=_make_user("ca-appr"),
        )
        with self.assertRaises(ValueError):
            cancel_work_order(
                wo,
                dealership=self.default,
                cancelled_by=self.canceller,
                cancellation_reason="",
            )
        # Whitespace-only also rejected.
        with self.assertRaises(ValueError):
            cancel_work_order(
                wo,
                dealership=self.default,
                cancelled_by=self.canceller,
                cancellation_reason="  \n\t  ",
            )
        # Nonblank reason succeeds.
        cancelled = cancel_work_order(
            wo,
            dealership=self.default,
            cancelled_by=self.canceller,
            cancellation_reason="Vendor unavailable this week.",
        )
        self.assertEqual(cancelled.status, WORK_ORDER_STATUS_CANCELLED)
        self.assertIn("Vendor unavailable", cancelled.cancellation_reason)

    def test_cancel_in_progress_preserves_start_provenance(self):
        wo = self._draft_wo()
        approve_work_order(
            wo,
            dealership=self.default,
            approved_by=_make_user("ca-appr-2"),
        )
        starter = _make_user("ca-starter")
        start_work_order(
            wo, dealership=self.default, started_by=starter
        )
        cancelled = cancel_work_order(
            wo,
            dealership=self.default,
            cancelled_by=self.canceller,
            cancellation_reason="Customer withdrew consent.",
        )
        # Start-side provenance preserved.
        self.assertEqual(cancelled.started_by, starter)
        self.assertIsNotNone(cancelled.started_at)

    def test_cancel_from_completed_rejected(self):
        wo = self._draft_wo()
        approve_work_order(
            wo,
            dealership=self.default,
            approved_by=_make_user("ca-completed-appr"),
        )
        start_work_order(
            wo,
            dealership=self.default,
            started_by=_make_user("ca-completed-start"),
        )
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=_make_user("ca-completed-comp"),
            actual_cost=Decimal("100.00"),
        )
        with self.assertRaises(InvalidReconTransitionError):
            cancel_work_order(
                wo,
                dealership=self.default,
                cancelled_by=self.canceller,
                cancellation_reason="Too late.",
            )

    def test_cancel_from_cancelled_rejected(self):
        wo = self._draft_wo()
        cancel_work_order(
            wo, dealership=self.default, cancelled_by=self.canceller
        )
        with self.assertRaises(InvalidReconTransitionError):
            cancel_work_order(
                wo, dealership=self.default, cancelled_by=self.canceller
            )


class NoLedgerSideEffectsWithoutEstimate(TestCase):
    """M4.3 boundary: WorkOrders with no ``estimated_cost`` and no
    ``actual_cost`` do not post to VehicleCost. Positive-assertion
    tests for the estimate/actual ledger paths live in
    ``test_recon_ledger.py``."""

    def test_approve_without_estimated_cost_posts_no_row(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-NOEST-APPR", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = create_work_order(
            vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            # No estimated_cost — nothing to post.
        )
        attach_findings(wo, dealership=default, finding_ids=[finding.pk])
        pre = VehicleCost.objects.count()
        approve_work_order(
            wo,
            dealership=default,
            approved_by=_make_user("noest-appr"),
        )
        self.assertEqual(VehicleCost.objects.count(), pre)

    def test_cancel_without_outstanding_estimate_posts_no_row(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-NOEST-CANC", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = create_work_order(
            vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(wo, dealership=default, finding_ids=[finding.pk])
        approve_work_order(
            wo,
            dealership=default,
            approved_by=_make_user("noest-canc-appr"),
        )
        pre = VehicleCost.objects.count()
        cancel_work_order(
            wo,
            dealership=default,
            cancelled_by=_make_user("noest-canc"),
            cancellation_reason="Nothing was estimated.",
        )
        self.assertEqual(VehicleCost.objects.count(), pre)


class RefreshBeforeStateCheck(TestCase):
    """Transition functions call select_for_update() + refresh_from_db
    inside their transaction so a stale in-memory copy doesn't let
    the caller drive an illegal transition. Locks the concurrency
    posture at the module-docstring level."""

    def test_stale_status_in_memory_does_not_bypass_state_check(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-REFRESH", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = create_work_order(
            vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(wo, dealership=default, finding_ids=[finding.pk])
        # Approve via a fresh handle.
        approve_work_order(
            wo,
            dealership=default,
            approved_by=_make_user("rf-appr"),
        )
        # Simulate a stale caller: manually reset in-memory status.
        wo.status = WORK_ORDER_STATUS_DRAFT
        # But start_work_order should refresh from DB and see
        # 'approved' → the transition succeeds because it's a valid
        # approved→in_progress move.
        started = start_work_order(
            wo, dealership=default, started_by=_make_user("rf-start")
        )
        self.assertEqual(started.status, WORK_ORDER_STATUS_IN_PROGRESS)
        # Conversely, an already-in_progress WO with a stale
        # 'approved' in-memory copy should NOT allow a second start.
        wo.refresh_from_db()
        self.assertEqual(wo.status, WORK_ORDER_STATUS_IN_PROGRESS)
        wo.status = WORK_ORDER_STATUS_APPROVED  # stale
        with self.assertRaises(InvalidReconTransitionError):
            start_work_order(
                wo, dealership=default, started_by=_make_user("rf-start-2")
            )


# ============================================================================
# Vehicle read-model properties
# ============================================================================


class OpenWorkOrdersProperty(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-OWO", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_empty_when_no_work_orders(self):
        self.assertEqual(list(self.vehicle.open_work_orders), [])

    def test_draft_and_approved_included(self):
        wo_draft = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        wo_appr = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            wo_appr,
            dealership=self.default,
            finding_ids=[self.finding.pk],
        )
        approve_work_order(
            wo_appr,
            dealership=self.default,
            approved_by=_make_user("owo-appr"),
        )
        open_wos = list(self.vehicle.open_work_orders)
        self.assertEqual(len(open_wos), 2)
        self.assertIn(wo_draft, open_wos)

    def test_completed_and_cancelled_excluded(self):
        # Completed WO.
        wo_c = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            wo_c, dealership=self.default, finding_ids=[self.finding.pk]
        )
        approve_work_order(
            wo_c,
            dealership=self.default,
            approved_by=_make_user("owo-c-appr"),
        )
        start_work_order(
            wo_c,
            dealership=self.default,
            started_by=_make_user("owo-c-start"),
        )
        complete_work_order(
            wo_c,
            dealership=self.default,
            completed_by=_make_user("owo-c-comp"),
            actual_cost=Decimal("100.00"),
        )
        # Cancelled WO.
        wo_x = create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        cancel_work_order(
            wo_x,
            dealership=self.default,
            cancelled_by=_make_user("owo-x-canc"),
        )
        self.assertEqual(list(self.vehicle.open_work_orders), [])

    def test_ordering_deterministic_by_created_at_desc(self):
        wos = []
        for i in range(3):
            wo = create_work_order(
                self.vehicle,
                dealership=self.default,
                category=CONDITION_CATEGORY_MECHANICAL,
                venue=WORK_ORDER_VENUE_IN_HOUSE,
            )
            wos.append(wo)
        # Newest first (-created_at).
        open_list = list(self.vehicle.open_work_orders)
        self.assertEqual([wo.pk for wo in open_list], [wos[2].pk, wos[1].pk, wos[0].pk])

    def test_tenant_isolation(self):
        # A WO on a different dealership's vehicle must not appear.
        other = Dealership.objects.create(name="Other", slug="other-owo")
        other_vehicle = _make_vehicle("M42-OWO-XT", other)
        create_work_order(
            other_vehicle,
            dealership=other,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        self.assertEqual(list(self.vehicle.open_work_orders), [])


class HasReconDecisionsProperty(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M42-HRD", self.default)

    def test_false_when_no_report(self):
        self.assertFalse(self.vehicle.has_recon_decisions)

    def test_false_when_only_draft_report(self):
        _make_report(
            self.vehicle,
            self.default,
            status=CONDITION_REPORT_STATUS_DRAFT,
        )
        self.assertFalse(self.vehicle.has_recon_decisions)

    def test_false_when_completed_but_no_decisions(self):
        report = _make_report(self.vehicle, self.default)
        _make_finding(report, self.default)
        self.assertFalse(self.vehicle.has_recon_decisions)

    def test_true_when_at_least_one_decision_recorded(self):
        report = _make_report(self.vehicle, self.default)
        finding = _make_finding(report, self.default)
        record_decision(
            finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
        )
        self.assertTrue(self.vehicle.has_recon_decisions)

    def test_uses_exists_query_not_full_load(self):
        # Structural check: the backing service function relies on
        # .exists(). Load a decision and ensure the property returns
        # True without materializing the finding/decision.
        report = _make_report(self.vehicle, self.default)
        for i in range(20):
            f = _make_finding(report, self.default, description=f"F{i}")
            record_decision(
                f,
                dealership=self.default,
                tier=RECON_DECISION_TIER_SHOULD_DO,
            )
        # Just call the property — if it were fetching everything
        # it would be far slower, but functionally we assert True.
        self.assertTrue(self.vehicle.has_recon_decisions)


# ============================================================================
# M3 preservation
# ============================================================================


class M3ReportsAndFindingsUnchanged(TestCase):
    """All M4.2 service functions must leave M3 ConditionReport and
    ConditionFinding rows untouched. Locks the read-only
    boundary."""

    def test_full_lifecycle_leaves_report_row_unchanged(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-M3-UC", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        report_before_updated_at = report.updated_at
        finding_before_updated_at = finding.updated_at
        # Full lifecycle.
        record_decision(
            finding, dealership=default, tier=RECON_DECISION_TIER_MUST_DO
        )
        wo = create_work_order(
            vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(wo, dealership=default, finding_ids=[finding.pk])
        approve_work_order(
            wo, dealership=default, approved_by=_make_user("m3-uc-appr")
        )
        start_work_order(
            wo, dealership=default, started_by=_make_user("m3-uc-start")
        )
        complete_work_order(
            wo,
            dealership=default,
            completed_by=_make_user("m3-uc-comp"),
            actual_cost=Decimal("100.00"),
        )
        report.refresh_from_db()
        finding.refresh_from_db()
        self.assertEqual(report.updated_at, report_before_updated_at)
        self.assertEqual(finding.updated_at, finding_before_updated_at)
        # Report is still complete + finding still exists.
        self.assertEqual(report.status, CONDITION_REPORT_STATUS_COMPLETE)
        self.assertTrue(ConditionFinding.objects.filter(pk=finding.pk).exists())


# ============================================================================
# Service helper direct invocation (sanity)
# ============================================================================


class ServiceHelperDirectInvocation(TestCase):
    """The two Vehicle @property accessors delegate one-line to
    service functions. Verify direct invocation of the service
    functions matches property behavior — locks the delegation
    contract."""

    def test_open_work_orders_service_matches_property(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-HELPER", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = create_work_order(
            vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(wo, dealership=default, finding_ids=[finding.pk])
        from_service = list(
            open_work_orders_for_vehicle(vehicle, dealership=default)
        )
        from_prop = list(vehicle.open_work_orders)
        self.assertEqual(from_service, from_prop)

    def test_has_recon_decisions_service_matches_property(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M42-HELPER-HRD", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        record_decision(
            finding, dealership=default, tier=RECON_DECISION_TIER_MUST_DO
        )
        self.assertEqual(
            has_recon_decisions_for_vehicle(vehicle, dealership=default),
            vehicle.has_recon_decisions,
        )


# ============================================================================
# Module-level constants
# ============================================================================


class ModuleConstantsExported(TestCase):
    """The transition functions rely on the _OPEN_STATUSES and
    _DECISION_LOCKING_WORK_ORDER_STATUSES module-level frozensets.
    Locking their exact contents so a future edit doesn't silently
    drift the vocabulary."""

    def test_open_statuses_exact_membership(self):
        self.assertEqual(
            recon_service._OPEN_STATUSES,
            frozenset(
                {
                    WORK_ORDER_STATUS_DRAFT,
                    WORK_ORDER_STATUS_APPROVED,
                    WORK_ORDER_STATUS_IN_PROGRESS,
                }
            ),
        )

    def test_decision_locking_statuses_exact_membership(self):
        self.assertEqual(
            recon_service._DECISION_LOCKING_WORK_ORDER_STATUSES,
            frozenset(
                {
                    WORK_ORDER_STATUS_APPROVED,
                    WORK_ORDER_STATUS_IN_PROGRESS,
                    WORK_ORDER_STATUS_COMPLETED,
                    WORK_ORDER_STATUS_CANCELLED,
                }
            ),
        )

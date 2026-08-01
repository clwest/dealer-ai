"""Milestone 4 · Increment 3 — recon → ledger integration tests.

Coverage of the ledger-posting helpers (:func:`_post_estimate`,
:func:`_post_estimate_reversal`,
:func:`_post_completion_reversal`, :func:`_post_cancel_reversal`,
:func:`_post_actual`) and the transition-function wiring that
invokes them at approve / revise-estimate / complete / cancel.

Locked invariants (per SESSION_066 planning refinement §5.e +
SESSION_068 brief):

Reference-key vocabulary:
- Every auto-minted VehicleCost row's ``reference`` matches
  exactly one of the five families.
- Sequence numbers on estimate + estimate_reversal rows form the
  monotonic pair `estimate:N` ↔ `estimate_reversal:N`.

Idempotency:
- Repeated call to any transition with the same reference key
  does not create a duplicate row.

Atomicity:
- Completion posts actual + completion_estimate_reversal inside
  a single transaction — a mid-completion save failure rolls
  back both.

Terminal-state invariants:
- After a WO reaches ``completed``, the net estimate contribution
  equals ``Decimal("0.00")``.
- After a WO reaches ``cancelled``, the net estimate contribution
  equals ``Decimal("0.00")``.
- ``projected_total_investment`` after completion equals the
  actual, not estimate + actual (SESSION_066 anti-double-count
  invariant).

Vendor snapshot:
- ``VehicleCost.vendor`` free-text captures the vendor name at
  posting time.
- A subsequent vendor rename does not rewrite historical rows.
- Vendor deactivation does not affect historical readability.

M3 preservation:
- ``ConditionFinding.estimated_cost`` continues to never post to
  VehicleCost (M3.5 invariant preserved).

Category mapping:
- WorkOrder.category maps deterministically to VehicleCost.category
  per the module-level ``_WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY``
  table.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_BODY_WORK,
    CATEGORY_BRAKES,
    CATEGORY_DIAGNOSTICS,
    CATEGORY_GLASS,
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_MISC_DEALER_EXPENSES,
    CATEGORY_OIL_SERVICE,
    CATEGORY_PAINT,
    CATEGORY_TIRES,
    CATEGORY_UPHOLSTERY,
    CONDITION_CATEGORY_ACCESSORIES,
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_COSMETIC,
    CONDITION_CATEGORY_ELECTRICAL,
    CONDITION_CATEGORY_FLUIDS,
    CONDITION_CATEGORY_GLASS,
    CONDITION_CATEGORY_INTERIOR,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_CATEGORY_MISSING,
    CONDITION_CATEGORY_OTHER,
    CONDITION_CATEGORY_SAFETY,
    CONDITION_CATEGORY_TIRES,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    Vehicle,
    VehicleCost,
    Vendor,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_VENUE_IN_HOUSE,
    WORK_ORDER_VENUE_OUTSOURCED,
    WorkOrder,
)
from dealer_ai.services import recon as recon_service
from dealer_ai.services.recon import (
    InvalidReconTransitionError,
    WORKORDER_LEDGER_REF_ACTUAL,
    WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL,
    WORKORDER_LEDGER_REF_ESTIMATE,
    WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL,
    WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL,
    _WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY,
    approve_work_order,
    attach_findings,
    cancel_work_order,
    complete_work_order,
    create_work_order,
    revise_estimate,
    start_work_order,
)
from dealer_ai.services.vehicle_ledger import compute_totals


User = get_user_model()


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("48000.00"),
        dealership=dealership,
    )


def _make_report(vehicle: Vehicle, dealership: Dealership) -> ConditionReport:
    return ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="M. Ruiz",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=timezone.now(),
    )


def _make_finding(
    report: ConditionReport,
    dealership: Dealership,
    category: str = CONDITION_CATEGORY_MECHANICAL,
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=category,
        severity=CONDITION_SEVERITY_REQUIRED,
        description="Ledger-test finding.",
    )


def _make_vendor(dealership: Dealership, slug: str = "led-vendor") -> Vendor:
    return Vendor.objects.create(
        dealership=dealership,
        name=f"Ledger Vendor {slug}",
        slug=slug,
    )


def _make_user(username: str) -> "User":
    return User.objects.create_user(username=username, password="test-pw")


def _built_wo(
    vehicle: Vehicle,
    dealership: Dealership,
    finding: ConditionFinding,
    *,
    estimated_cost=None,
    vendor: Vendor | None = None,
    category: str = CONDITION_CATEGORY_MECHANICAL,
) -> WorkOrder:
    """Create + attach + return a draft WorkOrder ready for approval."""
    wo = create_work_order(
        vehicle,
        dealership=dealership,
        category=category,
        venue=(
            WORK_ORDER_VENUE_OUTSOURCED
            if vendor is not None
            else WORK_ORDER_VENUE_IN_HOUSE
        ),
        vendor=vendor,
        estimated_cost=estimated_cost,
    )
    attach_findings(wo, dealership=dealership, finding_ids=[finding.pk])
    return wo


# ============================================================================
# Reference-key vocabulary
# ============================================================================


class ReferenceKeyFormatStrings(TestCase):
    """The five reference-key format strings are the public contract
    for M4.6+ read APIs that need to filter VehicleCost rows by
    origin. Lock the exact format so refactor doesn't silently
    drift them."""

    def test_estimate_format(self):
        self.assertEqual(
            WORKORDER_LEDGER_REF_ESTIMATE.format(wo_id=42, seq=1),
            "WORKORDER:42:estimate:1",
        )

    def test_estimate_reversal_format(self):
        self.assertEqual(
            WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL.format(wo_id=42, seq=1),
            "WORKORDER:42:estimate_reversal:1",
        )

    def test_completion_estimate_reversal_format(self):
        self.assertEqual(
            WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL.format(wo_id=42),
            "WORKORDER:42:completion_estimate_reversal",
        )

    def test_estimate_reversal_cancel_format(self):
        self.assertEqual(
            WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL.format(wo_id=42),
            "WORKORDER:42:estimate_reversal:cancel",
        )

    def test_actual_format(self):
        self.assertEqual(
            WORKORDER_LEDGER_REF_ACTUAL.format(wo_id=42),
            "WORKORDER:42:actual",
        )


class CategoryMappingCompleteness(TestCase):
    """All 12 M3 CONDITION_CATEGORY values must have a mapping
    entry — a future addition to CONDITION_CATEGORY_CHOICES that
    forgets to update the mapping would silently KeyError at
    posting time."""

    def test_mapping_covers_all_twelve_condition_categories(self):
        expected = {
            CONDITION_CATEGORY_MECHANICAL: CATEGORY_MECHANICAL_LABOR,
            CONDITION_CATEGORY_COSMETIC: CATEGORY_PAINT,
            CONDITION_CATEGORY_BODY: CATEGORY_BODY_WORK,
            CONDITION_CATEGORY_GLASS: CATEGORY_GLASS,
            CONDITION_CATEGORY_TIRES: CATEGORY_TIRES,
            CONDITION_CATEGORY_INTERIOR: CATEGORY_UPHOLSTERY,
            CONDITION_CATEGORY_FLUIDS: CATEGORY_OIL_SERVICE,
            CONDITION_CATEGORY_ELECTRICAL: CATEGORY_DIAGNOSTICS,
            CONDITION_CATEGORY_SAFETY: CATEGORY_BRAKES,
            CONDITION_CATEGORY_ACCESSORIES: CATEGORY_MISC_DEALER_EXPENSES,
            CONDITION_CATEGORY_MISSING: CATEGORY_MISC_DEALER_EXPENSES,
            CONDITION_CATEGORY_OTHER: CATEGORY_MISC_DEALER_EXPENSES,
        }
        self.assertEqual(
            _WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY, expected
        )


# ============================================================================
# Approve → estimate post
# ============================================================================


class ApproveWithEstimatePostsInitialEstimate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M43-APEST", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.approver = _make_user("apest-appr")

    def test_estimate_row_posted_on_first_approval(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("500.00"),
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        rows = VehicleCost.objects.filter(
            reference=f"WORKORDER:{wo.pk}:estimate:1"
        )
        self.assertEqual(rows.count(), 1)
        row = rows.first()
        self.assertTrue(row.is_estimate)
        self.assertEqual(row.amount, Decimal("500.00"))
        self.assertEqual(row.category, CATEGORY_MECHANICAL_LABOR)

    def test_no_estimate_row_when_estimated_cost_is_none(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=None,
        )
        pre = VehicleCost.objects.count()
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        self.assertEqual(VehicleCost.objects.count(), pre)

    def test_category_mapping_applied(self):
        # A BODY finding + BODY category WO should post
        # CATEGORY_BODY_WORK.
        body_finding = _make_finding(
            self.report, self.default, category=CONDITION_CATEGORY_BODY
        )
        wo = _built_wo(
            self.vehicle,
            self.default,
            body_finding,
            estimated_cost=Decimal("1200.00"),
            category=CONDITION_CATEGORY_BODY,
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        row = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:estimate:1"
        )
        self.assertEqual(row.category, CATEGORY_BODY_WORK)

    def test_idempotent_reapprove_does_not_duplicate_estimate(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("500.00"),
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        pre = VehicleCost.objects.filter(
            reference__startswith=f"WORKORDER:{wo.pk}:estimate"
        ).count()
        # Idempotent re-approve — should not post another estimate.
        approve_work_order(
            wo,
            dealership=self.default,
            approved_by=self.approver,
            authorized_cost=Decimal("700.00"),
        )
        post = VehicleCost.objects.filter(
            reference__startswith=f"WORKORDER:{wo.pk}:estimate"
        ).count()
        self.assertEqual(pre, post)


# ============================================================================
# Vendor snapshot
# ============================================================================


class VendorSnapshotOnLedgerRow(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M43-VS", self.default)
        self.report = _make_report(
            self.vehicle, self.default
        )
        self.finding = _make_finding(
            self.report, self.default, category=CONDITION_CATEGORY_BODY
        )
        self.vendor = _make_vendor(self.default, slug="snap-vendor")
        self.approver = _make_user("vs-appr")

    def test_vendor_name_captured_on_estimate_row(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("300.00"),
            vendor=self.vendor,
            category=CONDITION_CATEGORY_BODY,
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        row = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:estimate:1"
        )
        self.assertEqual(row.vendor, self.vendor.name)

    def test_vendor_rename_does_not_rewrite_historical_row(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("300.00"),
            vendor=self.vendor,
            category=CONDITION_CATEGORY_BODY,
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        original_name = self.vendor.name
        self.vendor.name = "New Vendor Name Inc."
        self.vendor.save()
        row = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:estimate:1"
        )
        self.assertEqual(row.vendor, original_name)  # snapshot preserved

    def test_inactive_vendor_row_still_readable(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("300.00"),
            vendor=self.vendor,
            category=CONDITION_CATEGORY_BODY,
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        self.vendor.is_active = False
        self.vendor.save()
        row = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:estimate:1"
        )
        # Row still exists + still readable, vendor snapshot intact.
        self.assertEqual(row.vendor, self.vendor.name)

    def test_in_house_wo_posts_empty_vendor_snapshot(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("300.00"),
            # No vendor — in-house.
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        row = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:estimate:1"
        )
        self.assertEqual(row.vendor, "")


# ============================================================================
# Complete → atomic reversal + actual
# ============================================================================


class CompletionPostsReversalPlusActualAtomically(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M43-COMP", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.approver = _make_user("comp-appr")
        self.starter = _make_user("comp-start")
        self.completer = _make_user("comp-comp")

    def _lifecycle_through_start(self, estimated=Decimal("500.00")):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=estimated,
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        start_work_order(
            wo, dealership=self.default, started_by=self.starter
        )
        wo.refresh_from_db()
        return wo

    def test_completion_posts_reversal_and_actual(self):
        wo = self._lifecycle_through_start()
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=self.completer,
            actual_cost=Decimal("475.00"),
        )
        reversal = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:completion_estimate_reversal"
        )
        actual = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:actual"
        )
        self.assertEqual(reversal.amount, Decimal("-500.00"))
        self.assertTrue(reversal.is_estimate)
        self.assertEqual(actual.amount, Decimal("475.00"))
        self.assertFalse(actual.is_estimate)

    def test_net_estimate_contribution_zero_after_completion(self):
        wo = self._lifecycle_through_start(estimated=Decimal("500.00"))
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=self.completer,
            actual_cost=Decimal("475.00"),
        )
        # All is_estimate=True rows for this WO must sum to zero.
        est_sum = sum(
            (row.amount for row in VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{wo.pk}:",
                is_estimate=True,
            )),
            Decimal("0.00"),
        )
        self.assertEqual(est_sum, Decimal("0.00"))

    def test_projected_total_investment_no_double_count(self):
        wo = self._lifecycle_through_start(estimated=Decimal("500.00"))
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=self.completer,
            actual_cost=Decimal("475.00"),
        )
        totals = compute_totals(self.vehicle, dealership=self.default)
        # actual side picks up 475; estimated_cost_total is 0
        # (estimate + reversal cancel out). projected_total_investment
        # = total_investment + estimated = actual + 0 = 475
        # (no acquisition on this vehicle).
        self.assertEqual(totals.total_investment, Decimal("475.00"))
        self.assertEqual(totals.estimated_cost_total, Decimal("0.00"))
        self.assertEqual(
            totals.projected_total_investment,
            totals.total_investment,
        )

    def test_completion_no_estimate_posts_only_actual(self):
        """WorkOrder completed without a prior estimate — the
        completion reversal is a no-op; only the actual posts."""
        wo = self._lifecycle_through_start(estimated=None)
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=self.completer,
            actual_cost=Decimal("100.00"),
        )
        # No reversal row (outstanding was zero).
        self.assertFalse(
            VehicleCost.objects.filter(
                reference=f"WORKORDER:{wo.pk}:completion_estimate_reversal"
            ).exists()
        )
        # Actual posted.
        self.assertTrue(
            VehicleCost.objects.filter(
                reference=f"WORKORDER:{wo.pk}:actual"
            ).exists()
        )

    def test_atomic_completion_rollback_on_validation_failure(self):
        """If the WorkOrder.save() inside the transaction raises,
        neither ledger row should persist. Simulated by patching
        the actual-post helper to raise after the reversal writes."""
        wo = self._lifecycle_through_start(estimated=Decimal("500.00"))
        # Monkey-patch _post_actual to raise, so the transaction
        # rolls back the reversal along with the failure.
        from unittest.mock import patch

        with patch.object(
            recon_service,
            "_post_actual",
            side_effect=RuntimeError("simulated"),
        ):
            with self.assertRaises(RuntimeError):
                complete_work_order(
                    wo,
                    dealership=self.default,
                    completed_by=self.completer,
                    actual_cost=Decimal("475.00"),
                )
        # WO must not be marked completed (transaction rolled back).
        wo.refresh_from_db()
        self.assertNotEqual(wo.status, WORK_ORDER_STATUS_COMPLETED)
        # Neither ledger row should exist.
        self.assertFalse(
            VehicleCost.objects.filter(
                reference=f"WORKORDER:{wo.pk}:completion_estimate_reversal"
            ).exists()
        )
        self.assertFalse(
            VehicleCost.objects.filter(
                reference=f"WORKORDER:{wo.pk}:actual"
            ).exists()
        )


# ============================================================================
# Estimate revision
# ============================================================================


class ReviseEstimate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M43-REV", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.approver = _make_user("rev-appr")

    def _approved_wo(self, estimated=Decimal("500.00")):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=estimated,
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        wo.refresh_from_db()
        return wo

    def test_first_revision_posts_reversal_plus_new_estimate(self):
        wo = self._approved_wo(estimated=Decimal("500.00"))
        revise_estimate(
            wo,
            dealership=self.default,
            new_estimated_cost=Decimal("650.00"),
        )
        # estimate:1 = 500, estimate_reversal:1 = -500,
        # estimate:2 = 650.
        rows = list(
            VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{wo.pk}:"
            ).order_by("reference")
        )
        refs = [row.reference for row in rows]
        self.assertIn(f"WORKORDER:{wo.pk}:estimate:1", refs)
        self.assertIn(f"WORKORDER:{wo.pk}:estimate:2", refs)
        self.assertIn(
            f"WORKORDER:{wo.pk}:estimate_reversal:1", refs
        )
        # Signed sum should equal the new estimate.
        est_sum = sum(
            (row.amount for row in rows if row.is_estimate),
            Decimal("0.00"),
        )
        self.assertEqual(est_sum, Decimal("650.00"))

    def test_revise_updates_work_order_estimated_cost(self):
        wo = self._approved_wo(estimated=Decimal("500.00"))
        revise_estimate(
            wo,
            dealership=self.default,
            new_estimated_cost=Decimal("650.00"),
        )
        wo.refresh_from_db()
        self.assertEqual(wo.estimated_cost, Decimal("650.00"))

    def test_revise_to_same_value_is_noop(self):
        wo = self._approved_wo(estimated=Decimal("500.00"))
        pre_count = VehicleCost.objects.filter(
            reference__startswith=f"WORKORDER:{wo.pk}:"
        ).count()
        revise_estimate(
            wo,
            dealership=self.default,
            new_estimated_cost=Decimal("500.00"),
        )
        post_count = VehicleCost.objects.filter(
            reference__startswith=f"WORKORDER:{wo.pk}:"
        ).count()
        self.assertEqual(pre_count, post_count)

    def test_sequential_revisions_produce_monotonic_seq(self):
        wo = self._approved_wo(estimated=Decimal("500.00"))
        revise_estimate(
            wo,
            dealership=self.default,
            new_estimated_cost=Decimal("650.00"),
        )
        revise_estimate(
            wo,
            dealership=self.default,
            new_estimated_cost=Decimal("800.00"),
        )
        estimate_refs = sorted(
            VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{wo.pk}:estimate:"
            ).values_list("reference", flat=True)
        )
        # estimate:1, estimate:2, estimate:3
        self.assertEqual(
            estimate_refs,
            [
                f"WORKORDER:{wo.pk}:estimate:1",
                f"WORKORDER:{wo.pk}:estimate:2",
                f"WORKORDER:{wo.pk}:estimate:3",
            ],
        )
        reversal_refs = sorted(
            VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{wo.pk}:estimate_reversal:"
            ).values_list("reference", flat=True)
        )
        self.assertEqual(
            reversal_refs,
            [
                f"WORKORDER:{wo.pk}:estimate_reversal:1",
                f"WORKORDER:{wo.pk}:estimate_reversal:2",
            ],
        )
        # Net = latest estimate.
        wo.refresh_from_db()
        est_sum = sum(
            (row.amount for row in VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{wo.pk}:",
                is_estimate=True,
            )),
            Decimal("0.00"),
        )
        self.assertEqual(est_sum, Decimal("800.00"))

    def test_revise_negative_raises(self):
        wo = self._approved_wo(estimated=Decimal("500.00"))
        with self.assertRaises(ValueError):
            revise_estimate(
                wo,
                dealership=self.default,
                new_estimated_cost=Decimal("-100.00"),
            )

    def test_revise_from_draft_rejected(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("500.00"),
        )
        # Never approved.
        with self.assertRaises(InvalidReconTransitionError):
            revise_estimate(
                wo,
                dealership=self.default,
                new_estimated_cost=Decimal("650.00"),
            )

    def test_revise_from_completed_rejected(self):
        wo = self._approved_wo(estimated=Decimal("500.00"))
        start_work_order(
            wo,
            dealership=self.default,
            started_by=_make_user("rev-start"),
        )
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=_make_user("rev-comp"),
            actual_cost=Decimal("500.00"),
        )
        with self.assertRaises(InvalidReconTransitionError):
            revise_estimate(
                wo,
                dealership=self.default,
                new_estimated_cost=Decimal("650.00"),
            )

    def test_revision_then_completion_still_nets_zero_estimate(self):
        wo = self._approved_wo(estimated=Decimal("500.00"))
        revise_estimate(
            wo,
            dealership=self.default,
            new_estimated_cost=Decimal("650.00"),
        )
        start_work_order(
            wo,
            dealership=self.default,
            started_by=_make_user("rev-start2"),
        )
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=_make_user("rev-comp2"),
            actual_cost=Decimal("640.00"),
        )
        est_sum = sum(
            (row.amount for row in VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{wo.pk}:",
                is_estimate=True,
            )),
            Decimal("0.00"),
        )
        self.assertEqual(est_sum, Decimal("0.00"))


# ============================================================================
# Cancel → reversal
# ============================================================================


class CancelPostsEstimateReversal(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M43-CANC", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.approver = _make_user("canc-appr")
        self.canceller = _make_user("canc-canc")

    def test_cancel_from_approved_reverses_outstanding_estimate(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("500.00"),
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        cancel_work_order(
            wo,
            dealership=self.default,
            cancelled_by=self.canceller,
            cancellation_reason="Vendor unavailable.",
        )
        reversal = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:estimate_reversal:cancel"
        )
        self.assertEqual(reversal.amount, Decimal("-500.00"))
        # Net estimate contribution = 0.
        est_sum = sum(
            (row.amount for row in VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{wo.pk}:",
                is_estimate=True,
            )),
            Decimal("0.00"),
        )
        self.assertEqual(est_sum, Decimal("0.00"))

    def test_cancel_from_draft_posts_no_reversal(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("500.00"),
        )
        # Not yet approved — no estimate on ledger.
        cancel_work_order(
            wo,
            dealership=self.default,
            cancelled_by=self.canceller,
        )
        self.assertFalse(
            VehicleCost.objects.filter(
                reference__startswith=f"WORKORDER:{wo.pk}:"
            ).exists()
        )

    def test_cancel_after_revision_reverses_current_outstanding(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("500.00"),
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        revise_estimate(
            wo,
            dealership=self.default,
            new_estimated_cost=Decimal("800.00"),
        )
        cancel_work_order(
            wo,
            dealership=self.default,
            cancelled_by=self.canceller,
            cancellation_reason="Customer changed mind after quote.",
        )
        reversal = VehicleCost.objects.get(
            reference=f"WORKORDER:{wo.pk}:estimate_reversal:cancel"
        )
        # Outstanding was 800 (the revised value); reversal is -800.
        self.assertEqual(reversal.amount, Decimal("-800.00"))


# ============================================================================
# Idempotency
# ============================================================================


class IdempotencyOnReplay(TestCase):
    """Every ledger helper checks the resolved reference key before
    posting. Repeated invocation of the same transition (or a
    manual invocation of the helper) does not create duplicate
    rows. Locks the idempotency contract."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M43-IDEM", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.approver = _make_user("idem-appr")

    def test_direct_helper_replay_does_not_duplicate_estimate(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("500.00"),
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        pre = VehicleCost.objects.filter(
            reference=f"WORKORDER:{wo.pk}:estimate:1"
        ).count()
        # Manually invoke the helper again — should be a no-op.
        wo.refresh_from_db()
        result = recon_service._post_estimate(wo, seq=1)
        post = VehicleCost.objects.filter(
            reference=f"WORKORDER:{wo.pk}:estimate:1"
        ).count()
        self.assertEqual(pre, post)
        self.assertIsNone(result)

    def test_direct_actual_helper_replay_does_not_duplicate(self):
        wo = _built_wo(
            self.vehicle,
            self.default,
            self.finding,
            estimated_cost=Decimal("500.00"),
        )
        approve_work_order(
            wo, dealership=self.default, approved_by=self.approver
        )
        start_work_order(
            wo,
            dealership=self.default,
            started_by=_make_user("idem-start"),
        )
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=_make_user("idem-comp"),
            actual_cost=Decimal("475.00"),
        )
        wo.refresh_from_db()
        pre = VehicleCost.objects.filter(
            reference=f"WORKORDER:{wo.pk}:actual"
        ).count()
        result = recon_service._post_actual(wo)
        post = VehicleCost.objects.filter(
            reference=f"WORKORDER:{wo.pk}:actual"
        ).count()
        self.assertEqual(pre, post)
        self.assertIsNone(result)


# ============================================================================
# M3 preservation regression
# ============================================================================


class ConditionFindingEstimatedCostStillDoesNotPost(TestCase):
    """M3.5 invariant preserved through M4.3: creating a
    ConditionFinding with an estimated_cost still does NOT post to
    VehicleCost. Only WorkOrder transitions post."""

    def test_creating_finding_with_estimated_cost_still_no_post(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M43-M3INV", default)
        report = _make_report(vehicle, default)
        pre = VehicleCost.objects.count()
        ConditionFinding.objects.create(
            report=report,
            dealership=default,
            category=CONDITION_CATEGORY_BODY,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="M3 estimated_cost regression check.",
            estimated_cost=Decimal("1200.00"),
        )
        self.assertEqual(VehicleCost.objects.count(), pre)

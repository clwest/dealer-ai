"""Milestone 4 · Increment 4 — parts service tests.

Coverage of :func:`add_part`, :func:`update_part`,
:func:`transition_part_status`, and :func:`delete_part` in
``dealer_ai/services/recon.py``.

Locked invariants (per SESSION_069 brief + planning §1.5 + §5.h):

Add:
- Parent WO status must be draft / approved / in_progress.
- Cross-tenant WO refused.
- Invalid source_type refused.
- quantity < 1 refused via MinValueValidator (full_clean).
- Always creates in status='needed'.
- Zero VehicleCost side effects.

Update:
- Whitelist enforcement (8 fields).
- Rejects status via whitelist.
- Rejects timestamps via whitelist.
- Rejects unknown fields.
- Parent WO status gating.
- Cross-tenant refused.
- Invalid source_type refused.

Transition:
- Every allowed transition succeeds + sets correct timestamp.
- Every disallowed transition raises InvalidReconTransitionError.
- Terminal states (installed / returned) reject all transitions.
- Parent WO status gating.
- Cross-tenant refused.
- Invalid new_status refused.
- select_for_update + refresh_from_db pattern (stale in-memory
  status does not bypass the gate).

Delete:
- Draft-only.
- Non-draft rejected.
- Cross-tenant refused.

Cascade / preservation:
- Parts survive WO cancellation (documentation).
- Parts survive WO completion (documentation).

Zero-ledger:
- No add_part / update_part / transition / delete call creates a
  VehicleCost row. Parts do not independently post to VehicleCost
  (planning §5.h).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    Vehicle,
    VehicleCost,
    WORK_ORDER_PART_SOURCE_CUSTOMER_SUPPLIED,
    WORK_ORDER_PART_SOURCE_IN_STOCK,
    WORK_ORDER_PART_SOURCE_LOCAL_PARTS,
    WORK_ORDER_PART_SOURCE_OEM_DEALER,
    WORK_ORDER_PART_STATUS_BACKORDERED,
    WORK_ORDER_PART_STATUS_INSTALLED,
    WORK_ORDER_PART_STATUS_NEEDED,
    WORK_ORDER_PART_STATUS_ORDERED,
    WORK_ORDER_PART_STATUS_RECEIVED,
    WORK_ORDER_PART_STATUS_RETURNED,
    WORK_ORDER_VENUE_IN_HOUSE,
    WorkOrder,
    WorkOrderPart,
)
from dealer_ai.services import recon as recon_service
from dealer_ai.services.recon import (
    CrossTenantReconError,
    InvalidReconTransitionError,
    add_part,
    approve_work_order,
    attach_findings,
    cancel_work_order,
    complete_work_order,
    create_work_order,
    delete_part,
    start_work_order,
    transition_part_status,
    update_part,
)


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
    report: ConditionReport, dealership: Dealership
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        severity=CONDITION_SEVERITY_REQUIRED,
        description="Parts-service test finding.",
    )


def _make_user(username: str) -> "User":
    return User.objects.create_user(username=username, password="test-pw")


def _draft_wo(
    vehicle: Vehicle, dealership: Dealership, finding: ConditionFinding
) -> WorkOrder:
    wo = create_work_order(
        vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        venue=WORK_ORDER_VENUE_IN_HOUSE,
    )
    attach_findings(wo, dealership=dealership, finding_ids=[finding.pk])
    return wo


def _approved_wo(
    vehicle: Vehicle, dealership: Dealership, finding: ConditionFinding
) -> WorkOrder:
    wo = _draft_wo(vehicle, dealership, finding)
    approve_work_order(
        wo, dealership=dealership, approved_by=_make_user(f"appr-{wo.pk}")
    )
    wo.refresh_from_db()
    return wo


def _in_progress_wo(
    vehicle: Vehicle, dealership: Dealership, finding: ConditionFinding
) -> WorkOrder:
    wo = _approved_wo(vehicle, dealership, finding)
    start_work_order(
        wo, dealership=dealership, started_by=_make_user(f"start-{wo.pk}")
    )
    wo.refresh_from_db()
    return wo


# ============================================================================
# add_part
# ============================================================================


class AddPartHappyPath(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-ADD", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_creates_part_in_needed_status(self):
        wo = _draft_wo(self.vehicle, self.default, self.finding)
        part = add_part(
            wo,
            dealership=self.default,
            name="Front brake pads",
            quantity=1,
            part_number="BREMBO-P85",
            source_type=WORK_ORDER_PART_SOURCE_OEM_DEALER,
            source_name="Ford Yuma",
            unit_cost=Decimal("125.00"),
        )
        self.assertEqual(part.status, WORK_ORDER_PART_STATUS_NEEDED)
        self.assertEqual(part.work_order, wo)
        self.assertEqual(part.dealership, self.default)
        self.assertEqual(part.name, "Front brake pads")
        self.assertEqual(part.quantity, 1)
        self.assertEqual(part.unit_cost, Decimal("125.00"))
        self.assertEqual(part.source_type, WORK_ORDER_PART_SOURCE_OEM_DEALER)
        # Timestamps all null at creation.
        self.assertIsNone(part.ordered_at)
        self.assertIsNone(part.received_at)
        self.assertIsNone(part.installed_at)
        self.assertIsNone(part.returned_at)

    def test_defaults_source_type_in_stock(self):
        wo = _draft_wo(self.vehicle, self.default, self.finding)
        part = add_part(wo, dealership=self.default, name="Random bolt")
        self.assertEqual(part.source_type, WORK_ORDER_PART_SOURCE_IN_STOCK)
        self.assertEqual(part.quantity, 1)

    def test_customer_supplied_source_permitted(self):
        wo = _draft_wo(self.vehicle, self.default, self.finding)
        part = add_part(
            wo,
            dealership=self.default,
            name="Customer's own tire",
            source_type=WORK_ORDER_PART_SOURCE_CUSTOMER_SUPPLIED,
        )
        self.assertEqual(
            part.source_type, WORK_ORDER_PART_SOURCE_CUSTOMER_SUPPLIED
        )


class AddPartWorkOrderStatusGating(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-GATE", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_add_on_draft_permitted(self):
        wo = _draft_wo(self.vehicle, self.default, self.finding)
        add_part(wo, dealership=self.default, name="Draft OK")

    def test_add_on_approved_permitted(self):
        wo = _approved_wo(self.vehicle, self.default, self.finding)
        add_part(wo, dealership=self.default, name="Approved OK")

    def test_add_on_in_progress_permitted(self):
        wo = _in_progress_wo(self.vehicle, self.default, self.finding)
        add_part(wo, dealership=self.default, name="In progress OK")

    def test_add_on_completed_rejected(self):
        wo = _in_progress_wo(self.vehicle, self.default, self.finding)
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=_make_user("gate-comp"),
            actual_cost=Decimal("100.00"),
        )
        with self.assertRaises(InvalidReconTransitionError):
            add_part(wo, dealership=self.default, name="Too late")

    def test_add_on_cancelled_rejected(self):
        wo = _draft_wo(self.vehicle, self.default, self.finding)
        cancel_work_order(
            wo, dealership=self.default, cancelled_by=_make_user("gate-canc")
        )
        with self.assertRaises(InvalidReconTransitionError):
            add_part(wo, dealership=self.default, name="Also too late")


class AddPartValidation(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-VAL", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = _draft_wo(self.vehicle, self.default, self.finding)

    def test_invalid_source_type_rejected(self):
        with self.assertRaises(ValueError):
            add_part(
                self.wo,
                dealership=self.default,
                name="Bad source",
                source_type="martian_dealer",
            )

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            add_part(
                self.wo,
                dealership=self.default,
                name="Bad qty",
                quantity=0,
            )

    def test_cross_tenant_wo_rejected(self):
        other = Dealership.objects.create(name="Other", slug="other-add")
        with self.assertRaises(CrossTenantReconError):
            add_part(self.wo, dealership=other, name="Cross-tenant")


class AddPartNoLedgerSideEffect(TestCase):
    def test_add_part_creates_no_vehicle_cost(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M44-NOLDG", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = _draft_wo(vehicle, default, finding)
        pre = VehicleCost.objects.count()
        add_part(
            wo,
            dealership=default,
            name="Ledger regression",
            unit_cost=Decimal("500.00"),
        )
        self.assertEqual(VehicleCost.objects.count(), pre)


# ============================================================================
# update_part
# ============================================================================


class UpdatePartWhitelist(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-UPD", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = _draft_wo(self.vehicle, self.default, self.finding)
        self.part = add_part(
            self.wo, dealership=self.default, name="Original", quantity=1
        )

    def test_updates_whitelisted_fields(self):
        updated = update_part(
            self.part,
            dealership=self.default,
            name="Renamed",
            description="Updated description.",
            part_number="X-1000",
            quantity=3,
            unit_cost=Decimal("42.50"),
            source_type=WORK_ORDER_PART_SOURCE_LOCAL_PARTS,
            source_name="NAPA Yuma",
            notes="Ordered on backup.",
        )
        self.assertEqual(updated.name, "Renamed")
        self.assertEqual(updated.description, "Updated description.")
        self.assertEqual(updated.part_number, "X-1000")
        self.assertEqual(updated.quantity, 3)
        self.assertEqual(updated.unit_cost, Decimal("42.50"))
        self.assertEqual(updated.source_type, WORK_ORDER_PART_SOURCE_LOCAL_PARTS)
        self.assertEqual(updated.source_name, "NAPA Yuma")

    def test_rejects_status_field(self):
        with self.assertRaises(ValueError):
            update_part(
                self.part,
                dealership=self.default,
                status=WORK_ORDER_PART_STATUS_ORDERED,
            )

    def test_rejects_timestamp_fields(self):
        with self.assertRaises(ValueError):
            update_part(
                self.part,
                dealership=self.default,
                ordered_at=timezone.now().date(),
            )

    def test_rejects_work_order_field(self):
        with self.assertRaises(ValueError):
            update_part(
                self.part,
                dealership=self.default,
                work_order=self.wo,
            )

    def test_rejects_dealership_field(self):
        with self.assertRaises(ValueError):
            update_part(
                self.part,
                dealership=self.default,
                dealership_new=self.default,  # typo'd anyway
            )

    def test_rejects_unknown_field(self):
        with self.assertRaises(ValueError):
            update_part(
                self.part,
                dealership=self.default,
                serial_number="XYZ",  # not a real field
            )

    def test_rejects_invalid_source_type(self):
        with self.assertRaises(ValueError):
            update_part(
                self.part,
                dealership=self.default,
                source_type="unicorn_delivery",
            )


class UpdatePartWorkOrderStatusGating(TestCase):
    """update_part refuses when parent WO is terminal — parts on a
    finished WO are historical documentation."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-UGATE", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_update_on_in_progress_permitted(self):
        wo = _in_progress_wo(self.vehicle, self.default, self.finding)
        part = add_part(wo, dealership=self.default, name="Prog")
        update_part(part, dealership=self.default, name="Prog-renamed")

    def test_update_on_completed_rejected(self):
        wo = _in_progress_wo(self.vehicle, self.default, self.finding)
        part = add_part(wo, dealership=self.default, name="Locked-in")
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=_make_user("ugate-comp"),
            actual_cost=Decimal("100.00"),
        )
        with self.assertRaises(InvalidReconTransitionError):
            update_part(part, dealership=self.default, name="Too late")


class UpdatePartCrossTenant(TestCase):
    def test_cross_tenant_rejected(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M44-UXT", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = _draft_wo(vehicle, default, finding)
        part = add_part(wo, dealership=default, name="XT")
        other = Dealership.objects.create(name="Other", slug="other-upd")
        with self.assertRaises(CrossTenantReconError):
            update_part(part, dealership=other, name="Should fail")


# ============================================================================
# transition_part_status
# ============================================================================


class TransitionPartStatusAllowed(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-TR", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = _draft_wo(self.vehicle, self.default, self.finding)

    def _fresh_part(self, name: str) -> WorkOrderPart:
        return add_part(self.wo, dealership=self.default, name=name)

    def test_needed_to_ordered_sets_ordered_at(self):
        part = self._fresh_part("N→O")
        result = transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        self.assertEqual(result.status, WORK_ORDER_PART_STATUS_ORDERED)
        self.assertIsNotNone(result.ordered_at)
        self.assertIsNone(result.received_at)

    def test_ordered_to_received_sets_received_at(self):
        part = self._fresh_part("O→R")
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        result = transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_RECEIVED,
        )
        self.assertEqual(result.status, WORK_ORDER_PART_STATUS_RECEIVED)
        self.assertIsNotNone(result.received_at)

    def test_received_to_installed_sets_installed_at(self):
        part = self._fresh_part("R→I")
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_RECEIVED,
        )
        result = transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_INSTALLED,
        )
        self.assertEqual(result.status, WORK_ORDER_PART_STATUS_INSTALLED)
        self.assertIsNotNone(result.installed_at)

    def test_ordered_to_backordered_no_timestamp(self):
        part = self._fresh_part("O→B")
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        part.refresh_from_db()
        original_ordered_at = part.ordered_at
        self.assertIsNotNone(original_ordered_at)
        result = transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_BACKORDERED,
        )
        self.assertEqual(result.status, WORK_ORDER_PART_STATUS_BACKORDERED)
        # ordered_at preserved (not cleared, not refreshed).
        self.assertEqual(result.ordered_at, original_ordered_at)

    def test_backordered_to_ordered_refreshes_ordered_at(self):
        part = self._fresh_part("B→O")
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_BACKORDERED,
        )
        result = transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        self.assertEqual(result.status, WORK_ORDER_PART_STATUS_ORDERED)
        self.assertIsNotNone(result.ordered_at)

    def test_ordered_to_returned_sets_returned_at(self):
        part = self._fresh_part("O→Ret")
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        result = transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_RETURNED,
        )
        self.assertEqual(result.status, WORK_ORDER_PART_STATUS_RETURNED)
        self.assertIsNotNone(result.returned_at)

    def test_received_to_returned_sets_returned_at(self):
        part = self._fresh_part("R→Ret")
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_RECEIVED,
        )
        result = transition_part_status(
            part,
            dealership=self.default,
            new_status=WORK_ORDER_PART_STATUS_RETURNED,
        )
        self.assertEqual(result.status, WORK_ORDER_PART_STATUS_RETURNED)
        self.assertIsNotNone(result.returned_at)


class TransitionPartStatusDisallowed(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-TRDIS", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = _draft_wo(self.vehicle, self.default, self.finding)

    def _at_status(
        self, status: str, name: str = "T"
    ) -> WorkOrderPart:
        part = add_part(self.wo, dealership=self.default, name=name)
        if status == WORK_ORDER_PART_STATUS_NEEDED:
            return part
        transitions = {
            WORK_ORDER_PART_STATUS_ORDERED: [
                WORK_ORDER_PART_STATUS_ORDERED
            ],
            WORK_ORDER_PART_STATUS_BACKORDERED: [
                WORK_ORDER_PART_STATUS_ORDERED,
                WORK_ORDER_PART_STATUS_BACKORDERED,
            ],
            WORK_ORDER_PART_STATUS_RECEIVED: [
                WORK_ORDER_PART_STATUS_ORDERED,
                WORK_ORDER_PART_STATUS_RECEIVED,
            ],
            WORK_ORDER_PART_STATUS_INSTALLED: [
                WORK_ORDER_PART_STATUS_ORDERED,
                WORK_ORDER_PART_STATUS_RECEIVED,
                WORK_ORDER_PART_STATUS_INSTALLED,
            ],
            WORK_ORDER_PART_STATUS_RETURNED: [
                WORK_ORDER_PART_STATUS_ORDERED,
                WORK_ORDER_PART_STATUS_RETURNED,
            ],
        }
        for st in transitions[status]:
            part = transition_part_status(
                part, dealership=self.default, new_status=st
            )
        return part

    def test_needed_to_received_rejected(self):
        part = self._at_status(WORK_ORDER_PART_STATUS_NEEDED)
        with self.assertRaises(InvalidReconTransitionError):
            transition_part_status(
                part,
                dealership=self.default,
                new_status=WORK_ORDER_PART_STATUS_RECEIVED,
            )

    def test_needed_to_installed_rejected(self):
        part = self._at_status(WORK_ORDER_PART_STATUS_NEEDED)
        with self.assertRaises(InvalidReconTransitionError):
            transition_part_status(
                part,
                dealership=self.default,
                new_status=WORK_ORDER_PART_STATUS_INSTALLED,
            )

    def test_ordered_to_installed_rejected(self):
        part = self._at_status(WORK_ORDER_PART_STATUS_ORDERED)
        with self.assertRaises(InvalidReconTransitionError):
            transition_part_status(
                part,
                dealership=self.default,
                new_status=WORK_ORDER_PART_STATUS_INSTALLED,
            )

    def test_received_to_needed_rejected(self):
        part = self._at_status(WORK_ORDER_PART_STATUS_RECEIVED)
        with self.assertRaises(InvalidReconTransitionError):
            transition_part_status(
                part,
                dealership=self.default,
                new_status=WORK_ORDER_PART_STATUS_NEEDED,
            )

    def test_installed_is_terminal(self):
        part = self._at_status(WORK_ORDER_PART_STATUS_INSTALLED)
        for target in (
            WORK_ORDER_PART_STATUS_NEEDED,
            WORK_ORDER_PART_STATUS_ORDERED,
            WORK_ORDER_PART_STATUS_RECEIVED,
            WORK_ORDER_PART_STATUS_RETURNED,
            WORK_ORDER_PART_STATUS_BACKORDERED,
        ):
            with self.assertRaises(InvalidReconTransitionError):
                transition_part_status(
                    part, dealership=self.default, new_status=target
                )

    def test_returned_is_terminal(self):
        part = self._at_status(WORK_ORDER_PART_STATUS_RETURNED)
        for target in (
            WORK_ORDER_PART_STATUS_NEEDED,
            WORK_ORDER_PART_STATUS_ORDERED,
            WORK_ORDER_PART_STATUS_RECEIVED,
            WORK_ORDER_PART_STATUS_INSTALLED,
            WORK_ORDER_PART_STATUS_BACKORDERED,
        ):
            with self.assertRaises(InvalidReconTransitionError):
                transition_part_status(
                    part, dealership=self.default, new_status=target
                )


class TransitionPartStatusGating(TestCase):
    def test_transition_on_completed_wo_rejected(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M44-TRGATE", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = _in_progress_wo(vehicle, default, finding)
        part = add_part(wo, dealership=default, name="Locked")
        complete_work_order(
            wo,
            dealership=default,
            completed_by=_make_user("trgate-comp"),
            actual_cost=Decimal("100.00"),
        )
        with self.assertRaises(InvalidReconTransitionError):
            transition_part_status(
                part,
                dealership=default,
                new_status=WORK_ORDER_PART_STATUS_ORDERED,
            )

    def test_invalid_new_status_rejected(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M44-TRINV", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = _draft_wo(vehicle, default, finding)
        part = add_part(wo, dealership=default, name="Bad status")
        with self.assertRaises(ValueError):
            transition_part_status(
                part, dealership=default, new_status="teleported"
            )

    def test_cross_tenant_rejected(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M44-TRXT", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = _draft_wo(vehicle, default, finding)
        part = add_part(wo, dealership=default, name="XT")
        other = Dealership.objects.create(name="Other", slug="other-tr")
        with self.assertRaises(CrossTenantReconError):
            transition_part_status(
                part,
                dealership=other,
                new_status=WORK_ORDER_PART_STATUS_ORDERED,
            )


class TransitionPartStatusRefreshBeforeCheck(TestCase):
    """Concurrency: stale in-memory status must not bypass the
    transition gate. select_for_update + refresh_from_db pattern
    inherited from M4.2."""

    def test_stale_in_memory_status_does_not_bypass_gate(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M44-REFRESH", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = _draft_wo(vehicle, default, finding)
        part = add_part(wo, dealership=default, name="Stale")
        # Advance to installed via a fresh handle.
        transition_part_status(
            part, dealership=default, new_status=WORK_ORDER_PART_STATUS_ORDERED
        )
        transition_part_status(
            part, dealership=default, new_status=WORK_ORDER_PART_STATUS_RECEIVED
        )
        transition_part_status(
            part, dealership=default, new_status=WORK_ORDER_PART_STATUS_INSTALLED
        )
        # Stale caller: reset in-memory status.
        part.status = WORK_ORDER_PART_STATUS_ORDERED  # stale
        # Real status is 'installed' (terminal). Attempt to
        # transition to 'received' should be refused despite the
        # stale in-memory 'ordered'.
        with self.assertRaises(InvalidReconTransitionError):
            transition_part_status(
                part,
                dealership=default,
                new_status=WORK_ORDER_PART_STATUS_RECEIVED,
            )


# ============================================================================
# delete_part
# ============================================================================


class DeletePart(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-DEL", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_delete_on_draft_wo_removes_part(self):
        wo = _draft_wo(self.vehicle, self.default, self.finding)
        part = add_part(wo, dealership=self.default, name="Deletable")
        pk = part.pk
        delete_part(part, dealership=self.default)
        self.assertFalse(WorkOrderPart.objects.filter(pk=pk).exists())

    def test_delete_on_approved_wo_rejected(self):
        wo = _approved_wo(self.vehicle, self.default, self.finding)
        part = add_part(wo, dealership=self.default, name="Locked")
        with self.assertRaises(InvalidReconTransitionError):
            delete_part(part, dealership=self.default)
        # Part still exists.
        self.assertTrue(WorkOrderPart.objects.filter(pk=part.pk).exists())

    def test_delete_on_in_progress_wo_rejected(self):
        wo = _in_progress_wo(self.vehicle, self.default, self.finding)
        part = add_part(wo, dealership=self.default, name="Also locked")
        with self.assertRaises(InvalidReconTransitionError):
            delete_part(part, dealership=self.default)

    def test_delete_on_completed_wo_rejected(self):
        wo = _in_progress_wo(self.vehicle, self.default, self.finding)
        part = add_part(wo, dealership=self.default, name="Frozen")
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=_make_user("del-comp"),
            actual_cost=Decimal("100.00"),
        )
        with self.assertRaises(InvalidReconTransitionError):
            delete_part(part, dealership=self.default)

    def test_delete_cross_tenant_rejected(self):
        wo = _draft_wo(self.vehicle, self.default, self.finding)
        part = add_part(wo, dealership=self.default, name="XT")
        other = Dealership.objects.create(name="Other", slug="other-del")
        with self.assertRaises(CrossTenantReconError):
            delete_part(part, dealership=other)


# ============================================================================
# Parts survive terminal WO transitions
# ============================================================================


class PartsSurviveTerminalTransitions(TestCase):
    """Cancelling or completing a WO does NOT delete its parts —
    they stay as historical documentation of what the operator
    ordered / installed / returned during the recon process."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M44-SURV", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_parts_survive_cancellation(self):
        wo = _draft_wo(self.vehicle, self.default, self.finding)
        add_part(wo, dealership=self.default, name="Survives cancel")
        cancel_work_order(
            wo, dealership=self.default, cancelled_by=_make_user("surv-canc")
        )
        self.assertEqual(
            WorkOrderPart.objects.filter(work_order=wo).count(), 1
        )

    def test_parts_survive_completion(self):
        wo = _in_progress_wo(self.vehicle, self.default, self.finding)
        add_part(wo, dealership=self.default, name="Survives complete")
        complete_work_order(
            wo,
            dealership=self.default,
            completed_by=_make_user("surv-comp"),
            actual_cost=Decimal("100.00"),
        )
        self.assertEqual(
            WorkOrderPart.objects.filter(work_order=wo).count(), 1
        )


# ============================================================================
# Zero ledger side effects across all part operations
# ============================================================================


class NoLedgerSideEffectsFromPartsOperations(TestCase):
    """Planning §5.h: parts do NOT independently post to
    VehicleCost. Their cost lives on the WorkOrder's estimate /
    actual aggregate. Locks the M4.4 → M4.3 boundary."""

    def test_full_parts_lifecycle_creates_no_vehicle_cost(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M44-LDG", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        wo = _draft_wo(vehicle, default, finding)
        pre = VehicleCost.objects.count()
        # Add.
        part = add_part(
            wo,
            dealership=default,
            name="Lifecycle test",
            unit_cost=Decimal("175.00"),
        )
        # Update.
        update_part(
            part,
            dealership=default,
            unit_cost=Decimal("185.00"),
        )
        # Transitions.
        transition_part_status(
            part,
            dealership=default,
            new_status=WORK_ORDER_PART_STATUS_ORDERED,
        )
        transition_part_status(
            part,
            dealership=default,
            new_status=WORK_ORDER_PART_STATUS_RECEIVED,
        )
        transition_part_status(
            part,
            dealership=default,
            new_status=WORK_ORDER_PART_STATUS_INSTALLED,
        )
        # Delete (need a fresh part since installed can't be deleted
        # on approved, and this WO is still draft — but the installed
        # part can't be deleted on draft either? Actually it can —
        # delete gates on parent WO status, not part status).
        deletable = add_part(wo, dealership=default, name="Deletable")
        delete_part(deletable, dealership=default)
        self.assertEqual(VehicleCost.objects.count(), pre)


# ============================================================================
# Module-level constants
# ============================================================================


class PartsModuleConstantsExported(TestCase):
    """Lock the exact contents of the mutation-permitted-status set
    and the update whitelist so refactor cannot silently drift the
    vocabulary."""

    def test_part_mutation_allowed_statuses_exact_membership(self):
        from dealer_ai.models import (
            WORK_ORDER_STATUS_APPROVED,
            WORK_ORDER_STATUS_DRAFT,
            WORK_ORDER_STATUS_IN_PROGRESS,
        )
        self.assertEqual(
            recon_service._PART_MUTATION_ALLOWED_WORK_ORDER_STATUSES,
            frozenset(
                {
                    WORK_ORDER_STATUS_DRAFT,
                    WORK_ORDER_STATUS_APPROVED,
                    WORK_ORDER_STATUS_IN_PROGRESS,
                }
            ),
        )

    def test_update_part_whitelist_exact_membership(self):
        self.assertEqual(
            recon_service._UPDATE_PART_ALLOWED_FIELDS,
            frozenset(
                {
                    "name",
                    "description",
                    "part_number",
                    "quantity",
                    "unit_cost",
                    "source_type",
                    "source_name",
                    "notes",
                }
            ),
        )

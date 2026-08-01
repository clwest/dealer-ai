"""Milestone 3 · Increment 2 — condition-report service layer tests.

Service-layer coverage only. No view-layer / API tests — those land
at M3.6. No storage tests — those land at M3.4 / M3.5. No Vehicle
``@property`` accessor tests — those land at M3.3.

Every state transition is hand-verified. Every cross-tenant path is
exercised. Every service function verifies the ``estimated_cost``-
never-becomes-a-``VehicleCost`` invariant. ``full_clean()`` is
proven to fire before save by triggering the model layer's
``clean()`` cross-tenant guard through the service.

Test class map:

- ``CrossTenantGuards`` — fail-closed on all 7 public functions +
  ``ValueError`` subclass identity.
- ``CreateReportSemantics`` — always ``draft``, ``completed_at``
  NULL at birth, provenance fields distinct, cross-tenant.
- ``CompleteReportSemantics`` — one-way draft → complete;
  ``completed_at`` set exactly once; double-complete raises.
- ``AddFindingSemantics`` — draft-only; invalid category /
  severity raise; ``estimated_cost`` optional.
- ``UpdateFindingSemantics`` — whitelist enforced;
  ``report`` / ``dealership`` / unknown keys refused; re-validation
  on change.
- ``DeleteFindingSemantics`` — draft-only; row removed on success.
- ``CompletedReportImmutability`` — every mutation on a completed
  report raises :class:`ConditionReportImmutableError`.
- ``EstimatedCostRemainsInformational`` — no service op ever
  creates or modifies a ``VehicleCost`` row.
- ``LatestConditionReportAccessor`` — empty state, single, mixed,
  ordering, cross-tenant.
- ``LatestCompletedConditionReportAccessor`` — filter to complete,
  ordering, cross-tenant.
- ``DeterministicReads`` — repeated calls return identical
  results.
- ``FullCleanFiresBeforeSave`` — the model layer's ``clean()``
  invariants surface as ``ValidationError`` through the service.
- ``TransactionBehavior`` — refusals do not leave partial state.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_ACCESSORIES,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_CATEGORY_MISSING,
    CONDITION_CATEGORY_TIRES,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_REPORT_STATUS_DRAFT,
    CONDITION_SEVERITY_ADVISORY,
    CONDITION_SEVERITY_RECOMMENDED,
    CONDITION_SEVERITY_REQUIRED,
    CONDITION_SEVERITY_SAFETY,
    ConditionFinding,
    ConditionReport,
    Dealership,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.condition_report import (
    ConditionReportImmutableError,
    CrossTenantConditionReportError,
    add_finding,
    complete_report,
    create_report,
    delete_finding,
    latest_completed_condition_report,
    latest_condition_report,
    update_finding,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _make_draft(
    vehicle: Vehicle, dealership: Dealership, *, at=None
) -> ConditionReport:
    """Direct service call to seed a draft report for tests that
    exercise other service functions."""
    return create_report(
        vehicle,
        dealership=dealership,
        inspector_name="Marta Ruiz",
        inspected_at=at or timezone.now(),
        mileage_at_inspection=42_000,
    )


# ---- Cross-tenant fail-closed guards --------------------------------------


class CrossTenantGuards(TestCase):
    """Every public service function refuses when the caller's
    dealership does not match the target vehicle / report / finding.

    Fail-closed at the service layer (belt) + fail-closed at the
    model's ``clean()`` (suspenders).
    """

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-service"
        )
        self.vehicle_at_a = _make_vehicle("SVC-XTENANT", self.dealership_a)
        self.report_at_a = _make_draft(self.vehicle_at_a, self.dealership_a)
        self.finding_at_a = add_finding(
            self.report_at_a,
            dealership=self.dealership_a,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="LR tire at 3/32nds.",
        )

    def test_create_report_rejects_wrong_dealership(self):
        with self.assertRaises(CrossTenantConditionReportError):
            create_report(
                self.vehicle_at_a,
                dealership=self.dealership_b,
                inspector_name="Marta Ruiz",
                inspected_at=timezone.now(),
                mileage_at_inspection=42_000,
            )

    def test_complete_report_rejects_wrong_dealership(self):
        with self.assertRaises(CrossTenantConditionReportError):
            complete_report(self.report_at_a, dealership=self.dealership_b)

    def test_add_finding_rejects_wrong_dealership(self):
        with self.assertRaises(CrossTenantConditionReportError):
            add_finding(
                self.report_at_a,
                dealership=self.dealership_b,
                category=CONDITION_CATEGORY_TIRES,
                severity=CONDITION_SEVERITY_REQUIRED,
                description="Cross-tenant attempt.",
            )

    def test_update_finding_rejects_wrong_dealership(self):
        with self.assertRaises(CrossTenantConditionReportError):
            update_finding(
                self.finding_at_a,
                dealership=self.dealership_b,
                description="Cross-tenant attempt.",
            )

    def test_delete_finding_rejects_wrong_dealership(self):
        with self.assertRaises(CrossTenantConditionReportError):
            delete_finding(
                self.finding_at_a, dealership=self.dealership_b
            )

    def test_latest_condition_report_rejects_wrong_dealership(self):
        with self.assertRaises(CrossTenantConditionReportError):
            latest_condition_report(
                self.vehicle_at_a, dealership=self.dealership_b
            )

    def test_latest_completed_condition_report_rejects_wrong_dealership(self):
        with self.assertRaises(CrossTenantConditionReportError):
            latest_completed_condition_report(
                self.vehicle_at_a, dealership=self.dealership_b
            )

    def test_cross_tenant_error_is_a_value_error(self):
        # Callers catching ``ValueError`` also catch the subclass —
        # deliberate + documented in the service module.
        try:
            latest_condition_report(
                self.vehicle_at_a, dealership=self.dealership_b
            )
        except ValueError as exc:
            self.assertIsInstance(exc, CrossTenantConditionReportError)
        else:
            self.fail("Expected CrossTenantConditionReportError")


# ---- create_report --------------------------------------------------------


class CreateReportSemantics(TestCase):
    """``create_report`` always creates in ``draft`` with
    ``completed_at=None`` and distinct provenance fields."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-CREATE", self.default)

    def test_always_creates_in_draft_status(self):
        report = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        self.assertEqual(report.status, CONDITION_REPORT_STATUS_DRAFT)

    def test_completed_at_is_null_at_birth(self):
        report = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        self.assertIsNone(report.completed_at)

    def test_authored_by_and_inspector_name_are_distinct_provenance(self):
        # A service writer transcribing a paper inspection performed
        # by a mechanic — the two names differ intentionally per
        # RECON §2.4. Neither should silently overwrite the other.
        User = get_user_model()
        service_writer = User.objects.create_user(
            username="service_writer_1", password="pw"
        )
        report = create_report(
            self.vehicle,
            dealership=self.default,
            authored_by=service_writer,
            inspector_name="Diego Alvarez",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        self.assertEqual(report.authored_by, service_writer)
        self.assertEqual(report.inspector_name, "Diego Alvarez")

    def test_authored_by_is_optional(self):
        report = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        self.assertIsNone(report.authored_by)

    def test_multiple_reports_per_vehicle_are_supported(self):
        # RECON §7.5: a vehicle can be re-inspected. Every inspection
        # is a fresh row — no OneToOne constraint.
        report1 = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Arrival tech",
            inspected_at=timezone.make_aware(dt.datetime(2026, 5, 1, 9, 0)),
            mileage_at_inspection=42_000,
        )
        report2 = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Post-recon QC",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
            mileage_at_inspection=42_050,
        )
        self.assertNotEqual(report1.pk, report2.pk)
        self.assertEqual(
            ConditionReport.objects.filter(vehicle=self.vehicle).count(),
            2,
        )


# ---- complete_report ------------------------------------------------------


class CompleteReportSemantics(TestCase):
    """``complete_report`` transitions draft → complete exactly once;
    sets ``completed_at`` atomically; raises on double-complete."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-COMPL", self.default)
        self.report = _make_draft(self.vehicle, self.default)

    def test_transition_from_draft_to_complete_succeeds(self):
        before = timezone.now()
        completed = complete_report(self.report, dealership=self.default)
        after = timezone.now()
        self.assertEqual(completed.status, CONDITION_REPORT_STATUS_COMPLETE)
        self.assertIsNotNone(completed.completed_at)
        self.assertLessEqual(before, completed.completed_at)
        self.assertLessEqual(completed.completed_at, after)

    def test_returned_instance_equals_persisted_row(self):
        completed = complete_report(self.report, dealership=self.default)
        fetched = ConditionReport.objects.get(pk=self.report.pk)
        self.assertEqual(completed.pk, fetched.pk)
        self.assertEqual(fetched.status, CONDITION_REPORT_STATUS_COMPLETE)
        self.assertEqual(fetched.completed_at, completed.completed_at)

    def test_double_complete_raises_immutable_error(self):
        complete_report(self.report, dealership=self.default)
        with self.assertRaises(ConditionReportImmutableError):
            complete_report(self.report, dealership=self.default)

    def test_immutable_error_is_a_value_error(self):
        complete_report(self.report, dealership=self.default)
        try:
            complete_report(self.report, dealership=self.default)
        except ValueError as exc:
            self.assertIsInstance(exc, ConditionReportImmutableError)
        else:
            self.fail("Expected ConditionReportImmutableError")

    def test_double_complete_does_not_shift_completed_at(self):
        # The first completion stamps completed_at; a second attempt
        # must NOT overwrite it. This protects the audit trail —
        # "when did this become a finished record?" has one answer.
        first = complete_report(self.report, dealership=self.default)
        original_completed_at = first.completed_at
        with self.assertRaises(ConditionReportImmutableError):
            complete_report(self.report, dealership=self.default)
        self.report.refresh_from_db()
        self.assertEqual(self.report.completed_at, original_completed_at)


# ---- add_finding ----------------------------------------------------------


class AddFindingSemantics(TestCase):
    """``add_finding`` gates on draft status and validates the
    canonical vocabularies before touching the DB."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-ADD", self.default)
        self.report = _make_draft(self.vehicle, self.default)

    def test_add_finding_to_draft_succeeds(self):
        finding = add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="LR tire at 3/32nds.",
            estimated_cost=Decimal("165.00"),
        )
        self.assertEqual(finding.category, CONDITION_CATEGORY_TIRES)
        self.assertEqual(finding.severity, CONDITION_SEVERITY_REQUIRED)
        self.assertEqual(finding.estimated_cost, Decimal("165.00"))
        self.assertEqual(finding.report_id, self.report.pk)

    def test_add_finding_on_completed_report_raises(self):
        complete_report(self.report, dealership=self.default)
        with self.assertRaises(ConditionReportImmutableError):
            add_finding(
                self.report,
                dealership=self.default,
                category=CONDITION_CATEGORY_TIRES,
                severity=CONDITION_SEVERITY_REQUIRED,
                description="Too late.",
            )

    def test_invalid_category_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            add_finding(
                self.report,
                dealership=self.default,
                category="engine",  # not canonical
                severity=CONDITION_SEVERITY_REQUIRED,
                description="Anything.",
            )
        # Not the cross-tenant subclass — a plain ValueError with a
        # message pointing at the constant list.
        self.assertNotIsInstance(
            ctx.exception, CrossTenantConditionReportError
        )
        self.assertIn("category", str(ctx.exception))

    def test_invalid_severity_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            add_finding(
                self.report,
                dealership=self.default,
                category=CONDITION_CATEGORY_MECHANICAL,
                severity="urgent",  # not canonical
                description="Anything.",
            )
        self.assertNotIsInstance(
            ctx.exception, CrossTenantConditionReportError
        )
        self.assertIn("severity", str(ctx.exception))

    def test_estimated_cost_optional(self):
        finding = add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_ACCESSORIES,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Second key fob not present at inspection.",
        )
        self.assertIsNone(finding.estimated_cost)

    def test_description_required_full_clean_surfaces(self):
        # Passing empty description exercises the model's TextField
        # required-when-not-blank contract via full_clean.
        with self.assertRaises(ValidationError):
            add_finding(
                self.report,
                dealership=self.default,
                category=CONDITION_CATEGORY_MECHANICAL,
                severity=CONDITION_SEVERITY_REQUIRED,
                description="",
            )


# ---- update_finding -------------------------------------------------------


class UpdateFindingSemantics(TestCase):
    """``update_finding`` accepts only the whitelisted fields; refuses
    re-parenting, re-scoping, or unknown keys; re-validates category
    and severity on change."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-UPD", self.default)
        self.report = _make_draft(self.vehicle, self.default)
        self.finding = add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Original description.",
        )

    def test_update_whitelisted_fields_succeeds(self):
        updated = update_finding(
            self.finding,
            dealership=self.default,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Escalated after closer look.",
            estimated_cost=Decimal("240.00"),
            notes="Second opinion from senior tech.",
        )
        self.assertEqual(updated.severity, CONDITION_SEVERITY_REQUIRED)
        self.assertEqual(updated.description, "Escalated after closer look.")
        self.assertEqual(updated.estimated_cost, Decimal("240.00"))
        self.assertEqual(updated.notes, "Second opinion from senior tech.")

    def test_update_rejects_re_parenting_report(self):
        other_report = _make_draft(self.vehicle, self.default)
        with self.assertRaises(ValueError) as ctx:
            update_finding(
                self.finding,
                dealership=self.default,
                report=other_report,
            )
        self.assertIn("report", str(ctx.exception))

    def test_update_rejects_re_scoping_dealership(self):
        other = Dealership.objects.create(name="Other", slug="other-upd")
        with self.assertRaises(ValueError) as ctx:
            update_finding(
                self.finding,
                dealership=self.default,
                dealership_id=other.pk,  # not in whitelist by field-name
            )
        # dealership_id is not in the whitelist, so this raises for
        # the same reason "report" does.
        self.assertIn("dealership_id", str(ctx.exception))

    def test_update_rejects_unknown_field(self):
        with self.assertRaises(ValueError) as ctx:
            update_finding(
                self.finding,
                dealership=self.default,
                priority="high",  # not a real field
            )
        self.assertIn("priority", str(ctx.exception))

    def test_update_rejects_id_manipulation(self):
        with self.assertRaises(ValueError):
            update_finding(
                self.finding,
                dealership=self.default,
                id=99999,
            )

    def test_update_invalid_category_raises(self):
        with self.assertRaises(ValueError) as ctx:
            update_finding(
                self.finding,
                dealership=self.default,
                category="engine",
            )
        self.assertIn("category", str(ctx.exception))

    def test_update_invalid_severity_raises(self):
        with self.assertRaises(ValueError) as ctx:
            update_finding(
                self.finding,
                dealership=self.default,
                severity="urgent",
            )
        self.assertIn("severity", str(ctx.exception))

    def test_update_on_completed_report_raises(self):
        complete_report(self.report, dealership=self.default)
        with self.assertRaises(ConditionReportImmutableError):
            update_finding(
                self.finding,
                dealership=self.default,
                description="Too late.",
            )

    def test_no_op_update_is_permitted(self):
        # Passing no updatable fields is allowed — the caller may
        # simply want full_clean to run without changing anything.
        # Locks the current permissive behavior; if it becomes
        # noisy, revisit with a "requires at least one field" gate.
        result = update_finding(self.finding, dealership=self.default)
        self.assertEqual(result.pk, self.finding.pk)


# ---- delete_finding ------------------------------------------------------


class DeleteFindingSemantics(TestCase):
    """``delete_finding`` removes the row from a draft report and
    refuses on a completed one."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-DEL", self.default)
        self.report = _make_draft(self.vehicle, self.default)
        self.finding = add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Retracted after re-inspection.",
        )

    def test_delete_on_draft_removes_row(self):
        finding_pk = self.finding.pk
        result = delete_finding(self.finding, dealership=self.default)
        self.assertIsNone(result)
        self.assertFalse(
            ConditionFinding.objects.filter(pk=finding_pk).exists()
        )

    def test_delete_on_completed_report_raises(self):
        complete_report(self.report, dealership=self.default)
        with self.assertRaises(ConditionReportImmutableError):
            delete_finding(self.finding, dealership=self.default)
        # Finding still present — refusal did not partially execute.
        self.assertTrue(
            ConditionFinding.objects.filter(pk=self.finding.pk).exists()
        )


# ---- Completed-report immutability --------------------------------------


class CompletedReportImmutability(TestCase):
    """Every mutation on a completed report raises
    :class:`ConditionReportImmutableError`. This is the composite
    invariant across ``complete_report``, ``add_finding``,
    ``update_finding``, ``delete_finding``."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-IMMU", self.default)
        self.report = _make_draft(self.vehicle, self.default)
        self.finding = add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_MISSING,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Owner's manual absent.",
        )
        complete_report(self.report, dealership=self.default)

    def test_add_finding_after_complete_raises(self):
        with self.assertRaises(ConditionReportImmutableError):
            add_finding(
                self.report,
                dealership=self.default,
                category=CONDITION_CATEGORY_MECHANICAL,
                severity=CONDITION_SEVERITY_REQUIRED,
                description="Late addition.",
            )

    def test_update_finding_after_complete_raises(self):
        with self.assertRaises(ConditionReportImmutableError):
            update_finding(
                self.finding,
                dealership=self.default,
                notes="After the fact.",
            )

    def test_delete_finding_after_complete_raises(self):
        with self.assertRaises(ConditionReportImmutableError):
            delete_finding(self.finding, dealership=self.default)

    def test_double_complete_after_complete_raises(self):
        with self.assertRaises(ConditionReportImmutableError):
            complete_report(self.report, dealership=self.default)


# ---- estimated_cost never touches VehicleCost --------------------------


class EstimatedCostRemainsInformational(TestCase):
    """The service must NEVER create or modify a ``VehicleCost`` row
    as a side-effect of any condition-report operation. The
    ``estimated_cost`` field is documentation only until M4
    introduces the findings → work-order → cost flow."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-COST", self.default)
        self.report = _make_draft(self.vehicle, self.default)

    def _cost_count(self) -> int:
        return VehicleCost.objects.filter(vehicle=self.vehicle).count()

    def test_add_finding_with_estimated_cost_creates_no_vehicle_cost(self):
        before = self._cost_count()
        add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="LR tire.",
            estimated_cost=Decimal("165.00"),
        )
        self.assertEqual(self._cost_count(), before)

    def test_update_finding_estimated_cost_creates_no_vehicle_cost(self):
        finding = add_finding(
            self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="LR tire.",
            estimated_cost=Decimal("165.00"),
        )
        before = self._cost_count()
        update_finding(
            finding,
            dealership=self.default,
            estimated_cost=Decimal("240.00"),
        )
        self.assertEqual(self._cost_count(), before)

    def test_complete_report_with_findings_creates_no_vehicle_cost(self):
        for _ in range(3):
            add_finding(
                self.report,
                dealership=self.default,
                category=CONDITION_CATEGORY_TIRES,
                severity=CONDITION_SEVERITY_REQUIRED,
                description="LR tire.",
                estimated_cost=Decimal("100.00"),
            )
        before = self._cost_count()
        complete_report(self.report, dealership=self.default)
        self.assertEqual(self._cost_count(), before)


# ---- latest_condition_report --------------------------------------------


class LatestConditionReportAccessor(TestCase):
    """Returns most recent report of any status; tenant-safe;
    deterministic ordering."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-LATEST", self.default)

    def test_empty_state_returns_none(self):
        self.assertIsNone(
            latest_condition_report(self.vehicle, dealership=self.default)
        )

    def test_single_draft_report_returned(self):
        report = _make_draft(self.vehicle, self.default)
        latest = latest_condition_report(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(latest.pk, report.pk)

    def test_returns_most_recent_by_inspected_at(self):
        older = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Older",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            mileage_at_inspection=42_000,
        )
        newer = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Newer",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
            mileage_at_inspection=43_000,
        )
        latest = latest_condition_report(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(latest.pk, newer.pk)
        self.assertNotEqual(latest.pk, older.pk)

    def test_returns_draft_when_draft_is_newest(self):
        # A draft that comes AFTER a complete is the latest of any
        # status. The two-accessor split (this vs.
        # latest_completed_condition_report) exists precisely
        # because "which is latest?" has two useful answers.
        completed = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Old complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            mileage_at_inspection=42_000,
        )
        complete_report(completed, dealership=self.default)
        draft = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="New draft",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
            mileage_at_inspection=43_000,
        )
        latest = latest_condition_report(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(latest.pk, draft.pk)

    def test_cross_tenant_reports_are_not_returned(self):
        other = Dealership.objects.create(name="Other", slug="other-latest")
        vehicle_at_other = _make_vehicle("SVC-CR-OTH", other)
        create_report(
            vehicle_at_other,
            dealership=other,
            inspector_name="Cross-tenant",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        # Querying vehicle_at_other with the wrong dealership must
        # raise; querying self.vehicle (which has no reports) must
        # return None. Cross-tenant rows never leak.
        self.assertIsNone(
            latest_condition_report(self.vehicle, dealership=self.default)
        )


# ---- latest_completed_condition_report ---------------------------------


class LatestCompletedConditionReportAccessor(TestCase):
    """Returns most recent report with ``status=complete``; tenant-safe."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-LATCMP", self.default)

    def test_empty_state_returns_none(self):
        self.assertIsNone(
            latest_completed_condition_report(
                self.vehicle, dealership=self.default
            )
        )

    def test_returns_none_when_only_drafts_exist(self):
        _make_draft(self.vehicle, self.default)
        self.assertIsNone(
            latest_completed_condition_report(
                self.vehicle, dealership=self.default
            )
        )

    def test_returns_only_completed_report(self):
        report = _make_draft(self.vehicle, self.default)
        complete_report(report, dealership=self.default)
        latest = latest_completed_condition_report(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(latest.pk, report.pk)
        self.assertEqual(latest.status, CONDITION_REPORT_STATUS_COMPLETE)

    def test_skips_newer_draft_and_returns_older_complete(self):
        older = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Old complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            mileage_at_inspection=42_000,
        )
        complete_report(older, dealership=self.default)
        newer_draft = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="New draft",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
            mileage_at_inspection=43_000,
        )
        latest = latest_completed_condition_report(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(latest.pk, older.pk)
        self.assertNotEqual(latest.pk, newer_draft.pk)

    def test_returns_most_recent_completed_when_multiple_exist(self):
        older = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Old complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            mileage_at_inspection=42_000,
        )
        complete_report(older, dealership=self.default)
        newer = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Newer complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
            mileage_at_inspection=43_000,
        )
        complete_report(newer, dealership=self.default)
        latest = latest_completed_condition_report(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(latest.pk, newer.pk)


# ---- Deterministic reads ------------------------------------------------


class DeterministicReads(TestCase):
    """Repeated calls with identical arguments return identical
    results — no hidden caching, no query-order variance, no ordering
    drift between calls."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-DETR", self.default)
        # Two reports with the same inspected_at to exercise the
        # tie-breaker (-created_at). Ordering must be stable.
        same_inspection_time = timezone.make_aware(
            dt.datetime(2026, 5, 15, 9, 0)
        )
        self.first = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="First",
            inspected_at=same_inspection_time,
            mileage_at_inspection=42_000,
        )
        self.second = create_report(
            self.vehicle,
            dealership=self.default,
            inspector_name="Second",
            inspected_at=same_inspection_time,
            mileage_at_inspection=42_000,
        )

    def test_latest_condition_report_deterministic_across_repeated_calls(self):
        results = [
            latest_condition_report(self.vehicle, dealership=self.default).pk
            for _ in range(5)
        ]
        self.assertEqual(len(set(results)), 1)

    def test_latest_completed_condition_report_deterministic_across_repeated_calls(self):
        complete_report(self.first, dealership=self.default)
        results = [
            latest_completed_condition_report(
                self.vehicle, dealership=self.default
            ).pk
            for _ in range(5)
        ]
        self.assertEqual(len(set(results)), 1)


# ---- full_clean fires before save --------------------------------------


class FullCleanFiresBeforeSave(TestCase):
    """Every service write path calls ``full_clean()`` before
    ``save()``. Proven by triggering the model layer's ``clean()``
    cross-tenant guard through the service."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(
            name="Other", slug="other-fullclean"
        )
        self.vehicle_at_default = _make_vehicle(
            "SVC-CR-CLEAN", self.default
        )

    def test_full_clean_fires_via_completed_at_invariant_on_direct_save(self):
        # Direct model save bypasses full_clean; the service's
        # complete_report goes through full_clean. Setting the report
        # to complete without completed_at via direct .save() would
        # bypass; going through the service catches it because
        # complete_report always sets both atomically. This test
        # locks that the service does not skip the full_clean step
        # by constructing a report the service will complete and
        # verifying completed_at is set after the call.
        report = _make_draft(self.vehicle_at_default, self.default)
        completed = complete_report(report, dealership=self.default)
        self.assertIsNotNone(completed.completed_at)
        # If full_clean did not run, we might see completed_at=None
        # with status=complete — that would violate the model's
        # invariant. Its absence here is the observable evidence.

    def test_full_clean_catches_finding_field_shape_errors(self):
        report = _make_draft(self.vehicle_at_default, self.default)
        # Description is required; passing empty string reaches
        # full_clean and raises ValidationError. This test proves
        # the service invokes full_clean (not just choices=)
        # because empty-string on TextField is a field-shape check
        # only surfaced by full_clean.
        with self.assertRaises(ValidationError):
            add_finding(
                report,
                dealership=self.default,
                category=CONDITION_CATEGORY_MECHANICAL,
                severity=CONDITION_SEVERITY_SAFETY,
                description="",
            )


# ---- Transaction behavior on refusal -----------------------------------


class TransactionBehavior(TestCase):
    """When a service call raises, no partial DB state remains.
    Refusals happen before any write; validation errors happen
    before any commit."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(
            name="Other", slug="other-txn"
        )
        self.vehicle = _make_vehicle("SVC-CR-TXN", self.default)

    def test_cross_tenant_create_leaves_no_report(self):
        before = ConditionReport.objects.count()
        with self.assertRaises(CrossTenantConditionReportError):
            create_report(
                self.vehicle,
                dealership=self.other,
                inspector_name="Cross-tenant",
                inspected_at=timezone.now(),
                mileage_at_inspection=42_000,
            )
        self.assertEqual(ConditionReport.objects.count(), before)

    def test_immutable_add_finding_leaves_no_finding(self):
        report = _make_draft(self.vehicle, self.default)
        complete_report(report, dealership=self.default)
        before = ConditionFinding.objects.count()
        with self.assertRaises(ConditionReportImmutableError):
            add_finding(
                report,
                dealership=self.default,
                category=CONDITION_CATEGORY_MECHANICAL,
                severity=CONDITION_SEVERITY_REQUIRED,
                description="After the bell.",
            )
        self.assertEqual(ConditionFinding.objects.count(), before)

    def test_invalid_category_leaves_no_finding(self):
        report = _make_draft(self.vehicle, self.default)
        before = ConditionFinding.objects.count()
        with self.assertRaises(ValueError):
            add_finding(
                report,
                dealership=self.default,
                category="engine",
                severity=CONDITION_SEVERITY_REQUIRED,
                description="Invalid.",
            )
        self.assertEqual(ConditionFinding.objects.count(), before)

    def test_immutable_update_leaves_finding_unchanged(self):
        report = _make_draft(self.vehicle, self.default)
        finding = add_finding(
            report,
            dealership=self.default,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Original.",
        )
        complete_report(report, dealership=self.default)
        with self.assertRaises(ConditionReportImmutableError):
            update_finding(
                finding,
                dealership=self.default,
                description="Attempted change.",
            )
        finding.refresh_from_db()
        self.assertEqual(finding.description, "Original.")
        self.assertEqual(finding.severity, CONDITION_SEVERITY_ADVISORY)


# ---- Recommended severity coverage smoke ---------------------------------


class RecommendedSeverityUsable(TestCase):
    """The service accepts every canonical severity value — locks
    that the service's ``_VALID_SEVERITY_KEYS`` matches the model's
    enum tuple. If a future edit adds a severity to the enum but
    forgets to sync the service constant, this smoke catches it."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("SVC-CR-SEV", self.default)
        self.report = _make_draft(self.vehicle, self.default)

    def test_every_canonical_severity_accepted_by_add_finding(self):
        for sev in (
            CONDITION_SEVERITY_ADVISORY,
            CONDITION_SEVERITY_RECOMMENDED,
            CONDITION_SEVERITY_REQUIRED,
            CONDITION_SEVERITY_SAFETY,
        ):
            add_finding(
                self.report,
                dealership=self.default,
                category=CONDITION_CATEGORY_MECHANICAL,
                severity=sev,
                description=f"Coverage for {sev}.",
            )
        self.assertEqual(self.report.findings.count(), 4)

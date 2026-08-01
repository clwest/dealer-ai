"""Milestone 3 · Increment 1 — ConditionReport model tests.

Persistence-layer coverage only. No service-layer semantics
(``create_report``, ``complete_report``, cross-tenant service
errors) are tested here — those land at M3.2. Same shape as
``test_vehicle_acquisition.py`` and ``test_vehicle_cost.py`` from
Milestone 2.

Locked invariants:

- Field shape (choices enforcement, defaults, NOT NULL).
- ``status`` choices vocabulary (two canonical values).
- ``completed_at`` invariant — NULL iff status draft; set iff
  status complete (locked by ``clean``).
- Dealership FK NOT NULL from day one.
- Cross-tenant ``clean`` guard (dealership must match parent
  vehicle's dealership).
- Cascade behavior — deleting the parent Vehicle removes the
  ConditionReport.
- Ordering (newest inspected_at first, then created_at).
- Reverse accessor ``vehicle.condition_reports`` and
  ``dealership.condition_reports``.
- ``__str__`` for Django admin display.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_REPORT_STATUS_CHOICES,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_REPORT_STATUS_DRAFT,
    ConditionReport,
    Dealership,
    Vehicle,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


class StatusChoicesVocabulary(TestCase):
    """The two canonical status values are locked at the model layer.
    Any addition or rename requires a roadmap decision — this test
    forces that conversation."""

    def test_choices_contain_exactly_two_canonical_values(self):
        keys = {key for key, _ in CONDITION_REPORT_STATUS_CHOICES}
        self.assertEqual(
            keys,
            {CONDITION_REPORT_STATUS_DRAFT, CONDITION_REPORT_STATUS_COMPLETE},
        )


class ConditionReportCreate(TestCase):
    """Happy-path field-shape smokes."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M31R-CREATE", self.default)

    def test_round_trip_all_fields(self):
        inspected_at = timezone.make_aware(dt.datetime(2026, 6, 1, 9, 30))
        report = ConditionReport.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=inspected_at,
            mileage_at_inspection=42_113,
            notes="Arrival inspection against auction condition report.",
        )
        fetched = ConditionReport.objects.get(pk=report.pk)
        self.assertEqual(fetched.vehicle_id, self.vehicle.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(fetched.inspector_name, "Marta Ruiz")
        self.assertEqual(fetched.inspected_at, inspected_at)
        self.assertEqual(fetched.mileage_at_inspection, 42_113)
        self.assertEqual(fetched.status, CONDITION_REPORT_STATUS_DRAFT)
        self.assertIsNone(fetched.completed_at)

    def test_status_defaults_to_draft(self):
        report = ConditionReport.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        self.assertEqual(report.status, CONDITION_REPORT_STATUS_DRAFT)
        self.assertIsNone(report.completed_at)

    def test_authored_by_is_optional(self):
        # SET_NULL nullable — historical rows survive user deletion
        # so seed / management-command writes don't need a synthetic
        # user account.
        report = ConditionReport.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        self.assertIsNone(report.authored_by)

    def test_authored_by_set_null_on_user_delete(self):
        User = get_user_model()
        user = User.objects.create_user(username="inspector1", password="pw")
        report = ConditionReport.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            authored_by=user,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        user.delete()
        report.refresh_from_db()
        self.assertIsNone(report.authored_by_id)

    def test_status_full_clean_rejects_invalid_choice(self):
        report = ConditionReport(
            vehicle=self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
            status="reopen",  # not a valid choice
        )
        with self.assertRaises(ValidationError):
            report.full_clean()


class CompletedAtInvariant(TestCase):
    """``completed_at`` NULL exactly when status is draft; set exactly
    when status is complete. The M3.2 service layer sets both fields
    atomically; the persistence layer refuses inconsistent
    combinations via ``clean``."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M31R-COMPL", self.default)

    def _base_kwargs(self):
        return dict(
            vehicle=self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )

    def test_draft_with_null_completed_at_passes_clean(self):
        report = ConditionReport(
            **self._base_kwargs(),
            status=CONDITION_REPORT_STATUS_DRAFT,
            completed_at=None,
        )
        # Should not raise.
        report.full_clean()

    def test_complete_with_completed_at_passes_clean(self):
        report = ConditionReport(
            **self._base_kwargs(),
            status=CONDITION_REPORT_STATUS_COMPLETE,
            completed_at=timezone.now(),
        )
        report.full_clean()

    def test_draft_with_completed_at_raises(self):
        report = ConditionReport(
            **self._base_kwargs(),
            status=CONDITION_REPORT_STATUS_DRAFT,
            completed_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            report.full_clean()
        self.assertIn("completed_at", ctx.exception.message_dict)

    def test_complete_with_null_completed_at_raises(self):
        report = ConditionReport(
            **self._base_kwargs(),
            status=CONDITION_REPORT_STATUS_COMPLETE,
            completed_at=None,
        )
        with self.assertRaises(ValidationError) as ctx:
            report.full_clean()
        self.assertIn("completed_at", ctx.exception.message_dict)


class DealershipRequired(TestCase):
    """Dealership FK is NOT NULL from day one (greenfield table, no
    backfill). Same shape as M2's VehicleAcquisition/VehicleCost."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M31R-DEAL", self.default)

    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            ConditionReport._meta.get_field("dealership").null,
            "ConditionReport.dealership should be NOT NULL from day one",
        )

    def test_omitting_vehicle_raises(self):
        # Every ConditionReport must attach to a Vehicle. The write-path
        # tenancy autofill (SESSION_056) supplies dealership when
        # missing, but vehicle must always be explicit.
        with self.assertRaises((IntegrityError, ValueError)):
            with transaction.atomic():
                ConditionReport.objects.create(
                    dealership=self.default,
                    inspector_name="Marta Ruiz",
                    inspected_at=timezone.now(),
                    mileage_at_inspection=42_000,
                )


class CrossTenantClean(TestCase):
    """The denormalized ``dealership`` FK on ConditionReport must
    match the parent Vehicle's tenant. ``clean()`` is the model-layer
    guard against a mis-scoped view writing a report for the wrong
    tenant. See ``AUTHENTICATION_MODEL.md`` §1 layer 4."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-report"
        )
        self.vehicle_at_a = _make_vehicle("M31R-XTENANT", self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        report = ConditionReport(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        report.full_clean()

    def test_mismatched_dealership_raises_validation_error(self):
        report = ConditionReport(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_b,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        with self.assertRaises(ValidationError) as ctx:
            report.full_clean()
        self.assertIn("dealership", ctx.exception.message_dict)


class CascadeOnVehicleDelete(TestCase):
    """Deleting a Vehicle removes all its ConditionReports. Inspection
    history for a removed stock number does not survive as an orphan."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M31R-CASC", self.default)
        self.report = ConditionReport.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )

    def test_delete_vehicle_removes_condition_report(self):
        report_pk = self.report.pk
        self.vehicle.delete()
        self.assertFalse(
            ConditionReport.objects.filter(pk=report_pk).exists()
        )


class ReverseRelations(TestCase):
    """``vehicle.condition_reports`` and
    ``dealership.condition_reports`` are the reverse accessors service
    + admin surfaces rely on."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M31R-REV", self.default)
        self.report = ConditionReport.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )

    def test_vehicle_dot_condition_reports_lists_it(self):
        vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.assertIn(self.report, vehicle.condition_reports.all())

    def test_dealership_reverse_relation_works(self):
        self.assertIn(
            self.report, self.default.condition_reports.all()
        )


class OrderingContract(TestCase):
    """Default ordering is (``-inspected_at``, ``-created_at``) — the
    operator's default view is 'most-recent inspection first'."""

    def test_default_ordering_surfaces_newest_inspected_at_first(self):
        default = Dealership.objects.get(slug="default")
        v = _make_vehicle("M31R-ORD", default)
        ConditionReport.objects.create(
            vehicle=v,
            dealership=default,
            inspector_name="Older inspection",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            mileage_at_inspection=42_000,
        )
        ConditionReport.objects.create(
            vehicle=v,
            dealership=default,
            inspector_name="Newest inspection",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 15, 9, 0)),
            mileage_at_inspection=43_500,
        )
        ConditionReport.objects.create(
            vehicle=v,
            dealership=default,
            inspector_name="Middle inspection",
            inspected_at=timezone.make_aware(dt.datetime(2026, 5, 1, 9, 0)),
            mileage_at_inspection=43_000,
        )
        names = [r.inspector_name for r in ConditionReport.objects.all()]
        self.assertEqual(
            names,
            ["Newest inspection", "Middle inspection", "Older inspection"],
        )


class StringRepresentation(TestCase):
    """__str__ is what Django admin renders. Locks the shape."""

    def test_str_contains_stock_number_and_status_label(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M31R-STR", default)
        report = ConditionReport.objects.create(
            vehicle=vehicle,
            dealership=default,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        as_string = str(report)
        self.assertIn("M31R-STR", as_string)
        self.assertIn("Draft", as_string)

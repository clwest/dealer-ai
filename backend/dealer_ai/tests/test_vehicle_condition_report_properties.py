"""Milestone 3 · Increment 3 — Vehicle condition-report read-model tests.

Read-model coverage only. No service-layer semantics re-tested (M3.2
locks those). Focus:

- The two ``@property`` accessors on ``Vehicle`` return exactly what
  the service returns, with no filtering, ordering, or aggregation
  added at the model layer.
- Every property access resolves the tenant from ``self.dealership``.
- Cross-tenant vehicles never leak through.
- Query behavior is locked: exactly one query per property access
  when the ``dealership`` FK is prefetched (the shape production
  callers should use).
- No caching — repeated reads on the same instance fire the query
  every time. Verified so future work knows the baseline before
  promoting to ``@cached_property``.
- Delegation to the service is proven by mocking the service
  function and asserting call arguments (rather than re-testing
  service behavior exhaustively).

Test class map:

- ``LatestConditionReport`` — no reports, one draft, one complete,
  multiple drafts, multiple complete, mixed, newest-draft-wins,
  tenant isolation, deterministic repeated reads.
- ``LatestCompletedConditionReport`` — no completed, ignores drafts,
  newest complete wins over older, tenant isolation, deterministic
  repeated reads.
- ``VehicleContract`` — delegation-via-mock, result-passthrough,
  no-mutation, ``assertNumQueries(1)`` when dealership prefetched.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_REPORT_STATUS_DRAFT,
    ConditionReport,
    Dealership,
    Vehicle,
)
from dealer_ai.services.condition_report import (
    complete_report,
    create_report,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _seed_report(
    vehicle: Vehicle,
    dealership: Dealership,
    *,
    inspector_name: str,
    inspected_at,
    complete: bool = False,
) -> ConditionReport:
    """Create a report via the service; optionally complete it in
    the same call so tests express state declaratively."""
    report = create_report(
        vehicle,
        dealership=dealership,
        inspector_name=inspector_name,
        inspected_at=inspected_at,
        mileage_at_inspection=42_000,
    )
    if complete:
        complete_report(report, dealership=dealership)
    return report


# ---- latest_condition_report ---------------------------------------------


class LatestConditionReport(TestCase):
    """The ``latest_condition_report`` property returns the most
    recent report of any status, or ``None`` when the vehicle has no
    reports. Ordering is the underlying service function's
    ``(-inspected_at, -created_at)`` sort."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M33R-LATEST", self.default)

    def test_returns_none_when_no_reports_exist(self):
        self.assertIsNone(self.vehicle.latest_condition_report)

    def test_returns_the_only_draft_report(self):
        report = _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Marta",
            inspected_at=timezone.now(),
        )
        result = self.vehicle.latest_condition_report
        self.assertIsNotNone(result)
        self.assertEqual(result.pk, report.pk)
        self.assertEqual(result.status, CONDITION_REPORT_STATUS_DRAFT)

    def test_returns_the_only_completed_report(self):
        report = _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Marta",
            inspected_at=timezone.now(),
            complete=True,
        )
        result = self.vehicle.latest_condition_report
        self.assertEqual(result.pk, report.pk)
        self.assertEqual(result.status, CONDITION_REPORT_STATUS_COMPLETE)

    def test_returns_newest_when_multiple_drafts_exist(self):
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Older draft",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
        )
        newer = _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Newer draft",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
        )
        result = self.vehicle.latest_condition_report
        self.assertEqual(result.pk, newer.pk)

    def test_returns_newest_when_multiple_completes_exist(self):
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Older complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            complete=True,
        )
        newer = _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Newer complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
            complete=True,
        )
        result = self.vehicle.latest_condition_report
        self.assertEqual(result.pk, newer.pk)

    def test_mixed_state_returns_newest_regardless_of_status(self):
        # Older complete + newer draft → newer draft wins because
        # ``latest_condition_report`` does not filter on status.
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Older complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            complete=True,
        )
        newer_draft = _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Newer draft",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
        )
        result = self.vehicle.latest_condition_report
        self.assertEqual(result.pk, newer_draft.pk)
        self.assertEqual(result.status, CONDITION_REPORT_STATUS_DRAFT)

    def test_tenant_isolation_never_leaks_cross_tenant_reports(self):
        # A report on a vehicle in another dealership must never
        # surface through this vehicle's property. Vehicles borrow
        # their own tenant, and the service function filters by it.
        other = Dealership.objects.create(name="Other", slug="other-33r")
        vehicle_other = _make_vehicle("M33R-OTH", other)
        _seed_report(
            vehicle_other,
            other,
            inspector_name="Cross-tenant",
            inspected_at=timezone.now(),
        )
        self.assertIsNone(self.vehicle.latest_condition_report)

    def test_deterministic_across_repeated_reads(self):
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Only",
            inspected_at=timezone.now(),
        )
        results = [self.vehicle.latest_condition_report.pk for _ in range(5)]
        self.assertEqual(len(set(results)), 1)


# ---- latest_completed_condition_report -----------------------------------


class LatestCompletedConditionReport(TestCase):
    """The ``latest_completed_condition_report`` property filters to
    ``status="complete"``. Drafts never surface, even if newer."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M33R-COMPL", self.default)

    def test_returns_none_when_no_completed_reports_exist(self):
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Only a draft",
            inspected_at=timezone.now(),
        )
        self.assertIsNone(
            self.vehicle.latest_completed_condition_report
        )

    def test_returns_none_when_vehicle_has_no_reports_at_all(self):
        self.assertIsNone(
            self.vehicle.latest_completed_condition_report
        )

    def test_ignores_drafts_returns_older_complete(self):
        older_complete = _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Older complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            complete=True,
        )
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Newer draft",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
        )
        result = self.vehicle.latest_completed_condition_report
        self.assertEqual(result.pk, older_complete.pk)

    def test_returns_newest_completed_when_multiple_exist(self):
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Older complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 3, 1, 9, 0)),
            complete=True,
        )
        newer_complete = _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Newer complete",
            inspected_at=timezone.make_aware(dt.datetime(2026, 6, 1, 9, 0)),
            complete=True,
        )
        result = self.vehicle.latest_completed_condition_report
        self.assertEqual(result.pk, newer_complete.pk)

    def test_tenant_isolation_never_leaks_cross_tenant_reports(self):
        other = Dealership.objects.create(name="Other", slug="other-33c")
        vehicle_other = _make_vehicle("M33C-OTH", other)
        _seed_report(
            vehicle_other,
            other,
            inspector_name="Cross-tenant complete",
            inspected_at=timezone.now(),
            complete=True,
        )
        self.assertIsNone(
            self.vehicle.latest_completed_condition_report
        )

    def test_deterministic_across_repeated_reads(self):
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Only complete",
            inspected_at=timezone.now(),
            complete=True,
        )
        results = [
            self.vehicle.latest_completed_condition_report.pk
            for _ in range(5)
        ]
        self.assertEqual(len(set(results)), 1)


# ---- Vehicle contract ----------------------------------------------------


class VehicleContract(TestCase):
    """The properties are thin delegators. No filtering, ordering,
    aggregation, mutation, or caching at the model layer."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M33R-CONTRACT", self.default)

    def test_latest_condition_report_delegates_to_service(self):
        """Patch the service function; verify the property calls it
        with the vehicle instance and the vehicle's own dealership."""
        sentinel = object()
        with patch(
            "dealer_ai.services.condition_report.latest_condition_report",
            return_value=sentinel,
        ) as mocked:
            result = self.vehicle.latest_condition_report
        self.assertIs(result, sentinel)
        mocked.assert_called_once_with(
            self.vehicle, dealership=self.vehicle.dealership
        )

    def test_latest_completed_condition_report_delegates_to_service(self):
        sentinel = object()
        with patch(
            "dealer_ai.services.condition_report."
            "latest_completed_condition_report",
            return_value=sentinel,
        ) as mocked:
            result = self.vehicle.latest_completed_condition_report
        self.assertIs(result, sentinel)
        mocked.assert_called_once_with(
            self.vehicle, dealership=self.vehicle.dealership
        )

    def test_property_read_does_not_mutate_vehicle(self):
        # Read both properties; refetch the vehicle; every field
        # should be byte-identical (proves no hidden side effects
        # like touching updated_at, opening a transaction, etc.).
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Some inspection",
            inspected_at=timezone.now(),
            complete=True,
        )
        before_updated_at = Vehicle.objects.get(pk=self.vehicle.pk).updated_at
        _ = self.vehicle.latest_condition_report
        _ = self.vehicle.latest_completed_condition_report
        after_updated_at = Vehicle.objects.get(pk=self.vehicle.pk).updated_at
        self.assertEqual(before_updated_at, after_updated_at)

    def test_latest_condition_report_costs_exactly_one_query_when_dealership_prefetched(self):
        # Locks the natural query profile before any caching decision.
        # Production callers should ``.select_related('dealership')``
        # so the tenant FK is in memory; under that shape this
        # property adds exactly one query (the ConditionReport
        # lookup). If a future edit adds a hidden query (e.g.
        # cross-tenant recheck against Dealership), this test flags
        # it immediately.
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Some inspection",
            inspected_at=timezone.now(),
        )
        vehicle = Vehicle.objects.select_related("dealership").get(
            pk=self.vehicle.pk
        )
        with self.assertNumQueries(1):
            _ = vehicle.latest_condition_report

    def test_latest_completed_condition_report_costs_exactly_one_query_when_dealership_prefetched(self):
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Some inspection",
            inspected_at=timezone.now(),
            complete=True,
        )
        vehicle = Vehicle.objects.select_related("dealership").get(
            pk=self.vehicle.pk
        )
        with self.assertNumQueries(1):
            _ = vehicle.latest_completed_condition_report

    def test_no_caching_repeated_reads_hit_db_every_time(self):
        # Locks the *absence* of caching. Two consecutive reads on
        # the same instance fire two queries. If a future edit
        # promotes the property to ``@cached_property``, this test
        # will fail — the failure is the flag to update this test
        # deliberately alongside the promotion.
        _seed_report(
            self.vehicle,
            self.default,
            inspector_name="Some inspection",
            inspected_at=timezone.now(),
        )
        vehicle = Vehicle.objects.select_related("dealership").get(
            pk=self.vehicle.pk
        )
        with self.assertNumQueries(2):
            _ = vehicle.latest_condition_report
            _ = vehicle.latest_condition_report

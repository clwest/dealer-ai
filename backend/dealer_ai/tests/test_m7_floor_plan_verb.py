"""Milestone 7 · Increment 2 (SESSION_089) — floor-plan service verb tests.

Locks the extracted :func:`services.floor_plan.accrue_daily_interest`
verb contract. The extraction preserved the M2 command body verbatim,
so this suite exercises the verb's own interface (dealership arg,
optional as_of, dry_run) rather than re-testing the M2 orchestration
invariants (already covered by
``test_accrue_floor_plan_interest_command.py`` and the M2.4a engine
suite).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_FLOOR_PLAN_INTEREST,
    SOURCE_AUCTION,
    Dealership,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.floor_plan import (
    AccrualPlan,
    AccrualSummary,
    accrue_daily_interest,
)
from dealer_ai.services.vehicle_ledger import record_acquisition


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _seed_acquisition(
    vehicle: Vehicle,
    dealership: Dealership,
    purchase_date: dt.date,
    price: Decimal = Decimal("18000.00"),
) -> None:
    record_acquisition(
        vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=price,
        purchase_date=purchase_date,
    )


class VerbReturnsAccrualSummary(TestCase):
    """The verb returns a fully-populated :class:`AccrualSummary`."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        vehicle = _make_vehicle("M7VERB-1", self.default)
        _seed_acquisition(vehicle, self.default, thirty_days_ago)

    def test_returns_accrual_summary_instance(self):
        summary = accrue_daily_interest(self.default)
        self.assertIsInstance(summary, AccrualSummary)

    def test_summary_carries_dealership_slug(self):
        summary = accrue_daily_interest(self.default)
        self.assertEqual(summary.dealership_slug, "default")

    def test_summary_reports_accrued_count(self):
        summary = accrue_daily_interest(self.default)
        self.assertEqual(summary.vehicles_accrued, 1)


class VerbDryRunPostsNothing(TestCase):
    """``dry_run=True`` skips the atomic block and posts zero rows."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        vehicle = _make_vehicle("M7VERB-DRY", self.default)
        _seed_acquisition(vehicle, self.default, thirty_days_ago)

    def test_dry_run_writes_zero_rows(self):
        summary = accrue_daily_interest(self.default, dry_run=True)
        self.assertTrue(summary.dry_run)
        self.assertEqual(
            VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            ).count(),
            0,
        )

    def test_dry_run_still_reports_planned_accruals(self):
        # Even though nothing is written, the summary must count what
        # WOULD be accrued — the operator uses dry-run output to decide.
        summary = accrue_daily_interest(self.default, dry_run=True)
        self.assertEqual(summary.vehicles_accrued, 1)
        self.assertGreater(summary.total_accrued, Decimal("0.00"))


class VerbLiveModePostsRows(TestCase):
    """``dry_run=False`` (default) writes one row per eligible vehicle."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        for stock in ("M7VERB-LIVE-1", "M7VERB-LIVE-2"):
            vehicle = _make_vehicle(stock, self.default)
            _seed_acquisition(vehicle, self.default, thirty_days_ago)

    def test_live_run_posts_one_row_per_eligible_vehicle(self):
        summary = accrue_daily_interest(self.default)
        self.assertFalse(summary.dry_run)
        self.assertEqual(summary.vehicles_accrued, 2)
        self.assertEqual(
            VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            ).count(),
            2,
        )


class VerbAsOfDefaultsToToday(TestCase):
    """When ``as_of`` is None, the verb defaults to today's date."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        vehicle = _make_vehicle("M7VERB-ASOF", self.default)
        _seed_acquisition(vehicle, self.default, thirty_days_ago)

    def test_as_of_none_uses_today(self):
        today = timezone.now().date()
        summary = accrue_daily_interest(self.default)
        self.assertEqual(summary.as_of, today)


class VerbAcceptsExplicitAsOf(TestCase):
    """The verb honors an explicit ``as_of`` date."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        sixty_days_ago = timezone.now().date() - dt.timedelta(days=60)
        vehicle = _make_vehicle("M7VERB-EXPLICIT", self.default)
        _seed_acquisition(vehicle, self.default, sixty_days_ago)

    def test_explicit_as_of_used(self):
        as_of = timezone.now().date() - dt.timedelta(days=10)
        summary = accrue_daily_interest(self.default, as_of=as_of)
        self.assertEqual(summary.as_of, as_of)


class VerbIdempotentSameDayRerun(TestCase):
    """Same-day re-run posts zero new rows (duplicate detection)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        vehicle = _make_vehicle("M7VERB-IDEM", self.default)
        _seed_acquisition(vehicle, self.default, thirty_days_ago)

    def test_second_call_posts_zero_new_rows(self):
        first = accrue_daily_interest(self.default)
        self.assertEqual(first.vehicles_accrued, 1)

        second = accrue_daily_interest(self.default)
        self.assertEqual(second.vehicles_accrued, 0)
        self.assertEqual(second.skipped_duplicate, 1)

        # Only one accrual row exists.
        self.assertEqual(
            VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            ).count(),
            1,
        )


class VerbCrossTenantIsolation(TestCase):
    """The verb only touches its target tenant's vehicles."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(name="Other", slug="other")

        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        v_default = _make_vehicle("M7VERB-DEF", self.default)
        _seed_acquisition(v_default, self.default, thirty_days_ago)
        v_other = _make_vehicle("M7VERB-OTHER", self.other)
        _seed_acquisition(v_other, self.other, thirty_days_ago)

    def test_only_target_tenant_accrued(self):
        summary = accrue_daily_interest(self.default)
        self.assertEqual(summary.vehicles_accrued, 1)
        # Default tenant has an accrual row; other tenant does not.
        default_rows = VehicleCost.objects.filter(
            dealership=self.default,
            category=CATEGORY_FLOOR_PLAN_INTEREST,
        ).count()
        other_rows = VehicleCost.objects.filter(
            dealership=self.other,
            category=CATEGORY_FLOOR_PLAN_INTEREST,
        ).count()
        self.assertEqual(default_rows, 1)
        self.assertEqual(other_rows, 0)


class VerbDataclassesReexported(TestCase):
    """The package __init__ re-exports the dataclasses so callers can
    import from ``services.floor_plan`` without knowing the accrual
    submodule."""

    def test_accrual_plan_reexported(self):
        from dealer_ai.services.floor_plan import AccrualPlan as Reexported
        from dealer_ai.services.floor_plan.accrual import AccrualPlan as Direct
        self.assertIs(Reexported, Direct)

    def test_accrual_summary_reexported(self):
        from dealer_ai.services.floor_plan import AccrualSummary as Reexported
        from dealer_ai.services.floor_plan.accrual import AccrualSummary as Direct
        self.assertIs(Reexported, Direct)

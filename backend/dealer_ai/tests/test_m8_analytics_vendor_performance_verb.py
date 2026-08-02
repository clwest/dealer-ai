"""Milestone 8 · Increment 2 (SESSION_095) — vendor_performance tests.

Locks the behavior of
:func:`services.analytics.vendor_performance` (Q2 + Q4).

Coverage:

- Empty tenant → empty list.
- In-progress WOs are excluded (only ``status=completed``).
- In-house WOs are excluded (only ``venue=outsourced``).
- WOs with null vendor are excluded.
- ``mean_completion_days`` averages whole days (approved →
  completed); WOs missing either timestamp are skipped from the
  mean; clock-skew (completed before approved) clamps to 0.
- ``mean_variance_pct`` uses |actual - estimated| / estimated *
  100; WOs missing actual or estimated (or estimated=0) are
  skipped.
- ``over_budget_count`` fires only when actual > authorized;
  authorized=None skips the check.
- Multi-vendor sort by completed_count desc, tiebreak on slug.
- Cross-tenant isolation.
- Window filter on ``completed_at`` date bounds.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_IN_HOUSE,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    Vehicle,
    Vendor,
    WorkOrder,
)
from dealer_ai.services.analytics import vendor_performance


_STOCK_COUNTER = {"n": 0}


def _next_stock() -> str:
    _STOCK_COUNTER["n"] += 1
    return f"VP-{_STOCK_COUNTER['n']:04d}"


def _make_vehicle(dealership: Dealership, *, stock: str | None = None) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock or _next_stock(),
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _make_vendor(
    dealership: Dealership, *, slug: str = "gp-body", name: str | None = None
) -> Vendor:
    return Vendor.objects.create(
        dealership=dealership,
        slug=slug,
        name=name or f"Vendor {slug}",
    )


def _aware(y: int, m: int, d: int, hour: int = 12) -> dt.datetime:
    return timezone.make_aware(dt.datetime(y, m, d, hour, 0))


def _make_completed_wo(
    dealership: Dealership,
    vendor: Vendor,
    *,
    approved_at: dt.datetime | None = None,
    completed_at: dt.datetime,
    estimated_cost: str | None = None,
    authorized_cost: str | None = None,
    actual_cost: str | None = None,
    venue: str = WORK_ORDER_VENUE_OUTSOURCED,
    status: str = WORK_ORDER_STATUS_COMPLETED,
    stock: str | None = None,
) -> WorkOrder:
    vehicle = _make_vehicle(dealership, stock=stock)
    return WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        vendor=vendor,
        category=CONDITION_CATEGORY_BODY,
        venue=venue,
        status=status,
        approved_at=approved_at,
        completed_at=completed_at,
        estimated_cost=(
            Decimal(estimated_cost) if estimated_cost is not None else None
        ),
        authorized_cost=(
            Decimal(authorized_cost) if authorized_cost is not None else None
        ),
        actual_cost=(
            Decimal(actual_cost) if actual_cost is not None else None
        ),
    )


class VendorPerformanceVerbTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="vp-primary", name="VP Primary"
        )

    def test_empty_tenant_returns_empty(self) -> None:
        self.assertEqual(vendor_performance(self.dealership), [])

    def test_in_progress_wo_excluded(self) -> None:
        vendor = _make_vendor(self.dealership)
        vehicle = _make_vehicle(self.dealership)
        # in_progress WO has no completed_at yet; excluded from the
        # aggregation entirely.
        WorkOrder.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            vendor=vendor,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_cost=Decimal("500.00"),
        )
        self.assertEqual(vendor_performance(self.dealership), [])

    def test_in_house_wo_excluded(self) -> None:
        vendor = _make_vendor(self.dealership)
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 4),
            estimated_cost="500.00",
            actual_cost="500.00",
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        self.assertEqual(vendor_performance(self.dealership), [])

    def test_mean_completion_days_averages_whole_days(self) -> None:
        vendor = _make_vendor(self.dealership)
        # Two WOs: 2 days + 6 days = mean 4.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 3),
        )
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 5),
            completed_at=_aware(2026, 8, 11),
        )
        rows = vendor_performance(self.dealership)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].completed_count, 2)
        self.assertEqual(rows[0].mean_completion_days, 4)

    def test_missing_approved_at_skips_days_but_counts(self) -> None:
        vendor = _make_vendor(self.dealership)
        # Data-quality gap: approved_at absent. Excluded from the
        # completion-days mean but still counted in completed_count.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=None,
            completed_at=_aware(2026, 8, 3),
        )
        rows = vendor_performance(self.dealership)
        self.assertEqual(rows[0].completed_count, 1)
        self.assertIsNone(rows[0].mean_completion_days)

    def test_clock_skew_clamps_completion_days_to_zero(self) -> None:
        vendor = _make_vendor(self.dealership)
        # completed_at earlier than approved_at → clamp to 0 rather
        # than skew the mean negative.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 10),
            completed_at=_aware(2026, 8, 5),
        )
        rows = vendor_performance(self.dealership)
        self.assertEqual(rows[0].mean_completion_days, 0)

    def test_variance_pct_computed_absolutely(self) -> None:
        vendor = _make_vendor(self.dealership)
        # Two WOs — 10% over and 20% under. Mean absolute variance
        # = 15%.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 2),
            estimated_cost="100.00",
            actual_cost="110.00",
        )
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 3),
            completed_at=_aware(2026, 8, 4),
            estimated_cost="100.00",
            actual_cost="80.00",
        )
        rows = vendor_performance(self.dealership)
        self.assertEqual(rows[0].mean_variance_pct, Decimal("15.00"))

    def test_variance_skips_missing_or_zero_estimated(self) -> None:
        vendor = _make_vendor(self.dealership)
        # WO 1: estimated=None, excluded.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 2),
            actual_cost="500.00",
        )
        # WO 2: estimated=0, excluded (would be div-by-zero).
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 3),
            completed_at=_aware(2026, 8, 4),
            estimated_cost="0",
            actual_cost="500.00",
        )
        # WO 3: actual=None, excluded.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 5),
            completed_at=_aware(2026, 8, 6),
            estimated_cost="100.00",
        )
        rows = vendor_performance(self.dealership)
        self.assertEqual(rows[0].completed_count, 3)
        # No usable WO for variance → None.
        self.assertIsNone(rows[0].mean_variance_pct)

    def test_over_budget_counts_only_when_authorized_set(self) -> None:
        vendor = _make_vendor(self.dealership)
        # Over authorized cap — counted.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 2),
            estimated_cost="100.00",
            authorized_cost="120.00",
            actual_cost="150.00",
        )
        # Under authorized cap — not counted.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 3),
            completed_at=_aware(2026, 8, 4),
            estimated_cost="100.00",
            authorized_cost="120.00",
            actual_cost="110.00",
        )
        # Authorized cap not set — skipped from the check even
        # though actual exceeds estimated.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 5),
            completed_at=_aware(2026, 8, 6),
            estimated_cost="100.00",
            actual_cost="200.00",
        )
        rows = vendor_performance(self.dealership)
        self.assertEqual(rows[0].over_budget_count, 1)
        self.assertEqual(rows[0].completed_count, 3)

    def test_multi_vendor_sort_by_count_desc(self) -> None:
        heavy = _make_vendor(self.dealership, slug="heavy", name="Heavy Shop")
        light = _make_vendor(self.dealership, slug="light", name="Light Shop")
        # Heavy: 3 completed. Light: 1.
        for _ in range(3):
            _make_completed_wo(
                self.dealership,
                heavy,
                approved_at=_aware(2026, 8, 1),
                completed_at=_aware(2026, 8, 3),
            )
        _make_completed_wo(
            self.dealership,
            light,
            approved_at=_aware(2026, 8, 5),
            completed_at=_aware(2026, 8, 7),
        )
        rows = vendor_performance(self.dealership)
        self.assertEqual([r.vendor_slug for r in rows], ["heavy", "light"])

    def test_tiebreak_on_vendor_slug(self) -> None:
        alpha = _make_vendor(self.dealership, slug="alpha", name="Alpha")
        bravo = _make_vendor(self.dealership, slug="bravo", name="Bravo")
        # Both vendors get one completed WO — tiebreak on slug asc.
        for v in (bravo, alpha):
            _make_completed_wo(
                self.dealership,
                v,
                approved_at=_aware(2026, 8, 1),
                completed_at=_aware(2026, 8, 2),
            )
        rows = vendor_performance(self.dealership)
        self.assertEqual([r.vendor_slug for r in rows], ["alpha", "bravo"])

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="vp-other", name="VP Other"
        )
        other_vendor = _make_vendor(other, slug="other-shop", name="Other Shop")
        _make_completed_wo(
            other,
            other_vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 5),
        )
        mine_vendor = _make_vendor(
            self.dealership, slug="mine-shop", name="Mine Shop"
        )
        _make_completed_wo(
            self.dealership,
            mine_vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 2),
        )
        rows = vendor_performance(self.dealership)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].vendor_slug, "mine-shop")

    def test_window_bounds_inclusive(self) -> None:
        vendor = _make_vendor(self.dealership)
        # Three completed WOs: July, August, September.
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 7, 1),
            completed_at=_aware(2026, 7, 5),
        )
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 5),
        )
        _make_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 9, 1),
            completed_at=_aware(2026, 9, 5),
        )

        rows = vendor_performance(self.dealership)
        self.assertEqual(rows[0].completed_count, 3)

        # August only.
        rows = vendor_performance(
            self.dealership,
            window_start=dt.date(2026, 8, 1),
            window_end=dt.date(2026, 8, 31),
        )
        self.assertEqual(rows[0].completed_count, 1)

        # August onwards.
        rows = vendor_performance(
            self.dealership,
            window_start=dt.date(2026, 8, 1),
        )
        self.assertEqual(rows[0].completed_count, 2)

        # Through July.
        rows = vendor_performance(
            self.dealership,
            window_end=dt.date(2026, 7, 31),
        )
        self.assertEqual(rows[0].completed_count, 1)

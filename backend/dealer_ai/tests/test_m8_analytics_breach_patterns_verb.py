"""Milestone 8 · Increment 3 (SESSION_096) — breach_patterns tests.

Locks the behavior of
:func:`services.analytics.breach_patterns` (Q10).

Coverage:

- Empty tenant → total=0, average=None, empty rollups.
- Cross-tenant isolation.
- Window filter (``detected_at`` older than window_days).
- Total + average across mixed kinds.
- Top-vendors sort by breach count desc, tiebreak on name asc.
- Top-N vendor cap at 5.
- Per-kind rollup returns every observed kind.
- ``average_breach_days`` quantized to two decimal places.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    SLA_BREACH_KIND_APPROVED_STALE,
    SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
    SlaBreachRecord,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    Vehicle,
    Vendor,
    WorkOrder,
)
from dealer_ai.services.analytics import breach_patterns


_STOCK_COUNTER = {"n": 0}


def _next_stock() -> str:
    _STOCK_COUNTER["n"] += 1
    return f"BP-{_STOCK_COUNTER['n']:04d}"


def _make_wo(dealership: Dealership) -> WorkOrder:
    vehicle = Vehicle.objects.create(
        stock_number=_next_stock(),
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    vendor = Vendor.objects.create(
        dealership=dealership,
        slug=f"vendor-{_STOCK_COUNTER['n']}",
        name=f"Vendor {_STOCK_COUNTER['n']}",
    )
    return WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        vendor=vendor,
        category=CONDITION_CATEGORY_BODY,
        venue=WORK_ORDER_VENUE_OUTSOURCED,
        status=WORK_ORDER_STATUS_APPROVED,
    )


def _make_breach(
    dealership: Dealership,
    *,
    kind: str,
    vendor_name: str,
    breach_days: int,
    detected_at: dt.datetime | None = None,
) -> SlaBreachRecord:
    when = detected_at or timezone.now()
    wo = _make_wo(dealership)
    return SlaBreachRecord.objects.create(
        dealership=dealership,
        work_order=wo,
        kind=kind,
        breach_days=breach_days,
        detected_at=when,
        detected_at_date=when.date(),
        vehicle_stock=wo.vehicle.stock_number,
        vendor_name=vendor_name,
    )


class BreachPatternsVerbTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bp-primary", name="BP Primary"
        )

    def test_empty_tenant_report(self) -> None:
        report = breach_patterns(self.dealership)
        self.assertEqual(report.total_breach_count, 0)
        self.assertIsNone(report.average_breach_days)
        self.assertEqual(report.top_vendors_by_breach_count, [])
        self.assertEqual(report.breaches_by_kind, [])

    def test_total_and_average_across_kinds(self) -> None:
        _make_breach(
            self.dealership,
            kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            vendor_name="Alpha",
            breach_days=3,
        )
        _make_breach(
            self.dealership,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            vendor_name="Alpha",
            breach_days=8,
        )
        _make_breach(
            self.dealership,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            vendor_name="Beta",
            breach_days=10,
        )
        report = breach_patterns(self.dealership)
        self.assertEqual(report.total_breach_count, 3)
        # (3 + 8 + 10) / 3 = 7.00
        self.assertEqual(report.average_breach_days, Decimal("7.00"))

    def test_top_vendors_sort_and_tiebreak(self) -> None:
        # Alpha: 3 breaches. Beta: 2. Charlie: 2 (tiebreak on name).
        for i in range(3):
            _make_breach(
                self.dealership,
                kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
                vendor_name="Alpha",
                breach_days=1 + i,
            )
        for i in range(2):
            _make_breach(
                self.dealership,
                kind=SLA_BREACH_KIND_APPROVED_STALE,
                vendor_name="Beta",
                breach_days=8,
            )
        for i in range(2):
            _make_breach(
                self.dealership,
                kind=SLA_BREACH_KIND_APPROVED_STALE,
                vendor_name="Charlie",
                breach_days=9,
            )
        report = breach_patterns(self.dealership)
        # Alpha first (highest count); Beta beats Charlie on name.
        self.assertEqual(
            [v.vendor_name for v in report.top_vendors_by_breach_count],
            ["Alpha", "Beta", "Charlie"],
        )
        self.assertEqual(
            [v.breach_count for v in report.top_vendors_by_breach_count],
            [3, 2, 2],
        )

    def test_top_vendors_capped_at_five(self) -> None:
        # Seed 7 vendors each with one breach; verb should return
        # top 5.
        for name in ("V1", "V2", "V3", "V4", "V5", "V6", "V7"):
            _make_breach(
                self.dealership,
                kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
                vendor_name=name,
                breach_days=1,
            )
        report = breach_patterns(self.dealership)
        self.assertEqual(len(report.top_vendors_by_breach_count), 5)

    def test_breaches_by_kind_rollup(self) -> None:
        for _ in range(4):
            _make_breach(
                self.dealership,
                kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
                vendor_name="Alpha",
                breach_days=2,
            )
        for _ in range(1):
            _make_breach(
                self.dealership,
                kind=SLA_BREACH_KIND_APPROVED_STALE,
                vendor_name="Alpha",
                breach_days=9,
            )
        report = breach_patterns(self.dealership)
        # Both kinds present; sorted by count desc.
        self.assertEqual(len(report.breaches_by_kind), 2)
        self.assertEqual(
            report.breaches_by_kind[0].kind,
            SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
        )
        self.assertEqual(report.breaches_by_kind[0].breach_count, 4)
        self.assertEqual(report.breaches_by_kind[0].kind_display, "In progress past ETA")
        self.assertEqual(report.breaches_by_kind[1].breach_count, 1)

    def test_window_bound_excludes_older_rows(self) -> None:
        now = timezone.now()
        _make_breach(
            self.dealership,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            vendor_name="Alpha",
            breach_days=10,
            detected_at=now - dt.timedelta(days=45),
        )
        _make_breach(
            self.dealership,
            kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            vendor_name="Alpha",
            breach_days=3,
            detected_at=now - dt.timedelta(days=5),
        )
        # Default 30d window — older breach excluded.
        report = breach_patterns(self.dealership)
        self.assertEqual(report.total_breach_count, 1)
        # 90d window — both included.
        report = breach_patterns(self.dealership, window_days=90)
        self.assertEqual(report.total_breach_count, 2)

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="bp-other", name="BP Other"
        )
        _make_breach(
            other,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            vendor_name="OtherVendor",
            breach_days=15,
        )
        _make_breach(
            self.dealership,
            kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            vendor_name="MyVendor",
            breach_days=2,
        )
        report = breach_patterns(self.dealership)
        self.assertEqual(report.total_breach_count, 1)
        self.assertEqual(
            report.top_vendors_by_breach_count[0].vendor_name, "MyVendor"
        )

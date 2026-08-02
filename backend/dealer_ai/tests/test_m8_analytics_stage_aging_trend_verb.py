"""Milestone 8 · Increment 3 (SESSION_096) — stage_aging_trend tests.

Locks the behavior of
:func:`services.analytics.stage_aging_trend` (Q5 + Q9).

Coverage:

- Empty tenant → empty list.
- Unknown stage → ``ValueError``.
- Cross-tenant isolation.
- Cross-stage isolation (only requested stage rolls up).
- Window filter (``window_days`` bound).
- Time-ordering ascending.
- Row shape (all four fields carried).
"""

from __future__ import annotations

import datetime as dt

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    StageAgingSnapshot,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_FRONTLINE,
)
from dealer_ai.services.analytics import (
    AgingTrendPoint,
    stage_aging_trend,
)


def _make_snapshot(
    dealership: Dealership,
    *,
    stage: str,
    snapshot_at: dt.datetime,
    vehicle_count: int = 5,
    p50: int = 3,
    p90: int = 14,
) -> StageAgingSnapshot:
    return StageAgingSnapshot.objects.create(
        dealership=dealership,
        stage=stage,
        snapshot_at=snapshot_at,
        vehicle_count=vehicle_count,
        p50_days=p50,
        p90_days=p90,
    )


class StageAgingTrendVerbTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="aging-primary", name="Aging Primary"
        )

    def test_empty_tenant_returns_empty(self) -> None:
        self.assertEqual(
            stage_aging_trend(self.dealership, VEHICLE_STAGE_RECON),
            [],
        )

    def test_unknown_stage_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            stage_aging_trend(self.dealership, "not-a-stage")

    def test_cross_stage_isolation(self) -> None:
        now = timezone.now()
        _make_snapshot(
            self.dealership, stage=VEHICLE_STAGE_RECON, snapshot_at=now
        )
        _make_snapshot(
            self.dealership,
            stage=VEHICLE_STAGE_FRONTLINE,
            snapshot_at=now,
        )
        # Requesting recon returns only the recon snapshot.
        recon_points = stage_aging_trend(
            self.dealership, VEHICLE_STAGE_RECON
        )
        self.assertEqual(len(recon_points), 1)

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="aging-other", name="Aging Other"
        )
        now = timezone.now()
        _make_snapshot(
            other, stage=VEHICLE_STAGE_RECON, snapshot_at=now
        )
        _make_snapshot(
            self.dealership, stage=VEHICLE_STAGE_RECON, snapshot_at=now
        )
        points = stage_aging_trend(self.dealership, VEHICLE_STAGE_RECON)
        self.assertEqual(len(points), 1)

    def test_ordered_by_snapshot_at_ascending(self) -> None:
        # Insert three snapshots out of order; verb should emit
        # ascending.
        now = timezone.now()
        _make_snapshot(
            self.dealership,
            stage=VEHICLE_STAGE_RECON,
            snapshot_at=now - dt.timedelta(days=1),
            p50=1,
        )
        _make_snapshot(
            self.dealership,
            stage=VEHICLE_STAGE_RECON,
            snapshot_at=now - dt.timedelta(days=3),
            p50=3,
        )
        _make_snapshot(
            self.dealership,
            stage=VEHICLE_STAGE_RECON,
            snapshot_at=now - dt.timedelta(days=2),
            p50=2,
        )
        points = stage_aging_trend(self.dealership, VEHICLE_STAGE_RECON)
        # Ordered by snapshot_at asc → p50 values should be 3, 2, 1
        # (oldest to newest snapshot_at, corresponding p50 values).
        self.assertEqual([p.p50_days for p in points], [3, 2, 1])

    def test_window_bound_filters_older_snapshots(self) -> None:
        now = timezone.now()
        _make_snapshot(
            self.dealership,
            stage=VEHICLE_STAGE_RECON,
            snapshot_at=now - dt.timedelta(days=45),
        )
        _make_snapshot(
            self.dealership,
            stage=VEHICLE_STAGE_RECON,
            snapshot_at=now - dt.timedelta(days=5),
        )
        # Default 30-day window → older snapshot excluded.
        points = stage_aging_trend(self.dealership, VEHICLE_STAGE_RECON)
        self.assertEqual(len(points), 1)
        # 90-day window → both included.
        points = stage_aging_trend(
            self.dealership, VEHICLE_STAGE_RECON, window_days=90
        )
        self.assertEqual(len(points), 2)

    def test_row_shape_carries_all_fields(self) -> None:
        now = timezone.now()
        _make_snapshot(
            self.dealership,
            stage=VEHICLE_STAGE_RECON,
            snapshot_at=now,
            vehicle_count=7,
            p50=4,
            p90=18,
        )
        points = stage_aging_trend(self.dealership, VEHICLE_STAGE_RECON)
        self.assertEqual(len(points), 1)
        point = points[0]
        self.assertIsInstance(point, AgingTrendPoint)
        self.assertEqual(point.vehicle_count, 7)
        self.assertEqual(point.p50_days, 4)
        self.assertEqual(point.p90_days, 18)

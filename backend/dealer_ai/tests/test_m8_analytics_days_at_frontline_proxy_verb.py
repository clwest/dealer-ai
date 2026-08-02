"""Milestone 8 · Increment 4 (SESSION_097) — days_at_frontline_proxy tests.

Locks the behavior of
:func:`services.analytics.days_at_frontline_proxy` (Q8 proxy).

Coverage:

- Empty tenant / empty window → snapshot_count=0, every derived
  field None.
- Only ``stage='frontline'`` snapshots counted (cross-stage
  isolation).
- Mean p50 / p90 across window snapshots.
- ``latest_vehicle_count`` + ``latest_snapshot_at`` from the most
  recent snapshot in the window.
- Window filter excludes older snapshots.
- Cross-tenant isolation.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    StageAgingSnapshot,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_RECON,
)
from dealer_ai.services.analytics import days_at_frontline_proxy


def _snap(
    dealership: Dealership,
    *,
    stage: str = VEHICLE_STAGE_FRONTLINE,
    snapshot_at: dt.datetime | None = None,
    vehicle_count: int = 10,
    p50: int = 4,
    p90: int = 15,
) -> StageAgingSnapshot:
    return StageAgingSnapshot.objects.create(
        dealership=dealership,
        stage=stage,
        snapshot_at=snapshot_at or timezone.now(),
        vehicle_count=vehicle_count,
        p50_days=p50,
        p90_days=p90,
    )


class DaysAtFrontlineProxyVerbTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="dfp-primary", name="DFP Primary"
        )

    def test_empty_window_produces_null_fields(self) -> None:
        report = days_at_frontline_proxy(self.dealership)
        self.assertEqual(report.snapshot_count, 0)
        self.assertIsNone(report.mean_p50_days)
        self.assertIsNone(report.mean_p90_days)
        self.assertIsNone(report.latest_vehicle_count)
        self.assertIsNone(report.latest_snapshot_at)

    def test_only_frontline_snapshots_counted(self) -> None:
        now = timezone.now()
        _snap(
            self.dealership,
            stage=VEHICLE_STAGE_FRONTLINE,
            snapshot_at=now,
            vehicle_count=5,
            p50=3,
            p90=10,
        )
        # Recon-stage snapshot must NOT contribute to the frontline
        # proxy — cross-stage isolation.
        _snap(
            self.dealership,
            stage=VEHICLE_STAGE_RECON,
            snapshot_at=now,
            vehicle_count=99,
            p50=99,
            p90=99,
        )
        report = days_at_frontline_proxy(self.dealership)
        self.assertEqual(report.snapshot_count, 1)
        self.assertEqual(report.mean_p50_days, Decimal("3.00"))
        self.assertEqual(report.latest_vehicle_count, 5)

    def test_mean_across_window(self) -> None:
        now = timezone.now()
        # Three frontline snapshots with p50 = 2, 4, 6 → mean 4.00.
        # p90 = 10, 15, 20 → mean 15.00.
        _snap(
            self.dealership,
            snapshot_at=now - dt.timedelta(days=2),
            p50=2,
            p90=10,
        )
        _snap(
            self.dealership,
            snapshot_at=now - dt.timedelta(days=1),
            p50=4,
            p90=15,
        )
        _snap(self.dealership, snapshot_at=now, p50=6, p90=20)
        report = days_at_frontline_proxy(self.dealership)
        self.assertEqual(report.snapshot_count, 3)
        self.assertEqual(report.mean_p50_days, Decimal("4.00"))
        self.assertEqual(report.mean_p90_days, Decimal("15.00"))

    def test_latest_fields_from_most_recent_snapshot(self) -> None:
        now = timezone.now()
        _snap(
            self.dealership,
            snapshot_at=now - dt.timedelta(days=2),
            vehicle_count=8,
        )
        _snap(self.dealership, snapshot_at=now, vehicle_count=42)
        report = days_at_frontline_proxy(self.dealership)
        self.assertEqual(report.latest_vehicle_count, 42)
        self.assertIsNotNone(report.latest_snapshot_at)

    def test_window_excludes_older_snapshots(self) -> None:
        now = timezone.now()
        # 45 days old — outside default 30d.
        _snap(
            self.dealership,
            snapshot_at=now - dt.timedelta(days=45),
            p50=99,
            p90=99,
        )
        # 5 days old — inside default 30d.
        _snap(
            self.dealership,
            snapshot_at=now - dt.timedelta(days=5),
            p50=3,
            p90=10,
        )
        report = days_at_frontline_proxy(self.dealership)
        self.assertEqual(report.snapshot_count, 1)
        # 90d window — both included.
        report = days_at_frontline_proxy(self.dealership, window_days=90)
        self.assertEqual(report.snapshot_count, 2)

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="dfp-other", name="DFP Other"
        )
        now = timezone.now()
        _snap(other, snapshot_at=now, vehicle_count=999, p50=99, p90=999)
        _snap(self.dealership, snapshot_at=now, vehicle_count=5, p50=3)
        report = days_at_frontline_proxy(self.dealership)
        self.assertEqual(report.snapshot_count, 1)
        self.assertEqual(report.latest_vehicle_count, 5)

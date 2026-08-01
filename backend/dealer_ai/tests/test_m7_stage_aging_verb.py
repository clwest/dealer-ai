"""Milestone 7 · Increment 3 (SESSION_090) — aging-snapshot verb tests.

Locks the behavior of
:func:`services.lifecycle_aging.snapshot_stage_ages`:

- Empty tenant writes zero rows and returns an empty result.
- One row per stage-with-vehicles.
- p50 / p90 math matches the nearest-rank definition (module
  docstring in ``snapshots.py``).
- Days-in-stage clamps to 0 for future-dated / clock-skewed
  ``entered_at`` values.
- ``snapshot_at`` defaults to ``timezone.now()`` when omitted.
- Explicit ``snapshot_at`` is stamped on every written row.
- Cross-tenant isolation — snapshot for tenant A does not consider
  or write for tenant B.
- Bulk write is atomic (rolls back on mid-flight exception).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_RECON,
    Dealership,
    StageAgingSnapshot,
    Vehicle,
    VehicleStage,
)
from dealer_ai.services.lifecycle_aging import (
    SnapshotResult,
    StagePercentiles,
    snapshot_stage_ages,
)
from dealer_ai.services.lifecycle_aging.snapshots import (
    _compute_stage_percentiles,
    _nearest_rank_percentile,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    """Create a Vehicle. The test-only signal in
    ``dealer_ai/tests/__init__.py`` auto-seeds a frontline VehicleStage
    row with ``entered_at=now()``. Callers that need a different stage
    or entered_at must mutate the row via :func:`_place_in_stage_at`.
    """
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _place_in_stage_at(
    vehicle: Vehicle, stage: str, entered_at: dt.datetime
) -> VehicleStage:
    """Overwrite the vehicle's stage + entered_at in place.

    The auto-bootstrap signal already created a VehicleStage row for
    every ``Vehicle.objects.create`` call; this helper mutates that row
    rather than creating a duplicate (VehicleStage is OneToOne).
    """
    stage_row = VehicleStage.objects.get(vehicle=vehicle)
    stage_row.current_stage = stage
    stage_row.entered_at = entered_at
    stage_row.save(update_fields=("current_stage", "entered_at"))
    return stage_row


class VerbEmptyTenantWritesNothing(TestCase):
    """A tenant with no VehicleStage rows returns an empty result."""

    def test_empty_tenant_returns_empty_result(self):
        # A fresh tenant with no vehicles → no VehicleStage rows.
        empty = Dealership.objects.create(name="Empty", slug="empty-t")
        result = snapshot_stage_ages(empty)
        self.assertIsInstance(result, SnapshotResult)
        self.assertEqual(result.written_count, 0)
        self.assertEqual(result.stages_with_vehicles, [])

    def test_empty_tenant_writes_zero_rows(self):
        empty = Dealership.objects.create(name="Empty2", slug="empty-t2")
        snapshot_stage_ages(empty)
        self.assertEqual(
            StageAgingSnapshot.objects.filter(dealership=empty).count(), 0
        )


class VerbWritesOneRowPerStageWithVehicles(TestCase):
    """One row per stage that has at least one vehicle at snapshot time."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        now = timezone.now()
        # Two vehicles in frontline, one in recon.
        v1 = _make_vehicle("M73-A", self.default)
        _place_in_stage_at(
            v1, VEHICLE_STAGE_FRONTLINE, now - dt.timedelta(days=5)
        )
        v2 = _make_vehicle("M73-B", self.default)
        _place_in_stage_at(
            v2, VEHICLE_STAGE_FRONTLINE, now - dt.timedelta(days=10)
        )
        v3 = _make_vehicle("M73-C", self.default)
        _place_in_stage_at(
            v3, VEHICLE_STAGE_RECON, now - dt.timedelta(days=3)
        )

    def test_written_count_matches_stages_with_vehicles(self):
        result = snapshot_stage_ages(self.default)
        # Two stages populated → two rows.
        self.assertEqual(result.written_count, 2)
        self.assertEqual(
            sorted(result.stages_with_vehicles),
            [VEHICLE_STAGE_FRONTLINE, VEHICLE_STAGE_RECON],
        )

    def test_rows_persisted_with_correct_stage(self):
        snapshot_stage_ages(self.default)
        stages = set(
            StageAgingSnapshot.objects.filter(
                dealership=self.default
            ).values_list("stage", flat=True)
        )
        self.assertEqual(
            stages, {VEHICLE_STAGE_FRONTLINE, VEHICLE_STAGE_RECON}
        )

    def test_vehicle_count_per_row_matches_stage_population(self):
        snapshot_stage_ages(self.default)
        frontline = StageAgingSnapshot.objects.get(
            dealership=self.default, stage=VEHICLE_STAGE_FRONTLINE
        )
        recon = StageAgingSnapshot.objects.get(
            dealership=self.default, stage=VEHICLE_STAGE_RECON
        )
        self.assertEqual(frontline.vehicle_count, 2)
        self.assertEqual(recon.vehicle_count, 1)


class VerbP50P90Math(TestCase):
    """The percentile math matches nearest-rank on synthetic
    distributions."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.snapshot_at = timezone.now()

    def _seed_frontline_ages(self, ages_in_days: list[int]) -> None:
        for idx, days in enumerate(ages_in_days):
            v = _make_vehicle(f"M73-P-{idx}", self.default)
            _place_in_stage_at(
                v,
                VEHICLE_STAGE_FRONTLINE,
                self.snapshot_at - dt.timedelta(days=days),
            )

    def test_single_vehicle_p50_equals_p90_equals_its_age(self):
        self._seed_frontline_ages([7])
        snapshot_stage_ages(self.default, snapshot_at=self.snapshot_at)
        row = StageAgingSnapshot.objects.get(
            dealership=self.default, stage=VEHICLE_STAGE_FRONTLINE
        )
        self.assertEqual(row.vehicle_count, 1)
        self.assertEqual(row.p50_days, 7)
        self.assertEqual(row.p90_days, 7)

    def test_ten_vehicles_ascending_percentiles(self):
        # Distribution 1..10 days → nearest-rank p50 = index
        # ceil(0.5*10)-1 = 4 → value 5; p90 = index ceil(0.9*10)-1 = 8
        # → value 9.
        self._seed_frontline_ages([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        snapshot_stage_ages(self.default, snapshot_at=self.snapshot_at)
        row = StageAgingSnapshot.objects.get(
            dealership=self.default, stage=VEHICLE_STAGE_FRONTLINE
        )
        self.assertEqual(row.vehicle_count, 10)
        self.assertEqual(row.p50_days, 5)
        self.assertEqual(row.p90_days, 9)

    def test_two_vehicles_nearest_rank(self):
        # Distribution [3, 30] → p50 = index ceil(0.5*2)-1 = 0 → 3;
        # p90 = index ceil(0.9*2)-1 = 1 → 30.
        self._seed_frontline_ages([3, 30])
        snapshot_stage_ages(self.default, snapshot_at=self.snapshot_at)
        row = StageAgingSnapshot.objects.get(
            dealership=self.default, stage=VEHICLE_STAGE_FRONTLINE
        )
        self.assertEqual(row.p50_days, 3)
        self.assertEqual(row.p90_days, 30)


class NearestRankHelperContract(TestCase):
    """Direct coverage of the internal ``_nearest_rank_percentile``."""

    def test_p50_of_five_element_list(self):
        # ceil(0.5*5)-1 = 2 → third element.
        self.assertEqual(
            _nearest_rank_percentile([1, 2, 3, 4, 5], 0.50), 3
        )

    def test_p90_of_ten_element_list(self):
        self.assertEqual(
            _nearest_rank_percentile([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 0.90),
            8,
        )

    def test_singleton_returns_sole_value_at_any_percentile(self):
        self.assertEqual(_nearest_rank_percentile([42], 0.50), 42)
        self.assertEqual(_nearest_rank_percentile([42], 0.90), 42)

    def test_empty_raises_index_error(self):
        with self.assertRaises(IndexError):
            _nearest_rank_percentile([], 0.50)


class VerbDaysInStageClampsNonNegative(TestCase):
    """A future-dated / clock-skewed ``entered_at`` clamps to 0 days
    rather than producing a negative :attr:`PositiveIntegerField`
    write."""

    def test_future_entered_at_clamps_to_zero(self):
        default = Dealership.objects.get(slug="default")
        now = timezone.now()
        v = _make_vehicle("M73-FUTURE", default)
        # entered_at is IN THE FUTURE relative to snapshot_at — should
        # clamp to 0 days rather than raise a validation error on
        # PositiveIntegerField.
        _place_in_stage_at(
            v, VEHICLE_STAGE_FRONTLINE, now + dt.timedelta(days=7)
        )
        snapshot_stage_ages(default, snapshot_at=now)
        row = StageAgingSnapshot.objects.get(
            dealership=default, stage=VEHICLE_STAGE_FRONTLINE
        )
        self.assertEqual(row.p50_days, 0)
        self.assertEqual(row.p90_days, 0)


class VerbSnapshotAtDefaultsToNow(TestCase):
    """``snapshot_at=None`` uses ``timezone.now()``."""

    def test_defaults_to_now(self):
        default = Dealership.objects.get(slug="default")
        v = _make_vehicle("M73-DEFAULT-TS", default)
        _place_in_stage_at(
            v,
            VEHICLE_STAGE_FRONTLINE,
            timezone.now() - dt.timedelta(days=2),
        )
        before = timezone.now()
        result = snapshot_stage_ages(default)
        after = timezone.now()
        self.assertGreaterEqual(result.snapshot_at, before)
        self.assertLessEqual(result.snapshot_at, after)

    def test_explicit_snapshot_at_stamped_on_row(self):
        default = Dealership.objects.get(slug="default")
        v = _make_vehicle("M73-EXPLICIT-TS", default)
        _place_in_stage_at(
            v,
            VEHICLE_STAGE_FRONTLINE,
            timezone.now() - dt.timedelta(days=2),
        )
        explicit = timezone.now() - dt.timedelta(hours=1)
        result = snapshot_stage_ages(default, snapshot_at=explicit)
        self.assertEqual(result.snapshot_at, explicit)
        row = StageAgingSnapshot.objects.get(
            dealership=default, stage=VEHICLE_STAGE_FRONTLINE
        )
        self.assertEqual(row.snapshot_at, explicit)


class VerbCrossTenantIsolation(TestCase):
    """A snapshot for tenant A does not consider or write for tenant B."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(name="Other", slug="other-t")

        now = timezone.now()
        v_default = _make_vehicle("M73-DEF", self.default)
        _place_in_stage_at(
            v_default, VEHICLE_STAGE_FRONTLINE, now - dt.timedelta(days=5)
        )
        v_other = _make_vehicle("M73-OTHER", self.other)
        _place_in_stage_at(
            v_other, VEHICLE_STAGE_FRONTLINE, now - dt.timedelta(days=99)
        )

    def test_only_target_tenant_snapshotted(self):
        snapshot_stage_ages(self.default)
        default_rows = StageAgingSnapshot.objects.filter(
            dealership=self.default
        ).count()
        other_rows = StageAgingSnapshot.objects.filter(
            dealership=self.other
        ).count()
        self.assertEqual(default_rows, 1)
        self.assertEqual(other_rows, 0)

    def test_percentile_only_reflects_target_tenant_ages(self):
        # If the other tenant's 99-day vehicle leaked into the
        # computation, the default tenant's p50 would jump. It
        # shouldn't.
        snapshot_stage_ages(self.default)
        row = StageAgingSnapshot.objects.get(
            dealership=self.default, stage=VEHICLE_STAGE_FRONTLINE
        )
        # Only one default-tenant vehicle at 5 days → p50 = p90 = 5.
        self.assertEqual(row.p50_days, 5)
        self.assertEqual(row.p90_days, 5)


class VerbBulkWriteIsAtomic(TestCase):
    """If the bulk_create raises mid-flight, no partial rows persist."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        now = timezone.now()
        v1 = _make_vehicle("M73-ATOMIC-1", self.default)
        _place_in_stage_at(
            v1, VEHICLE_STAGE_FRONTLINE, now - dt.timedelta(days=1)
        )
        v2 = _make_vehicle("M73-ATOMIC-2", self.default)
        _place_in_stage_at(
            v2, VEHICLE_STAGE_RECON, now - dt.timedelta(days=2)
        )

    def test_bulk_create_failure_rolls_back_all_rows(self):
        target = (
            "dealer_ai.services.lifecycle_aging.snapshots"
            ".StageAgingSnapshot.objects.bulk_create"
        )
        with patch(target, side_effect=RuntimeError("simulated failure")):
            with self.assertRaises(RuntimeError):
                snapshot_stage_ages(self.default)
        # ZERO rows persisted.
        self.assertEqual(
            StageAgingSnapshot.objects.filter(
                dealership=self.default
            ).count(),
            0,
        )


class ComputeStagePercentilesHelperContract(TestCase):
    """Direct coverage of ``_compute_stage_percentiles`` for edge cases
    not naturally exercised by the verb-level tests."""

    def test_empty_input_returns_empty_list(self):
        snapshot_at = timezone.now()
        self.assertEqual(
            _compute_stage_percentiles([], snapshot_at), []
        )

    def test_multiple_stages_sorted_by_name(self):
        snapshot_at = timezone.now()
        rows = [
            {
                "current_stage": VEHICLE_STAGE_RECON,
                "entered_at": snapshot_at - dt.timedelta(days=1),
            },
            {
                "current_stage": VEHICLE_STAGE_FRONTLINE,
                "entered_at": snapshot_at - dt.timedelta(days=2),
            },
        ]
        result = _compute_stage_percentiles(rows, snapshot_at)
        # Sorted alphabetically → frontline before recon.
        self.assertEqual(
            [p.stage for p in result],
            sorted([VEHICLE_STAGE_FRONTLINE, VEHICLE_STAGE_RECON]),
        )
        # Types are StagePercentiles.
        for p in result:
            self.assertIsInstance(p, StagePercentiles)


class VerbDataclassesReexported(TestCase):
    """Package facade exposes the dataclasses."""

    def test_snapshot_result_reexported(self):
        from dealer_ai.services.lifecycle_aging import SnapshotResult as R
        from dealer_ai.services.lifecycle_aging.snapshots import (
            SnapshotResult as D,
        )
        self.assertIs(R, D)

    def test_stage_percentiles_reexported(self):
        from dealer_ai.services.lifecycle_aging import StagePercentiles as R
        from dealer_ai.services.lifecycle_aging.snapshots import (
            StagePercentiles as D,
        )
        self.assertIs(R, D)

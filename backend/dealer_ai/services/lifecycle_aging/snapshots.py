"""Milestone 7 · Increment 3 (SESSION_090) — aging-per-stage snapshot verb.

The tenant-scoped service verb that reads current
:class:`VehicleStage` rows for one dealership, groups by
:attr:`VehicleStage.current_stage`, computes days-in-stage percentiles
per stage, and writes one :class:`StageAgingSnapshot` row per
stage-with-vehicles.

**What this module owns:**

- The math: whole-day days-in-stage per vehicle; p50 / p90 across a
  per-stage distribution.
- The write pattern: one atomic bulk-create per snapshot invocation
  so a partial batch is never persisted.

**What this module does NOT own:**

- Celery task decoration + tenant fan-out — that lives in
  :mod:`.tasks` (per-tenant task + all-tenants orchestrator).
- Broker / Beat schedule wiring — ``dealer_kit/settings.py``.
- M8 aggregation over historical snapshots — that's Milestone 8.

**Percentile semantics.** Uses the "nearest-rank" percentile method
(same as :func:`statistics.quantiles` with ``method="exclusive"``
would produce for the boundary points, but implemented directly to
keep the math obvious and rounding-consistent regardless of Python
version). For a distribution ``[d0, d1, ..., dN-1]`` sorted ascending:

- ``p50`` = value at index ``max(0, ceil(0.50 * N) - 1)`` — the median
  under nearest-rank.
- ``p90`` = value at index ``max(0, ceil(0.90 * N) - 1)`` — the 90th
  percentile under nearest-rank.

For ``N=1`` both p50 and p90 collapse to the sole value. For ``N=2``
p50 = the smaller value (index 0) and p90 = the larger (index 1). No
interpolation — the M8 dashboard's "long-tail" signal is preserved
regardless of exact sample count.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.3 +
§5.c (Option A) + §7 M7.3.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from typing import Optional

from django.db import transaction

from ...models import (
    Dealership,
    StageAgingSnapshot,
    VehicleStage,
)


@dataclass(frozen=True)
class StagePercentiles:
    """The per-stage percentile intermediate produced by
    :func:`_compute_stage_percentiles`. One instance per stage that has
    at least one vehicle in it at snapshot time.

    Frozen so downstream code cannot mutate the computation output —
    the persisted :class:`StageAgingSnapshot` rows should agree with
    the intermediate exactly.
    """

    stage: str
    vehicle_count: int
    p50_days: int
    p90_days: int


@dataclass
class SnapshotResult:
    """Verb execution summary. Consumed by the Celery task shell as a
    structured audit-log payload and by tests as an assertion surface.
    """

    dealership_slug: str
    snapshot_at: dt.datetime
    written: list[StageAgingSnapshot] = field(default_factory=list)
    # Stages that had at least one vehicle at snapshot time — the
    # written rows all correspond to entries in this list. Kept
    # separately so callers can distinguish "empty tenant" (list is
    # empty and no rows were written) from "verb was called with
    # per-stage writes disabled" (hypothetical future flag; not shipped
    # at M7.3).
    stages_with_vehicles: list[str] = field(default_factory=list)

    @property
    def written_count(self) -> int:
        return len(self.written)


# ---------------------------------------------------------------------------
# Public verb
# ---------------------------------------------------------------------------


def snapshot_stage_ages(
    dealership: Dealership,
    *,
    snapshot_at: Optional[dt.datetime] = None,
) -> SnapshotResult:
    """Compute per-stage aging percentiles for one tenant and persist
    the results.

    Parameters
    ----------
    dealership : Dealership
        The tenant whose current :class:`VehicleStage` rows are
        aggregated. Required — the verb is deliberately single-tenant;
        the M7.3 Celery orchestrator handles multi-tenant fan-out.
    snapshot_at : datetime, optional
        The wall-clock time to record on every written row and to
        subtract from each :attr:`VehicleStage.entered_at` when
        computing days-in-stage. Defaults to
        :func:`django.utils.timezone.now`. Explicit values are useful
        for tests and for backfill scenarios (e.g. "generate the
        snapshot that would have run yesterday at 03:00").

    Returns
    -------
    SnapshotResult
        Contains the list of persisted :class:`StageAgingSnapshot`
        rows and the list of stages that had at least one vehicle at
        snapshot time. An empty-tenant run returns an empty result
        with ``written_count == 0`` and does NOT write any rows.

    Notes
    -----
    Transaction strategy: whole-run atomicity. The ``bulk_create``
    happens inside a ``transaction.atomic()`` block. Any exception
    raised inside the loop that builds :class:`StagePercentiles`
    rolls back nothing yet (no writes happen until the bulk_create);
    an exception inside the bulk_create rolls back all rows in the
    batch. Rationale: partial state is worse than none for a
    dashboard-feeding job that the operator will re-run.
    """
    if snapshot_at is None:
        # Deferred import so this module's import graph stays free of
        # ``django.utils.timezone`` — the timezone lookup is only
        # needed when the caller doesn't supply an explicit datetime.
        from django.utils import timezone

        snapshot_at = timezone.now()

    result = SnapshotResult(
        dealership_slug=dealership.slug,
        snapshot_at=snapshot_at,
    )

    # Read every current VehicleStage row for the tenant. ``entered_at``
    # is the only field we need for the age computation; ``.values()``
    # skips the ORM-instance materialization overhead and yields
    # dictionaries that ``_compute_stage_percentiles`` can consume
    # directly.
    stage_rows = list(
        VehicleStage.objects.filter(dealership=dealership).values(
            "current_stage", "entered_at"
        )
    )

    percentiles = _compute_stage_percentiles(stage_rows, snapshot_at)
    result.stages_with_vehicles = [p.stage for p in percentiles]

    if not percentiles:
        # Empty tenant (or a tenant with no VehicleStage rows). No
        # rows to write; return an empty result.
        return result

    to_write = [
        StageAgingSnapshot(
            dealership=dealership,
            stage=p.stage,
            snapshot_at=snapshot_at,
            vehicle_count=p.vehicle_count,
            p50_days=p.p50_days,
            p90_days=p.p90_days,
        )
        for p in percentiles
    ]

    with transaction.atomic():
        StageAgingSnapshot.objects.bulk_create(to_write)

    # ``bulk_create`` on SQLite/PostgreSQL populates ``pk`` on the
    # instances so downstream consumers can reference them directly.
    result.written = to_write
    return result


# ---------------------------------------------------------------------------
# Internal computation
# ---------------------------------------------------------------------------


def _compute_stage_percentiles(
    stage_rows: list[dict],
    snapshot_at: dt.datetime,
) -> list[StagePercentiles]:
    """Group ``stage_rows`` by ``current_stage`` and compute p50 / p90
    of ``(snapshot_at - entered_at).days`` per stage.

    Returns a list of :class:`StagePercentiles` — one entry per stage
    that has at least one row. Empty input → empty output.

    Sorted by stage name for deterministic ordering; the M8 dashboards
    do not require a specific order but tests + operator inspection
    both benefit from predictability.
    """
    per_stage: dict[str, list[int]] = {}
    for row in stage_rows:
        stage = row["current_stage"]
        entered_at = row["entered_at"]
        # Whole days between entered_at and snapshot_at. A vehicle that
        # entered its current stage today reads 0 days — the correct
        # semantics for a "days in stage" metric.
        delta = snapshot_at - entered_at
        # Guard against clock skew or a mis-seeded future entered_at
        # producing a negative delta — clamp to 0 to keep the
        # PositiveIntegerField write valid.
        days = max(0, delta.days)
        per_stage.setdefault(stage, []).append(days)

    percentiles: list[StagePercentiles] = []
    for stage in sorted(per_stage.keys()):
        distribution = sorted(per_stage[stage])
        percentiles.append(
            StagePercentiles(
                stage=stage,
                vehicle_count=len(distribution),
                p50_days=_nearest_rank_percentile(distribution, 0.50),
                p90_days=_nearest_rank_percentile(distribution, 0.90),
            )
        )
    return percentiles


def _nearest_rank_percentile(sorted_values: list[int], percentile: float) -> int:
    """Nearest-rank percentile — see module docstring for the exact
    semantics.

    Parameters
    ----------
    sorted_values : list[int]
        Ascending-sorted numeric values.
    percentile : float
        In ``(0.0, 1.0]``. E.g. ``0.50`` for median, ``0.90`` for the
        90th percentile.

    Returns
    -------
    int
        The value at the nearest-rank index. For ``sorted_values=[]``
        raises :class:`IndexError` — callers must guard against empty
        input at the group-by layer.
    """
    if not sorted_values:
        raise IndexError(
            "nearest-rank percentile is undefined on an empty distribution"
        )
    # ``math.ceil(percentile * N) - 1`` is the nearest-rank index. For
    # p=0.5 and N=2 this yields index 0 (the smaller value) — the
    # "median" under nearest-rank collapses to the lower half. For
    # p=0.9 and N=1 this yields index 0 (the sole value). The
    # ``max(0, ...)`` guards against p * N rounding to 0 for very
    # small p (not reachable at M7.3 with p >= 0.5, but future-proof).
    index = max(0, math.ceil(percentile * len(sorted_values)) - 1)
    return sorted_values[index]

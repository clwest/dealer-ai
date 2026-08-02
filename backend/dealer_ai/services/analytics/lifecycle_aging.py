"""Milestone 8 · Increment 3 (SESSION_096) + Increment 4 (SESSION_097) — lifecycle-aging analytics.

Aggregations rooted in M7.3 :class:`StageAgingSnapshot`:

- :func:`stage_aging_trend` (Q5 + Q9, M8.3) — per-stage time-series
  of p50 / p90 / vehicle_count.
- :func:`days_at_frontline_proxy` (Q8 proxy, M8.4) — window-mean
  p50 / p90 + latest vehicle_count on the ``frontline`` stage. The
  proxy for §1.7's true inventory-turn question pending M9 Sale
  substrate. See ``MILESTONE_8_PLANNING.md`` §1.7 for the proxy
  rationale.

The M7.3 nightly Beat job writes snapshots; both verbs here read
them back.

**Read-only.** No verb here writes to the DB. Reads the
already-persisted M7.3 rows per :doc:`../../roadmap/MILESTONE_8_PLANNING.md`
§5.a Option C (hybrid, compute-on-request v1). M7.3 already did the
percentile math at snapshot time, so this verb is a straight
select-and-order.

**Tenant-scoped.** Every verb takes ``dealership`` as a required
first positional argument. The verb enforces tenant scoping in its
own querysets; there is no shared filter-manager layer.

**Stage validation.** The verb rejects unknown ``stage`` values
with :class:`ValueError`, letting the HTTP endpoint translate to
HTTP 400 rather than silently returning an empty list. Silent-empty
would hide operator typos in the query-arg.

Source of truth: ``docs/roadmap/MILESTONE_8_PLANNING.md`` §1.4 +
§7 M8.3.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from ...models import (
    VEHICLE_STAGE_CHOICES,
    VEHICLE_STAGE_FRONTLINE,
    Dealership,
    Sale,
    StageAgingSnapshot,
    VehicleStageEvent,
)


ZERO = Decimal("0.00")


# Precomputed set of valid stage keys for fast validation. Built at
# module load; the vocabulary is small and static.
_VALID_STAGE_KEYS: frozenset[str] = frozenset(
    key for key, _display in VEHICLE_STAGE_CHOICES
)


@dataclass(frozen=True)
class AgingTrendPoint:
    """One time-series point — the state of one lifecycle stage at
    one snapshot moment.

    Frozen because the aggregation output is immutable; callers
    should project into a serialized shape rather than mutate.

    Fields mirror :class:`StageAgingSnapshot` verbatim — the M7.3
    substrate already carries every field the M8.5 dashboard needs
    to plot a per-stage p50 / p90 / count trend line. No derivation
    here beyond time-ordering + windowing.
    """

    snapshot_at: dt.datetime
    vehicle_count: int
    p50_days: int
    p90_days: int


def stage_aging_trend(
    dealership: Dealership,
    stage: str,
    *,
    window_days: int = 30,
) -> list[AgingTrendPoint]:
    """Q5 + Q9 aggregation — per-stage aging time-series.

    Answers *"what are the aging trends per stage over the last N
    months?"* (Q5) and *"which lifecycle stages consistently exceed
    target dwell time?"* (Q9). Both cite RECON §pain #7 + #12; both
    feed off the M7.3 snapshot substrate.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    stage : str
        The lifecycle stage to trend — one of
        :data:`VEHICLE_STAGE_CHOICES` keys (``"incoming"`` /
        ``"inspection"`` / ``"recon"`` / ``"qc"`` / ``"detail"`` /
        ``"photography"`` / ``"listing"`` / ``"frontline"`` /
        ``"wholesale_out"`` / ``"hold_reserved"`` /
        ``"company_use"`` / ``"off_market"``).
    window_days : int, optional
        Number of days of history to return. Default 30. Filters
        ``snapshot_at >= now - window_days``.

    Returns
    -------
    list[AgingTrendPoint]
        Snapshots ordered by ``snapshot_at`` ascending — the M8.5
        dashboard's per-stage trend line reads left-to-right.
        Empty tenant / stage with no snapshots in the window
        returns ``[]``.

    Raises
    ------
    ValueError
        If ``stage`` is not a member of
        :data:`VEHICLE_STAGE_CHOICES`. The HTTP endpoint translates
        this into HTTP 400 so a query-arg typo surfaces as an
        error rather than a misleading empty result.
    """
    if stage not in _VALID_STAGE_KEYS:
        raise ValueError(
            f"Unknown lifecycle stage: {stage!r}. "
            f"Expected one of {sorted(_VALID_STAGE_KEYS)}."
        )

    since = timezone.now() - dt.timedelta(days=window_days)
    qs = (
        StageAgingSnapshot.objects.filter(
            dealership=dealership,
            stage=stage,
            snapshot_at__gte=since,
        )
        .order_by("snapshot_at")
        .values("snapshot_at", "vehicle_count", "p50_days", "p90_days")
    )
    return [AgingTrendPoint(**row) for row in qs]


# ---------------------------------------------------------------------------
# Q8 proxy — days-at-frontline (SESSION_097)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DaysAtFrontlineReport:
    """The Q8 proxy summary — an aggregate readout of the ``frontline``
    stage's aging behavior across a rolling window.

    Frozen because the aggregation output is immutable; callers
    should project into a serialized shape rather than mutate.

    **Proxy semantics.** True inventory-turn (Q8's original
    formulation) requires M9 Sale substrate: "days from acquisition
    to sale." M8 v1 approximates via M7.3 snapshots — how long
    vehicles sit in the ``frontline`` stage. This is a valid
    directional signal (stability + long-tail dwell) even though it
    is not literally days-to-sale. When M9 Sale substrate ships, a
    true ``inventory_turn`` verb replaces or complements this
    proxy.

    Fields:

    - ``snapshot_count`` — number of M7.3 snapshots that landed on
      the ``frontline`` stage inside the window. Zero implies
      "empty window" (no M7.3 runs, or no frontline vehicles at
      any run).
    - ``mean_p50_days`` — mean of ``StageAgingSnapshot.p50_days``
      across the window's frontline snapshots. Quantized to two
      decimal places. ``None`` when ``snapshot_count == 0``.
    - ``mean_p90_days`` — mean of ``StageAgingSnapshot.p90_days``
      across the same set. Quantized to 2dp. ``None`` when
      ``snapshot_count == 0``.
    - ``latest_vehicle_count`` — ``vehicle_count`` from the most
      recent snapshot in the window (i.e. the current-frontline
      inventory size, as of the last M7.3 run). ``None`` when
      ``snapshot_count == 0``.
    - ``latest_snapshot_at`` — the ``snapshot_at`` timestamp of the
      most recent snapshot. Callers render "last measured at ..."
      so the operator knows how fresh the number is. ``None`` when
      ``snapshot_count == 0``.
    """

    snapshot_count: int
    mean_p50_days: Optional[Decimal]
    mean_p90_days: Optional[Decimal]
    latest_vehicle_count: Optional[int]
    latest_snapshot_at: Optional[dt.datetime]


def days_at_frontline_proxy(
    dealership: Dealership,
    *,
    window_days: int = 30,
) -> DaysAtFrontlineReport:
    """Q8 proxy aggregation — days-at-frontline across a rolling
    window.

    Answers *"what is the inventory turn / days-to-sale?"* (Q8) —
    proxied via M7.3 ``frontline``-stage snapshots pending M9 Sale
    substrate. See ``MILESTONE_8_PLANNING.md`` §1.7 for the proxy
    rationale.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_days : int, optional
        Number of days of history. Default 30. Filters
        ``snapshot_at >= now - window_days``.

    Returns
    -------
    DaysAtFrontlineReport
        Structured summary. Empty window (no frontline snapshots in
        the window) produces a report with ``snapshot_count == 0``
        and every other field ``None`` — the "no signal" state is
        distinct from "average happens to be zero."

    Notes
    -----
    Read-only. Reads only ``stage='frontline'`` snapshots — other
    lifecycle stages are addressed by :func:`stage_aging_trend`
    (Q5 + Q9).
    """
    since = timezone.now() - dt.timedelta(days=window_days)
    qs = (
        StageAgingSnapshot.objects.filter(
            dealership=dealership,
            stage=VEHICLE_STAGE_FRONTLINE,
            snapshot_at__gte=since,
        )
        .order_by("-snapshot_at")
        .values("snapshot_at", "vehicle_count", "p50_days", "p90_days")
    )
    rows = list(qs)
    if not rows:
        return DaysAtFrontlineReport(
            snapshot_count=0,
            mean_p50_days=None,
            mean_p90_days=None,
            latest_vehicle_count=None,
            latest_snapshot_at=None,
        )

    p50_total = sum(row["p50_days"] for row in rows)
    p90_total = sum(row["p90_days"] for row in rows)
    n = len(rows)

    mean_p50 = (Decimal(p50_total) / Decimal(n)).quantize(Decimal("0.01"))
    mean_p90 = (Decimal(p90_total) / Decimal(n)).quantize(Decimal("0.01"))

    latest = rows[0]  # -snapshot_at ordering above
    return DaysAtFrontlineReport(
        snapshot_count=n,
        mean_p50_days=mean_p50,
        mean_p90_days=mean_p90,
        latest_vehicle_count=latest["vehicle_count"],
        latest_snapshot_at=latest["snapshot_at"],
    )


# ---------------------------------------------------------------------------
# Q8 true — inventory turn / days-to-sale (SESSION_102, M9.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InventoryTurnReport:
    """The Q8 true summary — days-from-frontline-to-sale statistics
    across a rolling window of closed sales.

    The M9.3 counterpart to :class:`DaysAtFrontlineReport` (the M8.4
    proxy). Both verbs coexist per M8 §6 lesson 11 — the proxy stays
    valid ("how long are vehicles sitting on frontline today?") and
    the true verb answers the original operational question ("what
    was the median days from frontline entry to sale?").

    Frozen because the aggregation output is immutable; callers
    should project into a serialized shape rather than mutate.

    **Days-to-sale semantics.** For each :class:`Sale` closed in the
    window, the days-to-sale is
    ``sale.sale_date - min(VehicleStageEvent.entered_at.date() for
    event in sale.vehicle.stage_events where to_stage=frontline)``.
    The MIN over frontline events handles a vehicle that returned
    to frontline (rare — the M5 lifecycle permits regression). Only
    vehicles whose stage-event log records at least one frontline
    entry contribute; vehicles with no frontline entry are skipped
    (would be a data-quality issue — every sold vehicle should have
    passed through frontline).

    Fields:

    - ``sold_count`` — number of sold vehicles in the window that
      contribute to the distribution (i.e. have both a Sale in the
      window and at least one frontline stage-event).
    - ``mean_days`` — arithmetic mean of days-to-sale across the
      contributing vehicles. Quantized to two decimal places.
      ``None`` when ``sold_count == 0``.
    - ``p50_days`` — median (50th percentile). ``None`` when
      ``sold_count == 0``. Integer — days are counted whole.
    - ``p90_days`` — 90th percentile. ``None`` when
      ``sold_count == 0``. Integer.
    - ``min_days`` — minimum days-to-sale. ``None`` when
      ``sold_count == 0``. Integer.
    - ``max_days`` — maximum days-to-sale. ``None`` when
      ``sold_count == 0``. Integer.
    """

    sold_count: int
    mean_days: Optional[Decimal]
    p50_days: Optional[int]
    p90_days: Optional[int]
    min_days: Optional[int]
    max_days: Optional[int]


def _percentile(sorted_values: list[int], pct: int) -> int:
    """Return the ``pct``-th percentile of a sorted list of integers
    using the "nearest-rank" method (matches numpy's default
    ``interpolation="nearest"``-like behavior for integer buckets).

    Kept as a local helper — the vocabulary is small (p50 + p90),
    the M7.3 snapshot code has its own percentile logic, and taking
    a numpy dependency here would be disproportionate.
    """
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty list.")
    # Nearest-rank: rank = ceil(pct / 100 * n).
    n = len(sorted_values)
    rank = max(1, (pct * n + 99) // 100)
    return sorted_values[rank - 1]


def inventory_turn(
    dealership: Dealership,
    *,
    window_days: int = 90,
) -> InventoryTurnReport:
    """Q8 true aggregation — days-from-frontline-to-sale over a
    rolling window.

    Answers *"what is the true inventory turn / days-to-sale?"* —
    the operational question :func:`days_at_frontline_proxy` (M8.4)
    could only proxy while the M9 Sale substrate was pending.
    Reads :class:`VehicleStageEvent` for frontline entries + M9.1
    :class:`Sale` for the close-out event and computes per-vehicle
    days-to-sale.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_days : int, optional
        Number of days of history to return. Default 90.
        Filters ``sale_date >= today - window_days``.

    Returns
    -------
    InventoryTurnReport
        Summary of the days-to-sale distribution across the
        window. Empty window (no sales OR no vehicles with
        frontline entries) produces a report with
        ``sold_count == 0`` and every percentile field ``None`` —
        the "no signal" state is distinct from "distribution
        happens to be zero."

    Notes
    -----
    Read-only. Vehicles with a Sale but no ``frontline``
    :class:`VehicleStageEvent` are skipped (data-quality issue —
    every sold vehicle should have passed through frontline). A
    dedicated "sold-without-frontline-event" data-quality report
    can land later if operator evidence surfaces need.
    """
    today = timezone.now().date()
    since = today - dt.timedelta(days=window_days)

    sale_qs = Sale.objects.filter(
        dealership=dealership,
        sale_date__gte=since,
    ).values_list("vehicle_id", "sale_date")

    sales_by_vehicle: dict[int, dt.date] = dict(sale_qs)
    if not sales_by_vehicle:
        return InventoryTurnReport(
            sold_count=0,
            mean_days=None,
            p50_days=None,
            p90_days=None,
            min_days=None,
            max_days=None,
        )

    # Pull every frontline stage-event for the sold vehicles in one
    # query. For each vehicle we want the earliest ``entered_at`` on
    # a ``frontline`` transition — the "first arrival at frontline"
    # is the reference point for days-to-sale. Later re-entries do
    # not restart the clock (a vehicle bounced back to recon and
    # returned to frontline is still "the same customer-facing
    # inventory item," not a fresh arrival).
    event_qs = VehicleStageEvent.objects.filter(
        dealership=dealership,
        vehicle_id__in=sales_by_vehicle.keys(),
        to_stage=VEHICLE_STAGE_FRONTLINE,
    ).values_list("vehicle_id", "entered_at")

    earliest_frontline_by_vehicle: dict[int, dt.datetime] = {}
    for vehicle_id, entered_at in event_qs:
        current = earliest_frontline_by_vehicle.get(vehicle_id)
        if current is None or entered_at < current:
            earliest_frontline_by_vehicle[vehicle_id] = entered_at

    # Compute per-vehicle days-to-sale for contributors only.
    days_values: list[int] = []
    for vehicle_id, sale_date in sales_by_vehicle.items():
        entered_at = earliest_frontline_by_vehicle.get(vehicle_id)
        if entered_at is None:
            # Sold vehicle with no frontline entry — data-quality
            # gap. Skip per docstring.
            continue
        delta = (sale_date - entered_at.date()).days
        # Guard: sale before frontline entry (should not happen —
        # would mean the vehicle sold before ever reaching
        # frontline). Skip rather than pollute the distribution
        # with negatives.
        if delta < 0:
            continue
        days_values.append(delta)

    if not days_values:
        return InventoryTurnReport(
            sold_count=0,
            mean_days=None,
            p50_days=None,
            p90_days=None,
            min_days=None,
            max_days=None,
        )

    n = len(days_values)
    total = sum(days_values)
    mean = (Decimal(total) / Decimal(n)).quantize(Decimal("0.01"))
    sorted_days = sorted(days_values)

    return InventoryTurnReport(
        sold_count=n,
        mean_days=mean,
        p50_days=_percentile(sorted_days, 50),
        p90_days=_percentile(sorted_days, 90),
        min_days=sorted_days[0],
        max_days=sorted_days[-1],
    )

"""Milestone 8 · Increment 1 (SESSION_094) + Increment 4 (SESSION_097) — acquisition-adjacent analytics.

Aggregations grouped by acquisition-time attributes:

- :func:`recon_cost_per_source` (Q1, M8.1) — reads
  :class:`VehicleAcquisition.source` + :class:`VehicleCost` to roll
  up recon cost per acquisition source.
- :func:`vehicle_type_recon_cost` (Q3 proxy, M8.4) — reads
  :class:`Vehicle` (make + model) + :class:`VehicleCost` to roll up
  recon cost per vehicle-type. **This is a proxy** for the Q3
  "vehicle-type profitability" question §1.2 originally posed;
  true profitability depends on M9 Sale substrate not yet shipped.
  See ``MILESTONE_8_PLANNING.md`` §0.a SESSION_097 for the option
  matrix + rationale for the proxy choice.

**Read-only.** No verb here writes to the DB — the aggregations run
against live rows per :doc:`../../roadmap/MILESTONE_8_PLANNING.md`
§5.a Option C (hybrid, compute-on-request v1). If evidence surfaces
latency pain, an M7-Beat materialization layer can wrap this without
touching the verb shape.

**Tenant-scoped.** Every verb takes ``dealership`` as a required
first positional argument. The verb enforces tenant scoping in its
own querysets; there is no shared filter-manager layer.

Source of truth: ``docs/roadmap/MILESTONE_8_PLANNING.md`` §1.2 +
§7 M8.1 + §7 M8.4 (as amended §0.a SESSION_097).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db.models import Sum

from ...models import (
    ACQUISITION_SOURCE_CHOICES,
    RECON_CATEGORIES,
    Dealership,
    Sale,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)


# Precomputed lookup for the "auction" / "trade-in" / etc. display
# names. Precomputed at module load so the aggregation loop doesn't
# rebuild it per row. The vocabulary is small and static.
_SOURCE_DISPLAY_BY_KEY: dict[str, str] = dict(ACQUISITION_SOURCE_CHOICES)


ZERO = Decimal("0.00")


@dataclass(frozen=True)
class SourcePerformanceRow:
    """One aggregation row — recon spend rolled up under one
    acquisition source.

    Frozen because the aggregation output is immutable; callers should
    project into a serialized shape rather than mutate.

    Fields:

    - ``source`` — the raw source key (``"auction"`` / ``"trade"`` /
      ``"wholesale"`` / etc.), matching :data:`ACQUISITION_SOURCE_CHOICES`.
    - ``source_display`` — the human-readable label (``"Auction"`` /
      ``"Trade-in"``). Precomputed so callers do not repeat the
      ``get_..._display`` lookup.
    - ``vehicle_count`` — distinct vehicles from this source that had
      any recon-category committed cost in the window.
    - ``total_recon_cost`` — sum of committed (``is_estimate=False``)
      recon-category ``VehicleCost.amount`` in the window across those
      vehicles.
    - ``mean_recon_cost`` — ``total_recon_cost / vehicle_count``
      quantized to two decimal places. Callers rendering "$1,234.56"
      strings do not need to re-round.
    """

    source: str
    source_display: str
    vehicle_count: int
    total_recon_cost: Decimal
    mean_recon_cost: Decimal


def recon_cost_per_source(
    dealership: Dealership,
    *,
    window_start: Optional[dt.date] = None,
    window_end: Optional[dt.date] = None,
) -> list[SourcePerformanceRow]:
    """Q1 aggregation — recon spend rolled up per acquisition source.

    Answers the operational question *"which auctions produce the
    highest recon costs?"* (INVENTORY §"To Ownership"). The row-per-
    source shape is what the M8.5 dashboard's per-source table +
    chart consumes; today's M8.1 endpoint returns the same shape as
    JSON.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_start : dt.date, optional
        Inclusive lower bound on ``VehicleCost.incurred_at``. ``None``
        means "no lower bound" (all history).
    window_end : dt.date, optional
        Inclusive upper bound on ``VehicleCost.incurred_at``. ``None``
        means "no upper bound" (through today).

    Returns
    -------
    list[SourcePerformanceRow]
        One row per acquisition source that produced any committed
        recon cost in the window. Sources with zero committed recon
        cost in the window are omitted — absence signals "no signal
        here." Rows sorted by ``total_recon_cost`` descending so the
        biggest cost centers land at the top of the operator's view.

    Notes
    -----
    Read-only. Committed costs only (``is_estimate=False``) — the
    M8.2 vendor-performance verb will separately surface estimated-vs-
    actual variance where that is the load-bearing signal. Recon
    categories only (``RECON_CATEGORIES``) — floor-plan interest,
    admin fees, and photography are excluded per the M2 category
    partition.
    """
    # Constrain the cost query first: tenant + recon categories +
    # committed + optional window. This is the outer filter every
    # aggregation-loop pass reuses.
    cost_qs = VehicleCost.objects.filter(
        dealership=dealership,
        category__in=RECON_CATEGORIES,
        is_estimate=False,
    )
    if window_start is not None:
        # ``incurred_at`` is a DateTimeField; combine the date with
        # the start-of-day so a window_start of 2026-08-01 includes
        # rows dated 2026-08-01 00:00:00 through 23:59:59.
        cost_qs = cost_qs.filter(incurred_at__date__gte=window_start)
    if window_end is not None:
        cost_qs = cost_qs.filter(incurred_at__date__lte=window_end)

    # Pull acquisition source per (dealership-scoped) vehicle in a
    # single query. Vehicles without an acquisition row are skipped —
    # no source known means the aggregation cannot attribute the
    # recon cost to a bucket. Operators posting recon costs against
    # a vehicle that never had an acquisition recorded is an M2 data-
    # quality issue this verb deliberately does not paper over.
    source_by_vehicle: dict[int, str] = dict(
        VehicleAcquisition.objects.filter(dealership=dealership).values_list(
            "vehicle_id", "source"
        )
    )

    # Aggregate cost rows by vehicle. ``Sum`` handles negatives
    # (M2 correction rows) — a reversal legitimately reduces the
    # rolled-up total.
    cost_by_vehicle_qs = (
        cost_qs.values("vehicle_id")
        .annotate(total=Sum("amount"))
        .order_by()  # strip default ordering so the group-by stays clean
    )

    totals_by_source: dict[str, Decimal] = {}
    counts_by_source: dict[str, int] = {}
    for row in cost_by_vehicle_qs:
        vehicle_id = row["vehicle_id"]
        source = source_by_vehicle.get(vehicle_id)
        if source is None:
            # Vehicle has recon cost but no acquisition record — skip
            # per the "no source known" rule above.
            continue
        total = row["total"] or ZERO
        totals_by_source[source] = (
            totals_by_source.get(source, ZERO) + total
        )
        counts_by_source[source] = counts_by_source.get(source, 0) + 1

    rows: list[SourcePerformanceRow] = []
    for source, total in totals_by_source.items():
        count = counts_by_source[source]
        mean = (total / count).quantize(Decimal("0.01")) if count > 0 else ZERO
        rows.append(
            SourcePerformanceRow(
                source=source,
                source_display=_SOURCE_DISPLAY_BY_KEY.get(source, source),
                vehicle_count=count,
                total_recon_cost=total,
                mean_recon_cost=mean,
            )
        )

    # Sort by total spend descending — the operator's default view
    # prioritizes the biggest cost centers. Deterministic tiebreak on
    # source key so equal-total rows have a stable order across runs.
    rows.sort(key=lambda r: (-r.total_recon_cost, r.source))
    return rows


# ---------------------------------------------------------------------------
# Q3 proxy — vehicle-type recon cost (SESSION_097)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VehicleTypeReconCostRow:
    """One aggregation row — recon spend rolled up under one
    ``(make, model)`` vehicle-type discriminator.

    Frozen because the aggregation output is immutable; callers
    should project into a serialized shape rather than mutate.

    **Discriminator choice.** ``(make, model)`` matches how a dealer
    thinks operationally ("F-150s cost more to prep than Escapes").
    ``year`` was rejected — buckets get too small for a mid-sized
    dealer's window. ``trim`` was rejected — noisy free-text field.
    ``body_style`` was rejected — 5-bucket vocabulary too coarse for
    the acquisition-strategy signal this proxy supports.

    Fields:

    - ``make`` — the vehicle make (``"Ford"`` / ``"Chevrolet"`` /
      etc.) as stored on :attr:`Vehicle.make`.
    - ``model`` — the vehicle model (``"F-150"`` / ``"Escape"`` /
      etc.) as stored on :attr:`Vehicle.model`.
    - ``vehicle_count`` — distinct vehicles of this type that had
      any committed recon cost in the window.
    - ``total_recon_cost`` — sum of committed
      (``is_estimate=False``) recon-category
      :attr:`VehicleCost.amount` in the window across those
      vehicles.
    - ``mean_recon_cost`` — ``total_recon_cost / vehicle_count``
      quantized to two decimal places.
    """

    make: str
    model: str
    vehicle_count: int
    total_recon_cost: Decimal
    mean_recon_cost: Decimal


def vehicle_type_recon_cost(
    dealership: Dealership,
    *,
    window_start: Optional[dt.date] = None,
    window_end: Optional[dt.date] = None,
) -> list[VehicleTypeReconCostRow]:
    """Q3 proxy aggregation — recon spend rolled up per vehicle-type.

    Answers the operational question *"which vehicle types cost the
    most to prep?"* — the proxy for §1.2's *"which vehicle types
    produce the highest profit?"* pending M9 Sale substrate. See
    ``MILESTONE_8_PLANNING.md`` §0.a SESSION_097 for the option
    matrix.

    Parameters mirror :func:`recon_cost_per_source` (Q1) exactly —
    the operator-facing window semantics are the same.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_start : dt.date, optional
        Inclusive lower bound on ``VehicleCost.incurred_at``.
        ``None`` means "no lower bound" (all history).
    window_end : dt.date, optional
        Inclusive upper bound on ``VehicleCost.incurred_at``.
        ``None`` means "no upper bound" (through today).

    Returns
    -------
    list[VehicleTypeReconCostRow]
        One row per ``(make, model)`` combination that produced any
        committed recon cost in the window. Rows with zero spend
        omitted — absence signals "no signal here." Rows sorted by
        ``total_recon_cost`` descending; deterministic tiebreak on
        ``(make, model)`` ascending.

    Notes
    -----
    Read-only. Committed costs only (``is_estimate=False``). Recon
    categories only (``RECON_CATEGORIES``) — floor-plan, admin, and
    photography excluded per the M2 category partition, same as
    Q1.
    """
    cost_qs = VehicleCost.objects.filter(
        dealership=dealership,
        category__in=RECON_CATEGORIES,
        is_estimate=False,
    )
    if window_start is not None:
        cost_qs = cost_qs.filter(incurred_at__date__gte=window_start)
    if window_end is not None:
        cost_qs = cost_qs.filter(incurred_at__date__lte=window_end)

    # Pull the vehicle-type discriminator per vehicle in one query.
    # Tenant-scoped so a vehicle owned by another dealership never
    # enters this map (defense-in-depth alongside the ``dealership``
    # filter on the cost query above).
    type_by_vehicle: dict[int, tuple[str, str]] = {
        vid: (make, model)
        for vid, make, model in Vehicle.objects.filter(
            dealership=dealership
        ).values_list("id", "make", "model")
    }

    # Aggregate cost rows by vehicle. ``Sum`` handles negatives
    # (M2 correction rows) — a reversal legitimately reduces the
    # rolled-up total.
    cost_by_vehicle_qs = (
        cost_qs.values("vehicle_id")
        .annotate(total=Sum("amount"))
        .order_by()  # strip default ordering so the group-by stays clean
    )

    totals_by_type: dict[tuple[str, str], Decimal] = {}
    counts_by_type: dict[tuple[str, str], int] = {}
    for row in cost_by_vehicle_qs:
        vehicle_id = row["vehicle_id"]
        vehicle_type = type_by_vehicle.get(vehicle_id)
        if vehicle_type is None:
            # Vehicle disappeared between the cost query and the
            # vehicle query (rare but possible under concurrent
            # deletion). Skip — the missing vehicle also cannot
            # anchor a type-bucket.
            continue
        total = row["total"] or ZERO
        totals_by_type[vehicle_type] = (
            totals_by_type.get(vehicle_type, ZERO) + total
        )
        counts_by_type[vehicle_type] = (
            counts_by_type.get(vehicle_type, 0) + 1
        )

    rows: list[VehicleTypeReconCostRow] = []
    for (make, model), total in totals_by_type.items():
        count = counts_by_type[(make, model)]
        mean = (total / count).quantize(Decimal("0.01")) if count > 0 else ZERO
        rows.append(
            VehicleTypeReconCostRow(
                make=make,
                model=model,
                vehicle_count=count,
                total_recon_cost=total,
                mean_recon_cost=mean,
            )
        )

    # Sort by total spend desc; deterministic tiebreak on
    # ``(make, model)`` asc.
    rows.sort(key=lambda r: (-r.total_recon_cost, r.make, r.model))
    return rows


# ---------------------------------------------------------------------------
# Q3 true — vehicle-type profitability (SESSION_102, M9.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VehicleTypeProfitabilityRow:
    """One aggregation row — true profitability rolled up under one
    ``(make, model)`` vehicle-type discriminator.

    The M9.3 counterpart to :class:`VehicleTypeReconCostRow` (the M8.4
    proxy). Both verbs coexist per M8 §6 lesson 11 — the proxy stays
    valid ("what did we spend to prep?") and the true verb answers
    the original operational question ("what did we realize on
    it?").

    Frozen because the aggregation output is immutable; callers
    should project into a serialized shape rather than mutate.

    **Discriminator choice.** Same ``(make, model)`` grouping as
    the M8.4 proxy — dealer operators reason in terms of models,
    not body-styles. Consistency across the two verbs matters more
    than optimizing per verb.

    Fields:

    - ``make`` / ``model`` — the vehicle-type discriminator, as
      stored on :attr:`Vehicle.make` + :attr:`Vehicle.model`.
    - ``sold_count`` — distinct sold vehicles of this type whose
      :attr:`Sale.sale_date` fell inside the window.
    - ``total_sale_gross`` — sum of :attr:`Sale.gross_realized`
      across those vehicles. Signed :class:`Decimal` — negative
      when the type ran a net loss over the window.
    - ``total_sold_price`` — sum of :attr:`Sale.sold_price` across
      the same vehicles. Included so the caller can compute the
      aggregate gross-margin ratio (``total_sale_gross /
      total_sold_price``) at rendering time without a second
      round-trip.
    - ``mean_gross_pct`` — mean of per-vehicle gross-margin
      percentages (``gross_realized / sold_price * 100`` per
      Sale, then averaged) quantized to two decimal places.
      Equal-weighted across vehicles regardless of price, so a
      single high-price sale does not dominate. Callers wanting
      revenue-weighted margin should compute the aggregate ratio
      from the two totals.
    """

    make: str
    model: str
    sold_count: int
    total_sale_gross: Decimal
    total_sold_price: Decimal
    mean_gross_pct: Decimal


def vehicle_type_profitability(
    dealership: Dealership,
    *,
    window_start: Optional[dt.date] = None,
    window_end: Optional[dt.date] = None,
) -> list[VehicleTypeProfitabilityRow]:
    """Q3 true aggregation — profitability per vehicle-type.

    Answers *"which vehicle types produce the highest profit?"* —
    the operational question ``vehicle_type_recon_cost`` (M8.4)
    could only proxy while the M9 Sale substrate was pending.
    Reads :attr:`Sale.gross_realized` (denormalized at M9.1 write
    time via :func:`services.sale.record_sale`) grouped by
    ``(Vehicle.make, Vehicle.model)``.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_start : dt.date, optional
        Inclusive lower bound on :attr:`Sale.sale_date`. ``None``
        means "no lower bound" (all history).
    window_end : dt.date, optional
        Inclusive upper bound on :attr:`Sale.sale_date`. ``None``
        means "no upper bound" (through today).

    Returns
    -------
    list[VehicleTypeProfitabilityRow]
        One row per ``(make, model)`` combination that produced
        any sale in the window. Rows sorted by
        ``total_sale_gross`` descending; deterministic tiebreak on
        ``(make, model)`` ascending. Vehicle-types with zero
        sales in the window are omitted — absence signals "no
        signal here."

    Notes
    -----
    Read-only. Reads ``Sale.gross_realized`` denormalized column
    directly rather than recomputing via
    :func:`services.sale.gross_realized` per row — the M9.1 verb
    denormalized at write time precisely so aggregations stay
    single-query.
    """
    sale_qs = Sale.objects.filter(dealership=dealership).select_related(
        "vehicle"
    )
    if window_start is not None:
        sale_qs = sale_qs.filter(sale_date__gte=window_start)
    if window_end is not None:
        sale_qs = sale_qs.filter(sale_date__lte=window_end)

    # Pull all in-window sale rows in one query with the vehicle
    # discriminator via select_related. The per-vehicle aggregation
    # runs in Python — the vocabulary of vehicle-types is small enough
    # that iterating in the app process avoids a group-by-with-count
    # subquery that would need denormalized make/model on Sale.
    totals_by_type: dict[tuple[str, str], Decimal] = {}
    prices_by_type: dict[tuple[str, str], Decimal] = {}
    counts_by_type: dict[tuple[str, str], int] = {}
    pct_sum_by_type: dict[tuple[str, str], Decimal] = {}

    for sale in sale_qs:
        vehicle_type = (sale.vehicle.make, sale.vehicle.model)
        totals_by_type[vehicle_type] = (
            totals_by_type.get(vehicle_type, ZERO) + sale.gross_realized
        )
        prices_by_type[vehicle_type] = (
            prices_by_type.get(vehicle_type, ZERO) + sale.sold_price
        )
        counts_by_type[vehicle_type] = (
            counts_by_type.get(vehicle_type, 0) + 1
        )
        # Per-vehicle margin percentage. Guard against zero
        # sold_price — impossible in practice (DB has no such
        # constraint but M9.1 record_sale requires a positive
        # Decimal) but defensive.
        if sale.sold_price > 0:
            pct = (sale.gross_realized / sale.sold_price) * Decimal("100")
            pct_sum_by_type[vehicle_type] = (
                pct_sum_by_type.get(vehicle_type, ZERO) + pct
            )

    rows: list[VehicleTypeProfitabilityRow] = []
    for (make, model), total in totals_by_type.items():
        count = counts_by_type[(make, model)]
        pct_sum = pct_sum_by_type.get((make, model), ZERO)
        mean_pct = (
            (pct_sum / count).quantize(Decimal("0.01"))
            if count > 0
            else ZERO
        )
        rows.append(
            VehicleTypeProfitabilityRow(
                make=make,
                model=model,
                sold_count=count,
                total_sale_gross=total,
                total_sold_price=prices_by_type[(make, model)],
                mean_gross_pct=mean_pct,
            )
        )

    # Sort by total sale gross desc; deterministic tiebreak on
    # ``(make, model)`` asc so ties render stably across runs.
    rows.sort(key=lambda r: (-r.total_sale_gross, r.make, r.model))
    return rows

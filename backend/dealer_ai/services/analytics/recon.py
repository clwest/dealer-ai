"""Milestone 8 · Increment 2 (SESSION_095) — recon analytics.

Owns the aggregations rooted in M4 :class:`WorkOrder` — today: Q2 +
Q4 (:func:`vendor_performance`). Q7 (buyer estimate accuracy) is
deferred per ``MILESTONE_8_PLANNING.md`` §0.a (SESSION_095) — its
substrate (acquisition-buyer provenance) is not shipped.

**Read-only.** No verb here writes to the DB — the aggregations run
against live ``WorkOrder`` rows per §5.a Option C (hybrid, compute-
on-request v1). If evidence surfaces latency pain, an M7-Beat
materialization layer can wrap this without touching the verb shape.

**Tenant-scoped.** Every verb takes ``dealership`` as a required
first positional argument. The verb enforces tenant scoping in its
own querysets; there is no shared filter-manager layer.

Source of truth: ``docs/roadmap/MILESTONE_8_PLANNING.md`` §1.3 +
§7 M8.2 (as amended §0.a SESSION_095).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from ...models import (
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    WorkOrder,
)


ZERO = Decimal("0.00")


@dataclass(frozen=True)
class VendorPerformanceRow:
    """One aggregation row — recon performance rolled up under one
    outsourced vendor.

    Frozen because the aggregation output is immutable; callers
    should project into a serialized shape rather than mutate.

    Fields:

    - ``vendor_slug`` — the M4 :attr:`Vendor.slug`.
    - ``vendor_name`` — the display name captured at aggregation
      time (denormalized so callers do not repeat the FK read).
    - ``completed_count`` — number of completed outsourced WOs from
      this vendor in the window.
    - ``mean_completion_days`` — mean whole-days from
      ``approved_at.date()`` → ``completed_at.date()`` across the
      subset with both timestamps set. ``None`` when no such WO in
      the window (rare — completed WOs almost always have both).
    - ``mean_variance_pct`` — mean absolute variance of
      ``actual_cost`` vs ``estimated_cost``, expressed as a percent
      quantized to two decimal places. Denominator is
      ``estimated_cost``. WOs with null / zero ``estimated_cost`` or
      null ``actual_cost`` are excluded from the numerator + denom.
      ``None`` when nothing in the window has both non-null costs
      with a positive estimate.
    - ``over_budget_count`` — number of completed WOs in the window
      whose ``actual_cost > authorized_cost``. WOs with null
      ``authorized_cost`` skip this check (no explicit budget cap
      → cannot be "over" a cap that was never set). This matches
      the M4.3 approval-time authorization semantics.
    """

    vendor_slug: str
    vendor_name: str
    completed_count: int
    mean_completion_days: Optional[int]
    mean_variance_pct: Optional[Decimal]
    over_budget_count: int


def vendor_performance(
    dealership: Dealership,
    *,
    window_start: Optional[dt.date] = None,
    window_end: Optional[dt.date] = None,
) -> list[VendorPerformanceRow]:
    """Q2 + Q4 aggregation — vendor recon performance.

    Answers the operational questions *"which vendors finish
    fastest? which cost the most?"* (Q2) and *"which repairs are
    consistently underestimated?"* (Q4 — rolled up per-vendor as
    variance %). Both cite RECON §"To Ownership".

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_start : dt.date, optional
        Inclusive lower bound on ``WorkOrder.completed_at``. ``None``
        means "no lower bound" (all completed history).
    window_end : dt.date, optional
        Inclusive upper bound on ``WorkOrder.completed_at``. ``None``
        means "no upper bound" (through today).

    Returns
    -------
    list[VendorPerformanceRow]
        One row per vendor that had at least one completed
        outsourced WO in the window. Vendors with zero completed
        WOs in the window are omitted — absence signals "no signal
        here." Rows sorted by ``completed_count`` desc (highest-
        workload vendors first), tiebreak on vendor slug.

    Notes
    -----
    Read-only. Only ``venue='outsourced'`` WOs are aggregated —
    in-house work has no vendor. Only ``status='completed'`` WOs —
    in-flight WOs have no ``actual_cost`` yet and would distort
    every derived metric.
    """
    wo_qs = WorkOrder.objects.filter(
        dealership=dealership,
        status=WORK_ORDER_STATUS_COMPLETED,
        venue=WORK_ORDER_VENUE_OUTSOURCED,
        vendor__isnull=False,
    ).select_related("vendor")
    if window_start is not None:
        wo_qs = wo_qs.filter(completed_at__date__gte=window_start)
    if window_end is not None:
        wo_qs = wo_qs.filter(completed_at__date__lte=window_end)

    # Aggregate in Python. The metric set is small per vendor (dozens
    # to hundreds of WOs), the DB round-trip is one query, and
    # keeping the derivations in Python keeps the "when do we skip
    # a WO?" branches readable + testable without SQL COALESCE
    # gymnastics.
    per_vendor_state: dict[int, _VendorState] = {}
    for wo in wo_qs:
        state = per_vendor_state.get(wo.vendor_id)
        if state is None:
            state = _VendorState(
                slug=wo.vendor.slug, name=wo.vendor.name
            )
            per_vendor_state[wo.vendor_id] = state
        state.absorb(wo)

    rows: list[VendorPerformanceRow] = [
        state.to_row() for state in per_vendor_state.values()
    ]
    rows.sort(key=lambda r: (-r.completed_count, r.vendor_slug))
    return rows


# ---------------------------------------------------------------------------
# Internal per-vendor accumulator
# ---------------------------------------------------------------------------


class _VendorState:
    """Mutable accumulator for one vendor's rolled-up metrics.

    Kept as a private class (not a dataclass) because the shape is
    strictly internal — the public row is
    :class:`VendorPerformanceRow`, produced by :meth:`to_row` at the
    end of the aggregation pass.
    """

    __slots__ = (
        "slug",
        "name",
        "completed_count",
        "_completion_days_total",
        "_completion_days_n",
        "_variance_pct_total",
        "_variance_pct_n",
        "over_budget_count",
    )

    def __init__(self, *, slug: str, name: str) -> None:
        self.slug = slug
        self.name = name
        self.completed_count = 0
        # Completion-days accumulator — total + count so the final
        # mean is a straight integer division. Not every completed
        # WO has both timestamps (data-quality gap), so the count
        # here is <= completed_count in the worst case.
        self._completion_days_total = 0
        self._completion_days_n = 0
        # Variance accumulator — mean-absolute-percent across WOs
        # with both non-null costs + a positive estimate.
        self._variance_pct_total = ZERO
        self._variance_pct_n = 0
        self.over_budget_count = 0

    def absorb(self, wo: WorkOrder) -> None:
        self.completed_count += 1

        if wo.approved_at is not None and wo.completed_at is not None:
            days = (wo.completed_at.date() - wo.approved_at.date()).days
            # Clock-skew guard: mean_completion_days can't be
            # negative. If a data-entry error puts completed_at
            # before approved_at, clamp to 0 rather than skewing the
            # running mean. Matches M7.3's fresh-vehicle-in-stage
            # clamp precedent.
            self._completion_days_total += max(days, 0)
            self._completion_days_n += 1

        if (
            wo.actual_cost is not None
            and wo.estimated_cost is not None
            and wo.estimated_cost > ZERO
        ):
            variance = abs(wo.actual_cost - wo.estimated_cost)
            variance_pct = (variance / wo.estimated_cost) * Decimal("100")
            self._variance_pct_total += variance_pct
            self._variance_pct_n += 1

        # Over-budget: ``actual_cost > authorized_cost`` when the cap
        # is set. Skipping the check when ``authorized_cost is None``
        # mirrors M4.3 semantics — approval without an explicit cap
        # means "any amount OK to the extent estimated" and does not
        # produce a hard ceiling to be exceeded.
        if (
            wo.actual_cost is not None
            and wo.authorized_cost is not None
            and wo.actual_cost > wo.authorized_cost
        ):
            self.over_budget_count += 1

    def to_row(self) -> VendorPerformanceRow:
        mean_days: Optional[int] = None
        if self._completion_days_n > 0:
            mean_days = self._completion_days_total // self._completion_days_n

        mean_variance: Optional[Decimal] = None
        if self._variance_pct_n > 0:
            mean_variance = (
                self._variance_pct_total / self._variance_pct_n
            ).quantize(Decimal("0.01"))

        return VendorPerformanceRow(
            vendor_slug=self.slug,
            vendor_name=self.name,
            completed_count=self.completed_count,
            mean_completion_days=mean_days,
            mean_variance_pct=mean_variance,
            over_budget_count=self.over_budget_count,
        )

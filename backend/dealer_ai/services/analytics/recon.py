"""Milestone 8 · Increment 2 (SESSION_095) + Milestone 9 · Increment 4 (SESSION_103) — recon analytics.

Owns the aggregations rooted in M4 :class:`WorkOrder`:

- :func:`vendor_performance` (Q2 + Q4, M8.2) — per-vendor completion
  time + variance rollup.
- :func:`buyer_estimate_accuracy` (Q7, M9.4) — per-buyer recon-cost
  estimate accuracy. Reads the M9.1
  :attr:`VehicleAcquisition.buyer` FK for provenance.

**Q7 substrate journey.** M8.2 planning §1.8 spec was deferred at
SESSION_095 because :attr:`VehicleAcquisition.buyer` did not exist
(``MILESTONE_8_PLANNING.md`` §0.a SESSION_095). M9.1 shipped the
FK as a nullable additive extension (SESSION_100). M9.4 now
implements the verb — historical acquisition rows without buyer
provenance (buyer IS NULL) are excluded from the aggregation
rather than treated as a single anonymous bucket.

**Read-only.** No verb here writes to the DB — same posture as the
sibling verbs (§5.a Option C, compute-on-request v1).

**Tenant-scoped.** Every verb takes ``dealership`` as a required
first positional argument.

Source of truth: ``docs/roadmap/MILESTONE_8_PLANNING.md`` §1.3 +
§1.8 + §7 M8.2 (as amended §0.a SESSION_095) +
``docs/roadmap/MILESTONE_9_PLANNING.md`` §1.5 Q7 + §7 M9.4.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model

from ...models import (
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    VehicleAcquisition,
    WorkOrder,
)


User = get_user_model()


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


# ---------------------------------------------------------------------------
# Q7 — buyer_estimate_accuracy (SESSION_103, M9.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuyerAccuracyRow:
    """One aggregation row — recon-cost estimate accuracy rolled up
    under one acquisition buyer.

    Frozen because the aggregation output is immutable; callers
    should project into a serialized shape rather than mutate.

    Semantic — *"how accurate were this buyer's recon-cost
    expectations?"* The buyer's implicit expectation is the sum of
    :attr:`WorkOrder.estimated_cost` on vehicles they acquired; the
    reality is the sum of :attr:`WorkOrder.actual_cost`. The
    variance and bias metrics express how the two compare over the
    window.

    Fields:

    - ``buyer_user_id`` — the acquisition-buyer's User PK
      (:attr:`VehicleAcquisition.buyer`).
    - ``buyer_display`` — human-readable buyer identifier. Prefers
      the User's full name; falls back to username.
    - ``vehicle_count`` — distinct vehicles this buyer acquired in
      the window that had at least one completed WorkOrder with
      both non-null costs and a positive estimate.
    - ``work_order_count`` — completed WorkOrders across those
      vehicles that contributed to the variance / bias metrics.
    - ``mean_absolute_variance_pct`` — mean of ``|actual -
      estimated| / estimated * 100`` across contributing WOs.
      Quantized to 2dp. Never negative.
    - ``bias_pct`` — mean of signed ``(actual - estimated) /
      estimated * 100`` across contributing WOs. Positive =
      "under-estimator" (actuals ran higher than estimates on
      average); negative = "over-estimator." Quantized to 2dp.

    Both metrics equal-weight WOs (not vehicles) so a vehicle with
    ten WOs weighs more than a vehicle with one — matches how
    recon-cost variance manifests operationally.
    """

    buyer_user_id: int
    buyer_display: str
    vehicle_count: int
    work_order_count: int
    mean_absolute_variance_pct: Decimal
    bias_pct: Decimal


def _buyer_display_for(user) -> str:
    """Best available human-readable identifier for a User.

    Prefers ``get_full_name()`` when populated; falls back to
    ``username`` otherwise. Kept as a private helper so the
    endpoint layer's projection can be trivial.
    """
    full = (user.get_full_name() or "").strip()
    return full if full else user.username


def buyer_estimate_accuracy(
    dealership: Dealership,
    *,
    window_days: int = 90,
    buyer_user_id: Optional[int] = None,
) -> list[BuyerAccuracyRow]:
    """Q7 aggregation — per-buyer recon-cost estimate accuracy.

    Answers *"which buyer's estimates land closest to actuals?"*
    (RECON §"To Ownership" + M8 §1.8). Reads the M9.1
    :attr:`VehicleAcquisition.buyer` FK to attribute each
    :class:`WorkOrder` to the buyer whose acquisition brought the
    parent Vehicle in.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_days : int, optional
        Number of days of history. Default 90. Filters
        ``VehicleAcquisition.purchase_date >= today - window_days``
        — the buyer's "window activity" is measured by acquisitions
        they made, not by when the WOs completed. A buyer who
        acquired heavily 6 months ago and whose WOs completed
        yesterday would NOT appear in a 90-day window; that's
        intentional (the buyer's decisions predate the window).
    buyer_user_id : int, optional
        If provided, filters to that buyer only. Empty list when
        the buyer has no acquisitions in the window OR no
        contributing WorkOrders on those acquisitions. When
        ``None`` (default), returns rows for every buyer with
        contributing data.

    Returns
    -------
    list[BuyerAccuracyRow]
        One row per buyer with at least one contributing WO in the
        window. Rows sorted by ``mean_absolute_variance_pct`` asc
        (most accurate buyers first); deterministic tiebreak on
        ``buyer_user_id`` asc.

    Notes
    -----
    Read-only. **NULL-buyer acquisitions excluded** — historical
    rows written before M9.1 have no buyer provenance; treating
    them as an anonymous "unknown buyer" bucket would produce a
    misleading aggregation. Completed WOs only
    (``status='completed'``) with both non-null ``estimated_cost``
    + ``actual_cost`` and a positive estimate — matches the M8.2
    ``vendor_performance`` variance semantics.

    **Deviation from M8 §1.8 spec.** M8 planning specified single-
    buyer-row return (``-> BuyerAccuracyRow``). M9.4 ships list-
    returning to match the dashboard's needs (rank all buyers by
    accuracy in one call). Filtering by ``buyer_user_id`` recovers
    the single-buyer shape (0 or 1 rows). Recorded in
    ``MILESTONE_9_PLANNING.md`` §0.a SESSION_103.
    """
    today = dt.date.today()
    since = today - dt.timedelta(days=window_days)

    # Pull acquisitions in-window with non-null buyer. When
    # ``buyer_user_id`` is provided, filter further so downstream
    # aggregation only touches that buyer's data.
    acq_qs = VehicleAcquisition.objects.filter(
        dealership=dealership,
        purchase_date__gte=since,
        buyer__isnull=False,
    )
    if buyer_user_id is not None:
        acq_qs = acq_qs.filter(buyer_id=buyer_user_id)

    # Map vehicle_id → buyer_id so we can attribute WO cost variance
    # to the buyer. One query.
    buyer_by_vehicle: dict[int, int] = dict(
        acq_qs.values_list("vehicle_id", "buyer_id")
    )
    if not buyer_by_vehicle:
        return []

    # Pull contributing WOs across those vehicles in one query.
    # Completed only + both non-null costs + positive estimate —
    # matches vendor_performance's variance-eligibility gate.
    wo_qs = WorkOrder.objects.filter(
        dealership=dealership,
        vehicle_id__in=buyer_by_vehicle.keys(),
        status=WORK_ORDER_STATUS_COMPLETED,
        estimated_cost__isnull=False,
        actual_cost__isnull=False,
        estimated_cost__gt=ZERO,
    ).values_list("vehicle_id", "estimated_cost", "actual_cost")

    # Per-buyer accumulators. Nested vehicle_ids set so we can count
    # distinct vehicles that contributed.
    accum_by_buyer: dict[int, _BuyerAccum] = {}
    for vehicle_id, estimated, actual in wo_qs:
        buyer_id = buyer_by_vehicle[vehicle_id]
        accum = accum_by_buyer.get(buyer_id)
        if accum is None:
            accum = _BuyerAccum()
            accum_by_buyer[buyer_id] = accum
        accum.absorb(vehicle_id, estimated, actual)

    if not accum_by_buyer:
        return []

    # Resolve User rows for display in one query.
    users_by_id: dict[int, "User"] = {
        u.pk: u
        for u in User.objects.filter(pk__in=accum_by_buyer.keys())
    }

    rows: list[BuyerAccuracyRow] = []
    for buyer_id, accum in accum_by_buyer.items():
        user = users_by_id.get(buyer_id)
        display = _buyer_display_for(user) if user else f"user#{buyer_id}"
        rows.append(accum.to_row(buyer_id=buyer_id, buyer_display=display))

    # Most-accurate buyers first (lowest mean absolute variance).
    # Deterministic tiebreak on buyer_user_id asc.
    rows.sort(key=lambda r: (r.mean_absolute_variance_pct, r.buyer_user_id))
    return rows


class _BuyerAccum:
    """Mutable per-buyer accumulator for the Q7 aggregation pass.

    Kept private — the public row is :class:`BuyerAccuracyRow`,
    produced by :meth:`to_row` at the end of the pass.
    """

    __slots__ = (
        "_vehicle_ids",
        "_wo_count",
        "_abs_variance_total",
        "_signed_variance_total",
    )

    def __init__(self) -> None:
        self._vehicle_ids: set[int] = set()
        self._wo_count = 0
        self._abs_variance_total = ZERO
        self._signed_variance_total = ZERO

    def absorb(
        self,
        vehicle_id: int,
        estimated: Decimal,
        actual: Decimal,
    ) -> None:
        self._vehicle_ids.add(vehicle_id)
        self._wo_count += 1
        signed_pct = ((actual - estimated) / estimated) * Decimal("100")
        self._signed_variance_total += signed_pct
        self._abs_variance_total += abs(signed_pct)

    def to_row(
        self, *, buyer_id: int, buyer_display: str
    ) -> BuyerAccuracyRow:
        n = Decimal(self._wo_count)
        return BuyerAccuracyRow(
            buyer_user_id=buyer_id,
            buyer_display=buyer_display,
            vehicle_count=len(self._vehicle_ids),
            work_order_count=self._wo_count,
            mean_absolute_variance_pct=(
                self._abs_variance_total / n
            ).quantize(Decimal("0.01")),
            bias_pct=(
                self._signed_variance_total / n
            ).quantize(Decimal("0.01")),
        )

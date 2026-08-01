"""Milestone 2 · Increment 2 — deterministic per-vehicle ledger service.

The one place all Vehicle Investment Ledger arithmetic happens. Answers
the two Milestone 2 questions for any stock number:

- *"How much money do we have invested in this vehicle right now?"*
- *"What is today's true cost basis by category?"*

The service is deliberately narrow. It writes and reads. It does not:

- Expose HTTP endpoints (Milestone 2 · Increment 6).
- Enforce permissions (Milestone 2 · Increment 6 — the DRF permission
  layer, which is *distinct* from this layer's cross-tenant guard;
  see ``docs/roadmap/AUTHENTICATION_MODEL.md`` §1 four-layer
  separation).
- Compute properties on ``Vehicle`` (Milestone 2 · Increment 3 lands
  the ``@property`` accessors that delegate to :func:`compute_totals`).
- Run floor-plan accrual (Milestone 2 · Increment 4 lands the math
  helper + management command).
- Sanitize LLM output (Milestone 2 · Increment 5 lands the
  acquisition-price scrub).

Layer discipline (see ``AUTHENTICATION_MODEL.md`` §1):

- **Identity + authorization** — the view layer. Not this module.
- **Data-scoping** — this module. Every function accepts an
  explicit ``dealership`` kwarg and refuses to touch rows in any
  other tenant. This is a defense-in-depth belt; the model layer's
  ``clean()`` cross-tenant guard is the suspenders.
- **Business semantics** — this module. Whether ``total_investment``
  includes estimates or not is a business decision this module
  makes and locks with tests. See :class:`LedgerTotals`.

Semantic decision — *estimated spend is NOT invested money*:

- ``total_investment`` = acquisition totals + costs where
  ``is_estimate=False``. Money the store has *actually committed*.
- ``estimated_cost_total`` = costs where ``is_estimate=True``.
  Money *projected but not yet committed* (open work orders,
  planned repairs).
- ``projected_total_investment`` = the sum of both. Useful for
  pricing decisions but must never be conflated with sunk cost.

Rationale: labeling estimated spending as invested money would
mislead operators making disposition decisions ("keep reconning /
retail as-is / wholesale-out"). The ``is_estimate`` field exists
on ``VehicleCost`` precisely because this distinction matters at
decision time.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Tuple

from django.core.exceptions import ValidationError
from django.db.models import Sum

from ..models import (
    ADMIN_CATEGORIES,
    FLOORING_CATEGORIES,
    PHOTOGRAPHY_CATEGORIES,
    RECON_CATEGORIES,
    VEHICLE_COST_CATEGORY_CHOICES,
    Dealership,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)


ZERO = Decimal("0.00")

_VALID_CATEGORY_KEYS = frozenset(key for key, _ in VEHICLE_COST_CATEGORY_CHOICES)


class CrossTenantLedgerError(ValueError):
    """Raised when a ledger service function is called with a
    ``dealership`` that does not match the target ``Vehicle``'s
    dealership.

    Subclasses :class:`ValueError` so callers that catch
    ``ValueError`` (test code, generic error handlers) still work.
    Named specifically so log lines and API responses can identify
    the failure mode without string-matching an error message.

    This is the *service-layer* defense against cross-tenant writes.
    The *model layer* (``VehicleAcquisition.clean`` /
    ``VehicleCost.clean``) is the second line — belt + suspenders.
    Do not remove either.
    """


# ---- Totals dataclass ------------------------------------------------------


@dataclass(frozen=True)
class LedgerTotals:
    """Deterministic per-vehicle financial rollup.

    Every field is a :class:`Decimal` — never a float — so
    aggregation preserves 2-decimal-place precision without drift.
    Zero-cost vehicles get ``ZERO`` for every field, never ``None``.

    Fields split into three groups:

    1. **Category rollups** (actual costs only, ``is_estimate=False``):
       ``flooring_total``, ``recon_total``, ``administrative_total``,
       ``photography_total``. Photography kept separate from admin
       so the Milestone 6 photography surface can distinguish
       "shot for listing" from "shot for damage documentation" —
       see the module docstring in ``dealer_ai.models`` where
       ``PHOTOGRAPHY_CATEGORIES`` lives.

    2. **Aggregate actual + estimate views:**
       - ``acquisition_total`` — sum of every fee on the
         ``VehicleAcquisition`` row. Always actual (there is no
         ``is_estimate`` field on acquisition).
       - ``actual_cost_total`` — sum of the four category rollups
         above. All actual by construction.
       - ``estimated_cost_total`` — sum of ``VehicleCost.amount``
         across *any* category where ``is_estimate=True``.

    3. **Business bottom lines** — the numbers the operator
       actually asks for:
       - ``total_investment`` = ``acquisition_total +
         actual_cost_total``. Money committed. Excludes estimates.
         *This is the number to compare against asking price for
         projected front-end gross.*
       - ``projected_total_investment`` = ``total_investment +
         estimated_cost_total``. Money in the piece once every
         open estimate lands. *Never compare this against asking
         price to compute realized gross — it double-counts
         projected spend as invested money.*

    Frozen (``frozen=True``) so the dataclass is hashable and safe
    to pass across service boundaries without callers accidentally
    mutating a shared instance.
    """

    acquisition_total: Decimal
    flooring_total: Decimal
    recon_total: Decimal
    administrative_total: Decimal
    photography_total: Decimal
    actual_cost_total: Decimal
    estimated_cost_total: Decimal
    total_investment: Decimal
    projected_total_investment: Decimal


# ---- Cross-tenant guard ----------------------------------------------------


def _assert_same_tenant(vehicle: Vehicle, dealership: Dealership) -> None:
    """Raise :class:`CrossTenantLedgerError` when the target vehicle
    does not belong to the caller's dealership.

    Runs at every public service function's entry — the fail-closed
    belt. The model layer's ``clean()`` guard is the suspenders.
    """
    if vehicle.dealership_id != dealership.pk:
        raise CrossTenantLedgerError(
            f"Vehicle #{vehicle.stock_number} belongs to dealership "
            f"{vehicle.dealership_id}, not {dealership.pk}. Ledger "
            "writes and reads MUST match the tenant that owns the "
            "vehicle (AUTHENTICATION_MODEL.md §1 layer 4)."
        )


# ---- Acquisition upsert ----------------------------------------------------


def record_acquisition(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    source: str,
    purchase_price: Decimal,
    purchase_date,
    source_detail: str = "",
    buyer_fees: Decimal = ZERO,
    arbitration_fees: Decimal = ZERO,
    transportation_cost: Decimal = ZERO,
    title_acquisition_cost: Decimal = ZERO,
    notes: str = "",
) -> Tuple[VehicleAcquisition, bool]:
    """Create-or-update the vehicle's acquisition record.

    Upsert semantics: ``VehicleAcquisition`` is OneToOne with
    ``Vehicle``. First call for a given vehicle creates the row and
    returns ``(instance, True)``. Every subsequent call for the same
    vehicle updates the same row and returns ``(instance, False)``.
    The tuple shape matches Django's :meth:`get_or_create` /
    :meth:`update_or_create` convention so callers do not have to
    learn a new one.

    Never creates a second acquisition record for the same vehicle.
    The OneToOne schema constraint enforces this at the DB layer;
    this function respects it at the ORM layer.

    Every write path:

    - Refuses cross-tenant writes at entry
      (:class:`CrossTenantLedgerError`).
    - Runs ``full_clean()`` before saving — surfaces the model's
      ``clean()`` cross-tenant guard + choices validation before
      hitting the DB.
    - Passes ``dealership=`` explicitly per
      ``AUTHENTICATION_MODEL.md`` §8b (does not rely on the
      ``pre_save`` autofill signal).

    Fee arguments default to :data:`ZERO`. Trades and private-party
    acquisitions typically have no auction / broker / arbitration
    fees; the caller sets whichever fields are non-zero.
    """
    _assert_same_tenant(vehicle, dealership)

    try:
        acquisition = VehicleAcquisition.objects.get(vehicle=vehicle)
        created = False
    except VehicleAcquisition.DoesNotExist:
        acquisition = VehicleAcquisition(vehicle=vehicle)
        created = True

    acquisition.dealership = dealership
    acquisition.source = source
    acquisition.source_detail = source_detail
    acquisition.purchase_price = purchase_price
    acquisition.purchase_date = purchase_date
    acquisition.buyer_fees = buyer_fees
    acquisition.arbitration_fees = arbitration_fees
    acquisition.transportation_cost = transportation_cost
    acquisition.title_acquisition_cost = title_acquisition_cost
    acquisition.notes = notes

    # Model-level cross-tenant guard + choices validation. Belt +
    # suspenders — ``_assert_same_tenant`` above catches most calls,
    # this catches (a) a caller who bypasses the service and mutates
    # the row directly, and (b) any future ``clean`` invariant.
    acquisition.full_clean()
    acquisition.save()
    return acquisition, created


# ---- Cost entry ------------------------------------------------------------


def add_cost(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    category: str,
    amount: Decimal,
    incurred_at,
    vendor: str = "",
    reference: str = "",
    notes: str = "",
    is_estimate: bool = False,
    created_by=None,
) -> VehicleCost:
    """Post a single, immutable cost row against the vehicle.

    Every call creates exactly one new :class:`VehicleCost` row.
    Existing rows are never touched — corrections happen by posting
    a *reversing row* whose ``amount`` is the negative of the
    original and whose ``reference`` points back at the original.
    This matches accounting practice
    (``ACCOUNTING_DEPARTMENT_MAPPING.md`` §2.11) and removes an
    entire class of "when did that number change?" bugs.

    Correction workflows (edit / delete / recategorize a cost row)
    are deliberately NOT introduced in this milestone. If operator
    evidence surfaces a case that reversing rows cannot address,
    revisit the design; do not add ad-hoc mutation paths.

    Signed amounts are permitted — the reversing pattern needs
    them. A negative ``amount`` is not a domain error; it is a
    reversal, and every downstream aggregation (``compute_totals``)
    handles them correctly by simple :class:`Sum`.

    Every write path:

    - Refuses cross-tenant writes at entry
      (:class:`CrossTenantLedgerError`).
    - Validates the category is one of the 26 canonical values
      (raises :class:`ValueError` with a clear message before
      touching the DB — earlier than the model's choices
      validation, and with a service-appropriate exception type).
    - Runs ``full_clean()`` before saving.
    - Passes ``dealership=`` explicitly per ``AUTHENTICATION_MODEL.md``
      §8b.
    """
    _assert_same_tenant(vehicle, dealership)

    if category not in _VALID_CATEGORY_KEYS:
        raise ValueError(
            f"Unknown VehicleCost category: {category!r}. Valid "
            f"categories live in "
            f"``dealer_ai.models.VEHICLE_COST_CATEGORY_CHOICES``."
        )

    cost = VehicleCost(
        vehicle=vehicle,
        dealership=dealership,
        category=category,
        amount=amount,
        incurred_at=incurred_at,
        vendor=vendor,
        reference=reference,
        notes=notes,
        is_estimate=is_estimate,
        created_by=created_by,
    )
    cost.full_clean()
    cost.save()
    return cost


# ---- Read: deterministic totals --------------------------------------------


def _sum_category(vehicle: Vehicle, categories, *, is_estimate: bool) -> Decimal:
    """Sum ``VehicleCost.amount`` for a vehicle, restricted to a
    category group + estimate flag.

    Returns ``ZERO`` when the queryset is empty (Django's
    :meth:`aggregate` returns ``{"amount__sum": None}`` in that
    case; this helper coalesces).
    """
    result = (
        VehicleCost.objects.filter(
            vehicle=vehicle,
            category__in=categories,
            is_estimate=is_estimate,
        )
        .aggregate(total=Sum("amount"))
        .get("total")
    )
    return result if result is not None else ZERO


def _acquisition_total(vehicle: Vehicle) -> Decimal:
    """Sum every cash line on the acquisition row.

    Returns ``ZERO`` when the vehicle has no acquisition record.
    Sums: purchase_price + buyer_fees + arbitration_fees +
    transportation_cost + title_acquisition_cost.
    """
    try:
        acq = vehicle.acquisition  # OneToOne reverse accessor
    except VehicleAcquisition.DoesNotExist:
        return ZERO
    return (
        acq.purchase_price
        + acq.buyer_fees
        + acq.arbitration_fees
        + acq.transportation_cost
        + acq.title_acquisition_cost
    )


def compute_totals(
    vehicle: Vehicle, *, dealership: Dealership
) -> LedgerTotals:
    """Return the vehicle's per-category + aggregate ledger rollup.

    Deterministic. Same vehicle + same DB state → same
    :class:`LedgerTotals`. Every field is a :class:`Decimal`.

    Runs four category-scoped queries + one acquisition lookup —
    O(1) DB round trips regardless of cost row count.

    Refuses cross-tenant reads at entry
    (:class:`CrossTenantLedgerError`) — the same fail-closed shape
    as the write functions above. A caller that resolves
    ``vehicle`` from a global query and then passes the wrong
    ``dealership`` cannot leak per-tenant totals through this
    function.

    Zero-cost vehicles get ``ZERO`` for every field, never
    ``None``. Zero-acquisition vehicles get ``ZERO`` for
    ``acquisition_total``.
    """
    _assert_same_tenant(vehicle, dealership)

    acquisition_total = _acquisition_total(vehicle)

    flooring_total = _sum_category(
        vehicle, FLOORING_CATEGORIES, is_estimate=False
    )
    recon_total = _sum_category(
        vehicle, RECON_CATEGORIES, is_estimate=False
    )
    administrative_total = _sum_category(
        vehicle, ADMIN_CATEGORIES, is_estimate=False
    )
    photography_total = _sum_category(
        vehicle, PHOTOGRAPHY_CATEGORIES, is_estimate=False
    )
    actual_cost_total = (
        flooring_total
        + recon_total
        + administrative_total
        + photography_total
    )

    # Estimates live across every category — a single query over
    # ALL categories with is_estimate=True is the right shape.
    estimated_cost_total_raw = (
        VehicleCost.objects.filter(vehicle=vehicle, is_estimate=True)
        .aggregate(total=Sum("amount"))
        .get("total")
    )
    estimated_cost_total = (
        estimated_cost_total_raw
        if estimated_cost_total_raw is not None
        else ZERO
    )

    total_investment = acquisition_total + actual_cost_total
    projected_total_investment = total_investment + estimated_cost_total

    return LedgerTotals(
        acquisition_total=acquisition_total,
        flooring_total=flooring_total,
        recon_total=recon_total,
        administrative_total=administrative_total,
        photography_total=photography_total,
        actual_cost_total=actual_cost_total,
        estimated_cost_total=estimated_cost_total,
        total_investment=total_investment,
        projected_total_investment=projected_total_investment,
    )


# ---- Convenience: category classifier --------------------------------------


def category_group_of(category: str) -> Optional[str]:
    """Return the grouping name (``"flooring"``, ``"recon"``,
    ``"administrative"``, ``"photography"``) for a category, or
    ``None`` for unknown categories.

    Convenience for callers (future serializer, future UI) that
    want to render a per-row group label without repeating the
    partition logic. Kept as a service function rather than a
    ``VehicleCost`` method so the partition stays in the service
    layer next to :func:`compute_totals` — one authoritative place
    that defines how categories roll up.
    """
    if category in FLOORING_CATEGORIES:
        return "flooring"
    if category in RECON_CATEGORIES:
        return "recon"
    if category in ADMIN_CATEGORIES:
        return "administrative"
    if category in PHOTOGRAPHY_CATEGORIES:
        return "photography"
    return None


# Kept as a defensive re-export so callers do not have to reach into
# the private ``ValidationError`` import above just to catch model-
# clean errors from ``full_clean()``.
__all__ = [
    "CrossTenantLedgerError",
    "LedgerTotals",
    "ValidationError",
    "ZERO",
    "add_cost",
    "category_group_of",
    "compute_totals",
    "record_acquisition",
]

"""Milestone 7 · Increment 2 (SESSION_089) — floor-plan accrual verb.

The M2 ``accrue_floor_plan_interest`` management command's orchestration
body, extracted verbatim per M4-M6 lesson 4 (service ownership). The
verb is the one authoritative write path for scheduled floor-plan
interest accrual — the management command and the M7.2 Celery task both
call this function; neither reimplements the orchestration.

**Preserved contracts (locked by tests):**

- Duplicate detection runs FIRST — before math, before date resolution.
  Same-day re-runs post ZERO new rows.
- Last-accrual-date resolution: most recent accrual row → acquisition
  purchase date → skip (with counter increment).
- Transaction strategy: whole-run atomicity in live mode; dry-run skips
  the atomic block because no writes happen.
- ``daily_floor_plan_interest`` from :mod:`services.payment_engine` is
  the source of arithmetic truth — this module never re-derives math.
- ``add_cost`` from :mod:`services.vehicle_ledger` is the one write
  path — this module never bypasses it.
- Zero-dollar amounts are skipped (no ledger value in a $0 row that
  would still anchor duplicate detection).

**What this module does NOT own:**

- CLI argument parsing / stdout formatting — that stays in the
  management command as a thin CLI adapter.
- Celery task decoration + tenant fan-out — that lives in
  ``services.floor_plan.tasks``.
- Broker / Beat schedule wiring — ``dealer_kit/settings.py``.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.2 +
§7 M7.2. Migration note: the M2 command body (SESSION_050) moved here
at SESSION_089 with zero business-logic changes — only the argparse /
stdout shell was left behind.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Optional

from django.db import transaction

from ...models import (
    CATEGORY_FLOOR_PLAN_INTEREST,
    Dealership,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from ..dealer_config import get_floor_plan_apr
from ..payment_engine import daily_floor_plan_interest
from ..vehicle_ledger import add_cost


# ---------------------------------------------------------------------------
# Operational-event abstractions (moved from
# ``dealer_ai/management/commands/accrue_floor_plan_interest.py`` at
# SESSION_089 — see module docstring for the extraction rationale).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccrualPlan:
    """One planned accrual — what would (or will) be posted for one
    vehicle in this run.

    Structured as a first-class object so future work that persists
    accrual events to a dedicated ``AccrualEvent`` model does not need
    to change the verb's user-facing surface. Today: transient, lives
    for the verb's lifetime. Tomorrow: could be the shape of a
    persisted row.

    Frozen because the plan is immutable once produced by the planning
    pass — no downstream code should mutate an already-computed plan.
    """

    vehicle: Vehicle
    principal: Decimal
    apr: Decimal
    days_elapsed: int
    amount: Decimal


@dataclass
class AccrualSummary:
    """Concise execution summary. Rendered by the CLI adapter as the
    command's final stdout line; consumed by the Celery task shell as
    a structured audit-log payload."""

    dealership_slug: str
    as_of: dt.date
    dry_run: bool
    vehicles_evaluated: int = 0
    vehicles_accrued: int = 0
    skipped_no_acquisition: int = 0
    skipped_no_elapsed_days: int = 0
    skipped_duplicate: int = 0
    total_accrued: Decimal = field(default_factory=lambda: Decimal("0.00"))

    @property
    def vehicles_skipped(self) -> int:
        return (
            self.skipped_no_acquisition
            + self.skipped_no_elapsed_days
            + self.skipped_duplicate
        )

    def format(self) -> str:
        dry_marker = " [DRY RUN — nothing written]" if self.dry_run else ""
        return (
            f"Floor-plan accrual for dealership '{self.dealership_slug}' "
            f"(as-of {self.as_of.isoformat()}){dry_marker}\n"
            f"  Evaluated:  {self.vehicles_evaluated}\n"
            f"  Accrued:    {self.vehicles_accrued} "
            f"(${self.total_accrued} total)\n"
            f"  Skipped:    {self.vehicles_skipped} "
            f"(no acquisition: {self.skipped_no_acquisition}, "
            f"no elapsed days: {self.skipped_no_elapsed_days}, "
            f"duplicate: {self.skipped_duplicate})"
        )


# ---------------------------------------------------------------------------
# Public verb
# ---------------------------------------------------------------------------


def accrue_daily_interest(
    dealership: Dealership,
    *,
    as_of: Optional[dt.date] = None,
    dry_run: bool = False,
) -> AccrualSummary:
    """Accrue floor-plan interest for one dealership as of a given date.

    Posts one :class:`VehicleCost` row per eligible vehicle via the
    ledger service :func:`services.vehicle_ledger.add_cost`. Idempotent
    — re-running with the same ``as_of`` posts zero new rows.

    Parameters
    ----------
    dealership : Dealership
        The tenant whose vehicles are accrued. Required — this verb is
        deliberately single-tenant. The Celery task shell in
        :mod:`services.floor_plan.tasks` handles the multi-tenant
        fan-out.
    as_of : dt.date, optional
        Accrual date. Defaults to today (in the project's configured
        timezone). Accrues from the last accrual date (or acquisition
        date if none) up to this date.
    dry_run : bool, optional
        If True, plan the accrual without writing any rows. The
        returned :class:`AccrualSummary` reflects what would be posted.

    Returns
    -------
    AccrualSummary
        Execution summary. ``vehicles_evaluated`` /
        ``vehicles_accrued`` / ``vehicles_skipped`` counters and
        ``total_accrued`` are all populated.

    Notes
    -----
    Transaction strategy: whole-run atomicity in live mode. Any
    exception raised inside — from ``add_cost`` or from any planning
    code that touches the DB — rolls back every accrual posted in this
    run. Dry-run mode skips the atomic block because no writes happen.
    """
    if as_of is None:
        # Deferred import so this module's import graph stays free of
        # ``django.utils.timezone`` — the timezone lookup is only
        # needed when the caller doesn't supply an explicit date.
        from django.utils import timezone

        as_of = timezone.now().date()

    apr = get_floor_plan_apr(dealership)
    summary = AccrualSummary(
        dealership_slug=dealership.slug,
        as_of=as_of,
        dry_run=dry_run,
    )

    # Fetch vehicles + prefetch acquisition to keep per-vehicle lookups
    # cheap (avoids N+1 on ``vehicle.acquisition``).
    vehicles = (
        Vehicle.objects.filter(dealership=dealership)
        .select_related("acquisition")
        .order_by("stock_number")
    )

    # Plan-and-execute. In dry-run mode we skip the atomic block
    # entirely (no writes happen). In live mode we wrap the whole run
    # in one transaction — partial state is worse than none for a
    # batch operation the operator will re-run.
    if dry_run:
        _process(vehicles, dealership, apr, as_of, summary)
    else:
        with transaction.atomic():
            _process(vehicles, dealership, apr, as_of, summary)

    return summary


# ---------------------------------------------------------------------------
# Internal orchestration (unchanged shape from the M2 command; the
# ``self.`` calls became module-level helpers).
# ---------------------------------------------------------------------------


def _process(
    vehicles: Iterable[Vehicle],
    dealership: Dealership,
    apr: Decimal,
    as_of: dt.date,
    summary: AccrualSummary,
) -> None:
    """Iterate every vehicle, plan each accrual, execute unless
    ``summary.dry_run``."""
    for vehicle in vehicles:
        summary.vehicles_evaluated += 1
        plan = _plan_accrual(vehicle, dealership, apr, as_of, summary)
        if plan is None:
            continue
        summary.vehicles_accrued += 1
        summary.total_accrued += plan.amount
        if not summary.dry_run:
            _execute(plan, dealership, as_of)


def _plan_accrual(
    vehicle: Vehicle,
    dealership: Dealership,
    apr: Decimal,
    as_of: dt.date,
    summary: AccrualSummary,
) -> Optional[AccrualPlan]:
    """Compute what would happen for one vehicle. No writes."""

    # Duplicate detection runs FIRST — before we resolve the last
    # accrual date, before we call the engine, before anything else.
    # This is the explicit operational-idempotency guarantee the
    # SESSION_050 brief locks in. Same-day re-runs post ZERO new rows.
    if _accrual_exists_for(vehicle, dealership, as_of):
        summary.skipped_duplicate += 1
        return None

    last_date = _resolve_last_accrual_date(vehicle, dealership, summary)
    if last_date is None:
        # ``_resolve_last_accrual_date`` incremented the
        # ``skipped_no_acquisition`` counter already.
        return None

    days_elapsed = (as_of - last_date).days
    if days_elapsed <= 0:
        summary.skipped_no_elapsed_days += 1
        return None

    # Principal = acquisition.purchase_price for v1. Curtailment
    # tracking (which would adjust the principal downward as
    # curtailment payments post) is deferred per
    # ``MILESTONE_2_PLANNING.md`` §5.
    acquisition = vehicle.acquisition
    principal = acquisition.purchase_price

    amount = daily_floor_plan_interest(principal, apr, days_elapsed)

    # A zero-dollar accrual is theoretically possible (apr=0 or
    # very-short-period rounding to zero). Skip it — no ledger value
    # in a $0 row that also creates a duplicate-detection anchor for
    # future runs.
    if amount == Decimal("0.00"):
        summary.skipped_no_elapsed_days += 1
        return None

    return AccrualPlan(
        vehicle=vehicle,
        principal=principal,
        apr=apr,
        days_elapsed=days_elapsed,
        amount=amount,
    )


def _resolve_last_accrual_date(
    vehicle: Vehicle,
    dealership: Dealership,
    summary: AccrualSummary,
) -> Optional[dt.date]:
    """Contract locked by
    ``test_accrue_floor_plan_interest_command::LastAccrualResolution``:

    1. Most recent floor-plan accrual row's ``incurred_at.date()``.
    2. Vehicle acquisition's ``purchase_date``.
    3. ``None`` — vehicle skipped, counted in ``skipped_no_acquisition``.
    """
    # Priority 1: most recent floor-plan accrual row.
    last_accrual = (
        VehicleCost.objects.filter(
            vehicle=vehicle,
            dealership=dealership,
            category=CATEGORY_FLOOR_PLAN_INTEREST,
            reference__startswith="ACCRUAL:",
        )
        .order_by("-incurred_at")
        .values_list("incurred_at", flat=True)
        .first()
    )
    if last_accrual is not None:
        return last_accrual.date()

    # Priority 2: acquisition purchase_date. Guard against
    # ``vehicle.acquisition`` raising ``DoesNotExist`` on vehicles
    # without an acquisition row.
    try:
        return vehicle.acquisition.purchase_date
    except VehicleAcquisition.DoesNotExist:
        # Priority 3: no data → skip. No principal known without an
        # acquisition; the verb never guesses.
        summary.skipped_no_acquisition += 1
        return None


def _accrual_exists_for(
    vehicle: Vehicle, dealership: Dealership, as_of: dt.date
) -> bool:
    """Explicit duplicate detection. The reference tag is the canonical
    marker for "this vehicle accrued for this as-of date" — one row per
    (vehicle, as_of) is the invariant."""
    return VehicleCost.objects.filter(
        vehicle=vehicle,
        dealership=dealership,
        category=CATEGORY_FLOOR_PLAN_INTEREST,
        reference=f"ACCRUAL:{as_of.isoformat()}",
    ).exists()


def _execute(plan: AccrualPlan, dealership: Dealership, as_of: dt.date) -> None:
    """Post the planned accrual via :func:`services.vehicle_ledger.add_cost`.

    ``incurred_at`` is set to noon on ``as_of`` in the project's
    configured timezone so subsequent ``.date()`` lookups return the
    intended calendar date without straddling midnight in any tz.
    Reference tag ``ACCRUAL:<iso-date>`` is the marker the duplicate-
    detection query looks up.
    """
    # Deferred import — same rationale as ``accrue_daily_interest``
    # above (keep the module-import graph minimal until the timezone
    # helper is actually needed).
    from django.utils import timezone

    as_of_datetime = timezone.make_aware(
        dt.datetime.combine(as_of, dt.time(12, 0))
    )
    notes = (
        f"Auto-accrual: principal ${plan.principal} × apr "
        f"{plan.apr}% × {plan.days_elapsed} days / 365 = "
        f"${plan.amount}"
    )
    add_cost(
        plan.vehicle,
        dealership=dealership,
        category=CATEGORY_FLOOR_PLAN_INTEREST,
        amount=plan.amount,
        incurred_at=as_of_datetime,
        reference=f"ACCRUAL:{as_of.isoformat()}",
        notes=notes,
        is_estimate=False,
    )

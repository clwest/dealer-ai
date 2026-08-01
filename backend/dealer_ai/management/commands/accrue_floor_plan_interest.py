"""python manage.py accrue_floor_plan_interest --dealership=<slug>
[--as-of=YYYY-MM-DD] [--dry-run]

Milestone 2 · Increment 4b — the operational workflow that records
floor-plan interest into the vehicle ledger.

Responsibilities (kept intentionally separate):

- **Calculation** — :func:`services.payment_engine.daily_floor_plan_interest`.
  Pure math. This command does NOT contain financial logic.
- **Persistence** — :func:`services.vehicle_ledger.add_cost`.
  The one write path. This command does NOT bypass it.
- **Orchestration** — this command. Iterates the dealership's
  vehicles, resolves per-vehicle state (last accrual date,
  duplicate detection), plans a set of :class:`AccrualPlan`
  objects, then either executes them (live run) or reports what
  would happen (``--dry-run``).

Operational-event framing: the :class:`AccrualPlan` dataclass is
today a transient Python object that lives only for the command's
lifetime. Tomorrow it could be persisted to a dedicated
``AccrualEvent`` model without changing the command's user-facing
surface — the ``handle`` flow already separates PLAN (pure
computation, no writes) from EXECUTE (post via ``add_cost``).

Idempotency contract:

- Explicit duplicate detection runs BEFORE calculation. For each
  vehicle, the command queries for an existing
  :class:`VehicleCost` row with:
  ``category = CATEGORY_FLOOR_PLAN_INTEREST`` AND
  ``reference = f"ACCRUAL:{as_of.isoformat()}"``. If one exists,
  the vehicle is skipped and counted in ``skipped_duplicate``.
- The mathematical engine's ``days_elapsed <= 0`` short-circuit
  is a secondary defense (belt + suspenders) — it prevents a
  vehicle whose "last accrual date" resolves to today from
  producing a zero-dollar row that would still count as an
  accrual event.
- Same-day re-runs post ZERO new rows, always. Locked by
  ``test_accrue_floor_plan_interest_command::IdempotencySameDayReRun``.

Last-accrual-date resolution (documented, tested):

1. Most recent floor-plan accrual row for this
   ``(vehicle, dealership)`` — the row's ``incurred_at.date()``.
2. ``VehicleAcquisition.purchase_date`` — used the first time
   the command runs on a fresh vehicle.
3. If neither exists (no acquisition record), the vehicle is
   skipped and counted in ``skipped_no_acquisition``. No principal
   is known without an acquisition — the command never guesses.

Transaction strategy: **whole-run atomicity, live mode only.** The
live execute phase wraps the entire per-vehicle loop in one
``transaction.atomic()`` block. Any exception raised inside — from
``add_cost`` or from any planning code that touches the DB — rolls
back every accrual posted in this run. The command exits non-zero;
the operator sees the exception. Rationale: partial state is worse
than no state for a batch operation the operator will re-run; a
half-committed accrual would corrupt the duplicate-detection
invariant on the next run. Dry-run mode skips the atomic block
because no writes happen.

Scope discipline: this command does NOT implement curtailments,
lender payoff tracking, scheduled execution, Celery, or
tenant-wide automation. Deferred per
``MILESTONE_2_PLANNING.md`` §5 and the SESSION_050 brief.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ...models import (
    CATEGORY_FLOOR_PLAN_INTEREST,
    Dealership,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from ...services.dealer_config import get_floor_plan_apr
from ...services.payment_engine import daily_floor_plan_interest
from ...services.vehicle_ledger import add_cost


# ---- Operational-event abstractions ---------------------------------------


@dataclass(frozen=True)
class AccrualPlan:
    """One planned accrual — what would (or will) be posted for one
    vehicle in this run.

    Structured as a first-class object so future work that
    persists accrual events to a dedicated ``AccrualEvent`` model
    does not need to change the command's user-facing surface.
    Today: transient, lives for the command's lifetime.
    Tomorrow: could be the shape of a persisted row.

    Frozen because the plan is immutable once produced by the
    planning pass — no downstream code should mutate an already-
    computed plan.
    """

    vehicle: Vehicle
    principal: Decimal
    apr: Decimal
    days_elapsed: int
    amount: Decimal


@dataclass
class AccrualSummary:
    """Concise execution summary. Renders as the command's final
    stdout line."""

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


class Command(BaseCommand):
    help = (
        "Accrue floor-plan interest for one dealership as of a given "
        "date. Posts one VehicleCost row per eligible vehicle via the "
        "ledger service. Idempotent — re-running with the same "
        "--as-of posts zero new rows."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dealership",
            required=True,
            help=(
                "Slug of the Dealership to process. Required — this "
                "command is deliberately single-tenant. Bulk-run "
                "helpers are deferred; run the command once per "
                "dealership from a shell loop if needed."
            ),
        )
        parser.add_argument(
            "--as-of",
            default=None,
            help=(
                "Accrual date (YYYY-MM-DD). Defaults to today (in "
                "``settings.TIME_ZONE``). Accrues from the last "
                "accrual date (or acquisition date if none) up to "
                "this date."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Plan the accrual without writing any rows. Prints "
                "the same summary the live run would."
            ),
        )

    def handle(self, *args, **options):
        dealership = self._resolve_dealership(options["dealership"])
        as_of = self._resolve_as_of(options["as_of"])
        dry_run: bool = options["dry_run"]

        apr = get_floor_plan_apr(dealership)
        summary = AccrualSummary(
            dealership_slug=dealership.slug,
            as_of=as_of,
            dry_run=dry_run,
        )

        # Fetch vehicles + prefetch acquisition to keep per-vehicle
        # lookups cheap (avoids N+1 on ``vehicle.acquisition``).
        vehicles = (
            Vehicle.objects.filter(dealership=dealership)
            .select_related("acquisition")
            .order_by("stock_number")
        )

        # Plan-and-execute. In dry-run mode we skip the atomic block
        # entirely (no writes happen). In live mode we wrap the whole
        # run in one transaction — partial state is worse than none
        # for a batch operation the operator will re-run.
        if dry_run:
            self._process(vehicles, dealership, apr, as_of, summary)
        else:
            with transaction.atomic():
                self._process(vehicles, dealership, apr, as_of, summary)

        self.stdout.write(summary.format())

    # ---- Resolve args ------------------------------------------------------

    @staticmethod
    def _resolve_dealership(slug: str) -> Dealership:
        try:
            return Dealership.objects.get(slug=slug)
        except Dealership.DoesNotExist as exc:
            raise CommandError(
                f"Unknown dealership slug: '{slug}'. Confirm the slug "
                f"in Django admin or via "
                f"``Dealership.objects.values_list('slug', flat=True)``."
            ) from exc

    @staticmethod
    def _resolve_as_of(raw: Optional[str]) -> dt.date:
        if raw is None:
            return timezone.now().date()
        try:
            return dt.date.fromisoformat(raw)
        except ValueError as exc:
            raise CommandError(
                f"--as-of must be YYYY-MM-DD, got: '{raw}'"
            ) from exc

    # ---- Orchestration -----------------------------------------------------

    def _process(
        self,
        vehicles,
        dealership: Dealership,
        apr: Decimal,
        as_of: dt.date,
        summary: AccrualSummary,
    ) -> None:
        """Iterate every vehicle, plan each accrual, execute unless
        ``--dry-run``."""
        for vehicle in vehicles:
            summary.vehicles_evaluated += 1
            plan = self._plan_accrual(
                vehicle, dealership, apr, as_of, summary
            )
            if plan is None:
                continue
            summary.vehicles_accrued += 1
            summary.total_accrued += plan.amount
            if not summary.dry_run:
                self._execute(plan, dealership, as_of)

    def _plan_accrual(
        self,
        vehicle: Vehicle,
        dealership: Dealership,
        apr: Decimal,
        as_of: dt.date,
        summary: AccrualSummary,
    ) -> Optional[AccrualPlan]:
        """Compute what would happen for one vehicle. No writes."""

        # Duplicate detection runs FIRST — before we resolve the last
        # accrual date, before we call the engine, before anything
        # else. This is the explicit operational-idempotency guarantee
        # the SESSION_050 brief locks in. Same-day re-runs post ZERO
        # new rows.
        if self._accrual_exists_for(vehicle, dealership, as_of):
            summary.skipped_duplicate += 1
            return None

        last_date = self._resolve_last_accrual_date(
            vehicle, dealership, summary
        )
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
        # ``MILESTONE_2_PLANNING.md`` §5. The engine accepts an
        # arbitrary principal, so future evolution requires only
        # changing this one line to compute the current balance
        # instead.
        acquisition = vehicle.acquisition
        principal = acquisition.purchase_price

        amount = daily_floor_plan_interest(principal, apr, days_elapsed)

        # A zero-dollar accrual is theoretically possible (apr=0 or
        # very-short-period rounding to zero). Skip it — no ledger
        # value in a $0 row that also creates a duplicate-detection
        # anchor for future runs.
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
        self,
        vehicle: Vehicle,
        dealership: Dealership,
        summary: AccrualSummary,
    ) -> Optional[dt.date]:
        """Contract locked by
        ``test_accrue_floor_plan_interest_command::LastAccrualResolution``:

        1. Most recent floor-plan accrual row's ``incurred_at.date()``.
        2. Vehicle acquisition's ``purchase_date``.
        3. ``None`` — vehicle skipped, counted in
           ``skipped_no_acquisition``.
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
            # Priority 3: no data → skip. No principal known without
            # an acquisition; the command never guesses.
            summary.skipped_no_acquisition += 1
            return None

    @staticmethod
    def _accrual_exists_for(
        vehicle: Vehicle, dealership: Dealership, as_of: dt.date
    ) -> bool:
        """Explicit duplicate detection. The reference tag is the
        canonical marker for "this vehicle accrued for this
        as-of date" — one row per (vehicle, as_of) is the
        invariant."""
        return VehicleCost.objects.filter(
            vehicle=vehicle,
            dealership=dealership,
            category=CATEGORY_FLOOR_PLAN_INTEREST,
            reference=f"ACCRUAL:{as_of.isoformat()}",
        ).exists()

    # ---- Execute a plan ----------------------------------------------------

    @staticmethod
    def _execute(plan: AccrualPlan, dealership: Dealership, as_of: dt.date) -> None:
        """Post the planned accrual via
        :func:`services.vehicle_ledger.add_cost`.

        ``incurred_at`` is set to noon on ``as_of`` in the project's
        configured timezone so subsequent ``.date()`` lookups return
        the intended calendar date without straddling midnight in
        any tz. Reference tag ``ACCRUAL:<iso-date>`` is the marker
        the duplicate-detection query looks up.
        """
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

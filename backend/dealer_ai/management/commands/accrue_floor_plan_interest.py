"""python manage.py accrue_floor_plan_interest --dealership=<slug>
[--as-of=YYYY-MM-DD] [--dry-run]

Milestone 2 · Increment 4b — the operational workflow that records
floor-plan interest into the vehicle ledger.

**SESSION_089 extraction** (M7.2): the command's orchestration body
moved to ``dealer_ai.services.floor_plan.accrue_daily_interest``. This
command is now a thin CLI adapter that parses arguments, resolves the
tenant, invokes the service verb, and writes the summary to stdout.
The M2 CLI surface (``--dealership`` / ``--as-of`` / ``--dry-run``) is
preserved verbatim so existing operator workflows and every existing
test continues to pass.

Responsibilities (kept intentionally separate):

- **Calculation** — :func:`services.payment_engine.daily_floor_plan_interest`.
  Pure math. This command does NOT contain financial logic.
- **Persistence** — :func:`services.vehicle_ledger.add_cost`.
  The one write path. This command does NOT bypass it.
- **Orchestration** — :func:`services.floor_plan.accrue_daily_interest`.
  The one authoritative scheduled-accrual verb. This command does NOT
  reimplement the orchestration — it hands off to the service.
- **CLI adaptation** — this file. Argument parsing, tenant resolution,
  stdout formatting. Everything else is a service call.

Idempotency contract (locked by the service verb; documented here for
operator reference):

- Explicit duplicate detection runs BEFORE calculation. For each
  vehicle, the verb queries for an existing :class:`VehicleCost` row
  with: ``category = CATEGORY_FLOOR_PLAN_INTEREST`` AND
  ``reference = f"ACCRUAL:{as_of.isoformat()}"``. If one exists, the
  vehicle is skipped and counted in ``skipped_duplicate``.
- Same-day re-runs post ZERO new rows, always. Locked by
  ``test_accrue_floor_plan_interest_command::IdempotencySameDayReRun``.

Last-accrual-date resolution (documented, tested):

1. Most recent floor-plan accrual row for this
   ``(vehicle, dealership)`` — the row's ``incurred_at.date()``.
2. ``VehicleAcquisition.purchase_date`` — used the first time the
   verb runs on a fresh vehicle.
3. If neither exists (no acquisition record), the vehicle is skipped
   and counted in ``skipped_no_acquisition``. No principal is known
   without an acquisition — the verb never guesses.

Transaction strategy: **whole-run atomicity, live mode only.** The live
execute phase (inside the service verb) wraps the entire per-vehicle
loop in one ``transaction.atomic()`` block. Any exception raised
inside rolls back every accrual posted in this run. The command exits
non-zero; the operator sees the exception. Dry-run mode skips the
atomic block because no writes happen.

Scope discipline: this command does NOT implement curtailments,
lender payoff tracking, or per-tenant broker scheduling. Deferred per
``MILESTONE_2_PLANNING.md`` §5 and the SESSION_050 brief; M7.2 added
the Celery task shell in ``services.floor_plan.tasks`` for scheduled
execution alongside the CLI.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...models import Dealership
from ...services.floor_plan import accrue_daily_interest


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
                "dealership from a shell loop if needed, or use the "
                "M7.2 Celery task's ``accrue_all_tenants`` orchestrator "
                "for scheduled fan-out."
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

        summary = accrue_daily_interest(
            dealership, as_of=as_of, dry_run=dry_run
        )
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

"""Milestone 2 · Increment 4b — accrual command workflow tests.

Locks the workflow's operational contract:

- Dealership required + validated.
- ``--as-of`` accepts YYYY-MM-DD; malformed → CommandError.
- ``--dry-run`` posts zero rows.
- Happy path: one row per eligible vehicle, amounts match the
  M2.4a engine (never re-derive math in tests).
- Explicit duplicate detection: same-day re-run posts zero rows;
  the ``skipped_duplicate`` counter increments.
- Next-day run posts only the delta.
- Last-accrual-date resolution order (accrual row → purchase
  date → skip).
- Cross-tenant safety: only the target tenant's ledger receives
  rows.
- Summary output format.
- Transaction safety: any exception mid-run rolls back the entire
  transaction — no partial state.

Every posted-amount assertion uses ``daily_floor_plan_interest``
from ``services.payment_engine`` as the source of truth so the
tests never re-derive the math the M2.4a engine already proves.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_FLOOR_PLAN_INTEREST,
    SOURCE_AUCTION,
    Dealership,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.payment_engine import daily_floor_plan_interest
from dealer_ai.services.vehicle_ledger import record_acquisition


COMMAND = "accrue_floor_plan_interest"


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _seed_acquisition(
    vehicle: Vehicle,
    dealership: Dealership,
    purchase_date: dt.date,
    price: Decimal = Decimal("18000.00"),
) -> None:
    record_acquisition(
        vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=price,
        purchase_date=purchase_date,
    )


class ArgumentValidation(TestCase):
    """--dealership required; unknown slug → CommandError; --as-of
    validation."""

    def test_dealership_argument_is_required(self):
        # Django's argparse raises CommandError for a missing
        # required argument.
        with self.assertRaises(CommandError):
            call_command(COMMAND, stdout=StringIO(), stderr=StringIO())

    def test_unknown_dealership_slug_raises_command_error(self):
        with self.assertRaises(CommandError) as ctx:
            call_command(
                COMMAND,
                "--dealership=does-not-exist",
                stdout=StringIO(),
                stderr=StringIO(),
            )
        # Error message names the offending slug so operators can
        # correct their input without digging into a stack trace.
        self.assertIn("does-not-exist", str(ctx.exception))

    def test_malformed_as_of_raises_command_error(self):
        with self.assertRaises(CommandError) as ctx:
            call_command(
                COMMAND,
                "--dealership=default",
                "--as-of=not-a-date",
                stdout=StringIO(),
                stderr=StringIO(),
            )
        self.assertIn("YYYY-MM-DD", str(ctx.exception))


class DryRunPurity(TestCase):
    """--dry-run posts zero rows even when accrual would otherwise
    happen. Summary still reflects what WOULD have been accrued."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M24B-DRY", self.default)
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        _seed_acquisition(self.vehicle, self.default, thirty_days_ago)

    def test_dry_run_writes_zero_ledger_rows(self):
        pre_count = VehicleCost.objects.count()
        call_command(
            COMMAND,
            "--dealership=default",
            "--dry-run",
            stdout=StringIO(),
            stderr=StringIO(),
        )
        self.assertEqual(VehicleCost.objects.count(), pre_count)

    def test_dry_run_summary_reports_planned_accrual(self):
        out = StringIO()
        call_command(
            COMMAND,
            "--dealership=default",
            "--dry-run",
            stdout=out,
            stderr=StringIO(),
        )
        output = out.getvalue()
        self.assertIn("DRY RUN", output)
        # Vehicle would be accrued (has acquisition + 30 days
        # elapsed), so the summary shows Accrued: 1.
        self.assertIn("Accrued:    1", output)


class HappyPath(TestCase):
    """Fresh run posts one accrual row per eligible vehicle. Posted
    amounts match the M2.4a engine byte-for-byte."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        # Three eligible vehicles at different prices to prove the
        # per-vehicle plan reads the right principal.
        self.vehicles = []
        for stock, price in [
            ("M24B-HP-1", Decimal("15000.00")),
            ("M24B-HP-2", Decimal("18000.00")),
            ("M24B-HP-3", Decimal("22000.00")),
        ]:
            vehicle = _make_vehicle(stock, self.default)
            _seed_acquisition(
                vehicle, self.default, self.thirty_days_ago, price=price
            )
            self.vehicles.append(vehicle)

    def test_fresh_run_posts_one_row_per_eligible_vehicle(self):
        call_command(
            COMMAND, "--dealership=default", stdout=StringIO(), stderr=StringIO()
        )
        posted = VehicleCost.objects.filter(
            category=CATEGORY_FLOOR_PLAN_INTEREST
        )
        self.assertEqual(posted.count(), 3)

    def test_posted_amounts_match_engine_output(self):
        # Compute what the engine says the amounts should be; the
        # test never re-derives the math.
        from dealer_ai.services.dealer_config import get_floor_plan_apr

        apr = get_floor_plan_apr(self.default)
        as_of = timezone.now().date()
        expected_by_stock = {
            "M24B-HP-1": daily_floor_plan_interest(
                Decimal("15000.00"), apr, 30
            ),
            "M24B-HP-2": daily_floor_plan_interest(
                Decimal("18000.00"), apr, 30
            ),
            "M24B-HP-3": daily_floor_plan_interest(
                Decimal("22000.00"), apr, 30
            ),
        }

        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={as_of.isoformat()}",
            stdout=StringIO(),
            stderr=StringIO(),
        )

        posted = {
            cost.vehicle.stock_number: cost.amount
            for cost in VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            )
        }
        self.assertEqual(posted, expected_by_stock)

    def test_posted_rows_carry_the_reference_tag(self):
        as_of = timezone.now().date()
        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={as_of.isoformat()}",
            stdout=StringIO(),
            stderr=StringIO(),
        )
        expected_ref = f"ACCRUAL:{as_of.isoformat()}"
        posted_refs = set(
            VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            ).values_list("reference", flat=True)
        )
        self.assertEqual(posted_refs, {expected_ref})

    def test_posted_rows_are_not_estimates(self):
        # is_estimate=False so the M2.2 total_investment picks them
        # up (estimated rows are excluded from actual_cost_total).
        call_command(
            COMMAND,
            "--dealership=default",
            stdout=StringIO(),
            stderr=StringIO(),
        )
        for cost in VehicleCost.objects.filter(
            category=CATEGORY_FLOOR_PLAN_INTEREST
        ):
            self.assertFalse(cost.is_estimate)


class IdempotencySameDayReRun(TestCase):
    """The explicit duplicate detection: same-day re-run posts ZERO
    new rows. The ``skipped_duplicate`` counter increments for each
    vehicle that already has an accrual row for this ``as_of``.

    This is the operational-idempotency guarantee the SESSION_050
    brief called out — do NOT rely on the engine's
    ``days_elapsed <= 0`` short-circuit alone; the workflow owns
    idempotency explicitly."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M24B-IDEM", self.default)
        _seed_acquisition(
            self.vehicle,
            self.default,
            timezone.now().date() - dt.timedelta(days=30),
        )

    def test_second_same_day_run_posts_zero_new_rows(self):
        as_of = timezone.now().date()

        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={as_of.isoformat()}",
            stdout=StringIO(),
            stderr=StringIO(),
        )
        after_first = VehicleCost.objects.filter(
            category=CATEGORY_FLOOR_PLAN_INTEREST
        ).count()
        self.assertEqual(after_first, 1)

        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={as_of.isoformat()}",
            stdout=StringIO(),
            stderr=StringIO(),
        )
        after_second = VehicleCost.objects.filter(
            category=CATEGORY_FLOOR_PLAN_INTEREST
        ).count()
        self.assertEqual(after_second, 1, "same-day re-run must not add rows")

    def test_second_same_day_run_reports_duplicate_skip(self):
        as_of = timezone.now().date()

        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={as_of.isoformat()}",
            stdout=StringIO(),
            stderr=StringIO(),
        )

        out = StringIO()
        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={as_of.isoformat()}",
            stdout=out,
            stderr=StringIO(),
        )
        output = out.getvalue()
        self.assertIn("duplicate: 1", output)
        self.assertIn("Accrued:    0", output)


class IncrementalDelta(TestCase):
    """A later ``--as-of`` posts an accrual only for the *new* days
    since the last accrual row's date. Locks the resolver's
    "priority 1 = most recent accrual row" branch."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M24B-DELTA", self.default)
        # Purchased 40 days ago; accrue up through 30 days ago, then
        # again through today, and verify the second run's amount is
        # only for the 30-day delta (not 40 days from purchase).
        _seed_acquisition(
            self.vehicle,
            self.default,
            timezone.now().date() - dt.timedelta(days=40),
        )

    def test_second_run_accrues_only_the_delta_days(self):
        from dealer_ai.services.dealer_config import get_floor_plan_apr

        apr = get_floor_plan_apr(self.default)
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        today = timezone.now().date()
        delta_days = (today - thirty_days_ago).days

        # First run: accrual for 10 days (40 → 30 days ago).
        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={thirty_days_ago.isoformat()}",
            stdout=StringIO(),
            stderr=StringIO(),
        )
        # Second run: accrual for 30 days (30 days ago → today).
        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={today.isoformat()}",
            stdout=StringIO(),
            stderr=StringIO(),
        )

        second_run_row = VehicleCost.objects.get(
            vehicle=self.vehicle,
            category=CATEGORY_FLOOR_PLAN_INTEREST,
            reference=f"ACCRUAL:{today.isoformat()}",
        )
        expected = daily_floor_plan_interest(
            Decimal("18000.00"), apr, delta_days
        )
        self.assertEqual(second_run_row.amount, expected)


class LastAccrualResolution(TestCase):
    """The resolver's contract: (1) most recent accrual row, (2)
    acquisition purchase_date, (3) skip. Each branch locked here."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_vehicle_without_acquisition_is_skipped(self):
        _make_vehicle("M24B-NOACQ", self.default)

        out = StringIO()
        call_command(
            COMMAND,
            "--dealership=default",
            stdout=out,
            stderr=StringIO(),
        )
        output = out.getvalue()
        self.assertIn("no acquisition: 1", output)
        # No ledger row posted.
        self.assertEqual(
            VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            ).count(),
            0,
        )

    def test_first_run_uses_purchase_date_as_last_accrual(self):
        from dealer_ai.services.dealer_config import get_floor_plan_apr

        apr = get_floor_plan_apr(self.default)
        vehicle = _make_vehicle("M24B-FIRSTRUN", self.default)
        purchase_date = timezone.now().date() - dt.timedelta(days=15)
        _seed_acquisition(vehicle, self.default, purchase_date)

        today = timezone.now().date()
        call_command(
            COMMAND,
            "--dealership=default",
            f"--as-of={today.isoformat()}",
            stdout=StringIO(),
            stderr=StringIO(),
        )
        posted = VehicleCost.objects.get(
            vehicle=vehicle, category=CATEGORY_FLOOR_PLAN_INTEREST
        )
        # 15 days between purchase_date and today.
        expected = daily_floor_plan_interest(
            Decimal("18000.00"), apr, 15
        )
        self.assertEqual(posted.amount, expected)


class CrossTenantSafety(TestCase):
    """--dealership is the sole tenant scope. Rows post ONLY to the
    specified dealership; other tenants' vehicles are not touched."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-accrual"
        )
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)

        self.vehicle_a = _make_vehicle("M24B-XT-A", self.dealership_a)
        self.vehicle_b = _make_vehicle("M24B-XT-B", self.dealership_b)
        _seed_acquisition(self.vehicle_a, self.dealership_a, thirty_days_ago)
        _seed_acquisition(self.vehicle_b, self.dealership_b, thirty_days_ago)

    def test_running_for_a_does_not_touch_b(self):
        call_command(
            COMMAND,
            "--dealership=default",
            stdout=StringIO(),
            stderr=StringIO(),
        )
        # A gets a row.
        self.assertEqual(
            VehicleCost.objects.filter(
                vehicle=self.vehicle_a,
                category=CATEGORY_FLOOR_PLAN_INTEREST,
            ).count(),
            1,
        )
        # B does not.
        self.assertEqual(
            VehicleCost.objects.filter(
                vehicle=self.vehicle_b,
                category=CATEGORY_FLOOR_PLAN_INTEREST,
            ).count(),
            0,
        )

    def test_summary_reports_only_the_target_dealership(self):
        out = StringIO()
        call_command(
            COMMAND,
            "--dealership=default",
            stdout=out,
            stderr=StringIO(),
        )
        output = out.getvalue()
        self.assertIn("default", output)
        self.assertNotIn("rivertown-accrual", output)


class SummaryReporting(TestCase):
    """Summary format contract locked here — the command will
    eventually run under a scheduler and its output is what an
    operator (or a monitoring pipeline) reads."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_summary_lines_present_and_labelled(self):
        vehicle = _make_vehicle("M24B-SUMMARY", self.default)
        _seed_acquisition(
            vehicle,
            self.default,
            timezone.now().date() - dt.timedelta(days=30),
        )

        out = StringIO()
        call_command(
            COMMAND,
            "--dealership=default",
            stdout=out,
            stderr=StringIO(),
        )
        output = out.getvalue()
        self.assertIn("Floor-plan accrual for dealership 'default'", output)
        self.assertIn("Evaluated:", output)
        self.assertIn("Accrued:", output)
        self.assertIn("Skipped:", output)
        self.assertIn("no acquisition:", output)
        self.assertIn("no elapsed days:", output)
        self.assertIn("duplicate:", output)


class TransactionSafety(TestCase):
    """The live-run execute phase wraps every add_cost call in one
    ``transaction.atomic()``. If ANY call raises mid-run, every
    previously-posted row in this run is rolled back. Rationale:
    partial state is worse than none for a batch operation the
    operator will re-run."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        # Three vehicles — the mock will raise on the second, and the
        # first must be rolled back.
        for stock in ("M24B-TX-1", "M24B-TX-2", "M24B-TX-3"):
            vehicle = _make_vehicle(stock, self.default)
            _seed_acquisition(vehicle, self.default, thirty_days_ago)

    def test_mid_run_failure_rolls_back_all_prior_accruals(self):
        # Patch add_cost so the second call raises. First call
        # succeeds inside the atomic block; second raises → whole
        # transaction rolls back.
        #
        # SESSION_089 (M7.2): the orchestration body moved from the
        # management command to ``services.floor_plan.accrual`` —
        # the patch target follows.
        call_count = {"n": 0}
        real_add_cost_target = (
            "dealer_ai.services.floor_plan.accrual.add_cost"
        )

        def _fake_add_cost(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("simulated mid-run failure")
            # Fall through to the real add_cost for the successful
            # first call so a real row would be posted — proving the
            # rollback works.
            from dealer_ai.services.vehicle_ledger import (
                add_cost as real_add_cost,
            )

            return real_add_cost(*args, **kwargs)

        with patch(real_add_cost_target, side_effect=_fake_add_cost):
            with self.assertRaises(RuntimeError):
                call_command(
                    COMMAND,
                    "--dealership=default",
                    stdout=StringIO(),
                    stderr=StringIO(),
                )

        # After the failed run, ZERO rows exist — the first call's
        # posted row was rolled back by the outer atomic block.
        self.assertEqual(
            VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            ).count(),
            0,
            "atomic transaction should have rolled back the first "
            "successful accrual when the second call raised",
        )

    def test_dry_run_does_not_need_atomic(self):
        # Dry-run mode skips the atomic block entirely (nothing to
        # roll back). Prove by patching transaction.atomic to raise
        # if called; dry-run should NOT trigger it.
        #
        # SESSION_089 (M7.2): the atomic block moved from the
        # management command to ``services.floor_plan.accrual`` —
        # the patch target follows.
        real_atomic_target = (
            "dealer_ai.services.floor_plan.accrual.transaction.atomic"
        )
        with patch(real_atomic_target) as mock_atomic:
            call_command(
                COMMAND,
                "--dealership=default",
                "--dry-run",
                stdout=StringIO(),
                stderr=StringIO(),
            )
            # Command completed. Atomic must NOT have been called
            # (dry-run skips the block).
            mock_atomic.assert_not_called()

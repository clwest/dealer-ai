"""Milestone 2 · Increment 4a — pure floor-plan-interest math tests.

Every expected value hand-verified with a calculator. Zero DB, zero
Vehicle, zero Dealership, zero ledger writes — this file tests the
mathematical engine in isolation.

The engine's design contract:

- APR is expressed in percent units (``Decimal("8.5")`` = 8.5%
  annual), matching the existing ``DEFAULT_APR = 7.49`` convention
  in ``payment_engine.py``.
- Day-count convention is 365 (calendar year). A 30-day period
  always produces 30/365 of the annual interest — no calendar-aware
  behavior, no leap-year adjustment.
- Return is always :class:`Decimal` quantized to two decimal places
  with ``ROUND_HALF_UP``.

Financial rules (locked below):

- Zero inputs (apr / principal / days) return ``Decimal("0.00")``.
- Negative days return ``Decimal("0.00")`` — the accrual command
  can pass negative days on a stale ``--as-of`` without crashing.
- Negative principal / negative apr raise :class:`ValueError` —
  those are data-corruption signals, not benign edge cases.
- Deterministic across repeated calls with the same inputs.

Test class map:

- ``HandVerifiedFinancialMath`` — the load-bearing tests. Each
  independently verifiable with a calculator.
- ``ZeroAndEdgeInputs`` — zero-return behavior for degenerate inputs.
- ``InvalidInputs`` — negative principal / APR raise.
- ``DecimalPrecisionAndRounding`` — Decimal type + quantize +
  ``ROUND_HALF_UP`` behavior.
- ``LeapYearNeutrality`` — 30 days is 30 days regardless of calendar
  placement.
- ``PrincipalIsGeneric`` — the engine does not care what "principal"
  represents (documents the M2.4a scope-discipline decision).
- ``TypeCoercion`` — non-Decimal numeric inputs are coerced safely.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase

from dealer_ai.services.payment_engine import daily_floor_plan_interest


class HandVerifiedFinancialMath(SimpleTestCase):
    """Every expected value here should be independently verifiable
    with a calculator. Format for the reader:

        principal × (apr / 100) × days / 365 → raw
        raw quantized to 2 decimals (ROUND_HALF_UP) → expected
    """

    def test_one_day_18500_at_850_pct(self):
        # 18500 × 0.085 × 1 / 365
        # = 1572.5 / 365
        # = 4.30821917808...
        # Rounded HALF_UP to 2 decimals → 4.31
        self.assertEqual(
            daily_floor_plan_interest(
                Decimal("18500.00"), Decimal("8.5"), 1
            ),
            Decimal("4.31"),
        )

    def test_thirty_day_18500_at_850_pct(self):
        # 18500 × 0.085 × 30 / 365
        # = 47175 / 365
        # = 129.24657534...
        # Rounded HALF_UP → 129.25
        self.assertEqual(
            daily_floor_plan_interest(
                Decimal("18500.00"), Decimal("8.5"), 30
            ),
            Decimal("129.25"),
        )

    def test_ninety_day_curtailment_window_18500_at_850_pct(self):
        # 18500 × 0.085 × 90 / 365
        # = 141525 / 365
        # = 387.73972602...
        # Rounded HALF_UP → 387.74
        self.assertEqual(
            daily_floor_plan_interest(
                Decimal("18500.00"), Decimal("8.5"), 90
            ),
            Decimal("387.74"),
        )

    def test_round_number_10000_at_12pct_one_day(self):
        # 10000 × 0.12 × 1 / 365
        # = 1200 / 365
        # = 3.28767123...
        # Rounded HALF_UP → 3.29
        self.assertEqual(
            daily_floor_plan_interest(
                Decimal("10000.00"), Decimal("12.0"), 1
            ),
            Decimal("3.29"),
        )

    def test_full_year_365_days(self):
        # 10000 × 0.10 × 365 / 365 = exactly 1000.00. A full 365-day
        # accrual at 10% APR is exactly 10% of principal — locks the
        # day-count convention (365, not 360).
        self.assertEqual(
            daily_floor_plan_interest(
                Decimal("10000.00"), Decimal("10.0"), 365
            ),
            Decimal("1000.00"),
        )

    def test_small_apr_small_principal(self):
        # 500 × 0.05 × 7 / 365
        # = 175 / 365 = 0.47945205...
        # Rounded HALF_UP → 0.48
        self.assertEqual(
            daily_floor_plan_interest(
                Decimal("500.00"), Decimal("5.0"), 7
            ),
            Decimal("0.48"),
        )


class ZeroAndEdgeInputs(SimpleTestCase):
    """Degenerate inputs return canonical ``Decimal("0.00")`` — not
    raise, not silently drop precision, not return an int."""

    def test_apr_zero_returns_zero(self):
        result = daily_floor_plan_interest(
            Decimal("18500.00"), Decimal("0"), 30
        )
        self.assertEqual(result, Decimal("0.00"))

    def test_principal_zero_returns_zero(self):
        result = daily_floor_plan_interest(
            Decimal("0"), Decimal("8.5"), 30
        )
        self.assertEqual(result, Decimal("0.00"))

    def test_days_zero_returns_zero(self):
        # The idempotency escape hatch for the accrual command's
        # same-day re-run.
        result = daily_floor_plan_interest(
            Decimal("18500.00"), Decimal("8.5"), 0
        )
        self.assertEqual(result, Decimal("0.00"))

    def test_negative_days_returns_zero(self):
        # A stale --as-of that resolves earlier than the last
        # accrual date must not crash the accrual command; it should
        # be a documented no-op.
        result = daily_floor_plan_interest(
            Decimal("18500.00"), Decimal("8.5"), -5
        )
        self.assertEqual(result, Decimal("0.00"))

    def test_zero_returns_are_canonical_decimal_shape(self):
        # ``Decimal("0.00")`` — quantized to 2 places, not
        # ``Decimal("0")`` (which is 0 places). Downstream
        # ``VehicleCost.amount`` (DecimalField(10, 2)) expects the
        # 2-place shape.
        for principal, apr, days in [
            (Decimal("0"), Decimal("8.5"), 30),
            (Decimal("100"), Decimal("0"), 30),
            (Decimal("100"), Decimal("8.5"), 0),
            (Decimal("100"), Decimal("8.5"), -1),
        ]:
            result = daily_floor_plan_interest(principal, apr, days)
            self.assertEqual(result, Decimal("0.00"))
            # Two decimal places preserved on zeros too.
            self.assertEqual(result.as_tuple().exponent, -2)


class InvalidInputs(SimpleTestCase):
    """Negative principal / APR are data-corruption signals, not
    benign edge cases. Raise :class:`ValueError` loudly."""

    def test_negative_principal_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            daily_floor_plan_interest(
                Decimal("-100"), Decimal("8.5"), 30
            )
        # Error message should be actionable — name the offending
        # argument, not a stack trace.
        self.assertIn("principal", str(ctx.exception).lower())

    def test_negative_apr_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            daily_floor_plan_interest(
                Decimal("100"), Decimal("-2.5"), 30
            )
        self.assertIn("apr", str(ctx.exception).lower())

    def test_both_negative_raises_on_principal_first(self):
        # Principal check runs first — establishes deterministic
        # error attribution.
        with self.assertRaises(ValueError) as ctx:
            daily_floor_plan_interest(
                Decimal("-100"), Decimal("-2.5"), 30
            )
        self.assertIn("principal", str(ctx.exception).lower())


class DecimalPrecisionAndRounding(SimpleTestCase):
    """Result is always :class:`Decimal`, always 2 decimal places,
    rounded with ``ROUND_HALF_UP``."""

    def test_result_type_is_decimal(self):
        result = daily_floor_plan_interest(
            Decimal("18500.00"), Decimal("8.5"), 30
        )
        self.assertIsInstance(result, Decimal)

    def test_result_is_quantized_to_two_decimal_places(self):
        result = daily_floor_plan_interest(
            Decimal("18500.00"), Decimal("8.5"), 30
        )
        # Two decimal places in Decimal terms = exponent of -2.
        self.assertEqual(result.as_tuple().exponent, -2)

    def test_round_half_up_pushes_the_five_up(self):
        # Construct an input where the third-decimal digit is exactly
        # 5 and everything to the right is 0 — the classic
        # HALF_UP-vs-HALF_EVEN divergence.
        # Target raw: 0.005 exactly. Then HALF_UP → 0.01, HALF_EVEN →
        # 0.00 (bank round to even).
        # Pick principal * apr * days / 36500 = 0.005:
        #   principal = 1825, apr = 1.0, days = 1
        #   → 1825 * 1 * 1 / 36500 = 0.05 (nope, too big)
        # Try principal = 1825, apr = 0.1, days = 1:
        #   → 1825 * 0.1 * 1 / 36500 = 182.5 / 36500 = 0.005 exactly
        result = daily_floor_plan_interest(
            Decimal("1825"), Decimal("0.1"), 1
        )
        # ROUND_HALF_UP: 0.005 → 0.01. If HALF_EVEN were in effect,
        # this would be 0.00. Failing this test means the rounding
        # mode drifted.
        self.assertEqual(result, Decimal("0.01"))

    def test_result_is_deterministic_across_repeated_calls(self):
        args = (Decimal("18500.00"), Decimal("8.5"), 30)
        first = daily_floor_plan_interest(*args)
        second = daily_floor_plan_interest(*args)
        third = daily_floor_plan_interest(*args)
        self.assertEqual(first, second)
        self.assertEqual(second, third)


class LeapYearNeutrality(SimpleTestCase):
    """The engine takes ``days_elapsed: int`` — it has no calendar
    knowledge. A 30-day accrual is a 30-day accrual regardless of
    whether those 30 days straddled Feb 29. Locks that the engine
    does not accidentally develop calendar-awareness later."""

    def test_thirty_day_result_is_identical_regardless_of_context(self):
        args = (Decimal("18500.00"), Decimal("8.5"), 30)
        # Any two calls with the same args must produce equal
        # results. The point of this test is to document the
        # invariant, not to prove Python arithmetic is stable —
        # the invariant is "no hidden calendar branch."
        self.assertEqual(
            daily_floor_plan_interest(*args),
            daily_floor_plan_interest(*args),
        )
        # And the value equals the calculator: 18500 * 0.085 * 30 /
        # 365 = 129.246575... → 129.25.
        self.assertEqual(
            daily_floor_plan_interest(*args), Decimal("129.25")
        )


class PrincipalIsGeneric(SimpleTestCase):
    """The M2.4a scope-discipline decision recorded here as a test:
    the engine accepts an arbitrary ``principal`` value and does not
    care whether it represents purchase price, post-curtailment
    balance, per-lender payoff, or a hypothetical amount. Future
    accrual services choose the meaningful principal in context."""

    def test_engine_accepts_arbitrary_principal_shapes(self):
        # Purchase-price principal.
        purchase_price = Decimal("18500.00")
        # Hypothetical post-curtailment principal (500 curtailment
        # applied).
        curtailed = Decimal("18000.00")
        # Hypothetical mid-period payoff amount (partial payment
        # applied).
        payoff = Decimal("17250.00")
        # Same APR + days for all three.
        apr = Decimal("8.5")
        days = 30
        # All three calls succeed and produce distinct, correctly-
        # ordered results (higher principal → higher interest).
        r1 = daily_floor_plan_interest(purchase_price, apr, days)
        r2 = daily_floor_plan_interest(curtailed, apr, days)
        r3 = daily_floor_plan_interest(payoff, apr, days)
        self.assertGreater(r1, r2)
        self.assertGreater(r2, r3)


class TypeCoercion(SimpleTestCase):
    """Non-Decimal numeric inputs are coerced safely — the engine
    should be forgiving to callers who pass int/float without
    silently drifting into float arithmetic."""

    def test_int_principal_and_apr_are_coerced(self):
        # Same math as ``test_full_year_365_days`` but with int inputs.
        # ``# type: ignore`` — the signature declares Decimal for
        # type-safety at call sites; this test verifies the runtime
        # coercion path (Decimal(str(value))) that keeps the engine
        # forgiving to callers that haven't wrapped their values yet.
        result = daily_floor_plan_interest(10000, 10, 365)  # type: ignore[arg-type]
        self.assertEqual(result, Decimal("1000.00"))
        self.assertIsInstance(result, Decimal)

    def test_float_principal_is_coerced_via_str(self):
        # Coercion goes through ``Decimal(str(value))`` to avoid
        # float→Decimal precision loss. 0.1 as a float is
        # 0.1000000000000000055511151231257827021181583404541015625;
        # via str() it becomes exactly Decimal("0.1").
        result = daily_floor_plan_interest(500.0, 5.0, 7)  # type: ignore[arg-type]
        self.assertEqual(result, Decimal("0.48"))

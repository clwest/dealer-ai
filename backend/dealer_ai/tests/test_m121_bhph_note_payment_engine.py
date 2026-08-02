"""Milestone 12 · Increment 1 (SESSION_121) — BhphNote amortization tests.

Locks the pure-math surface added to
:mod:`dealer_ai.services.payment_engine` for BhphNote origination:

- :func:`bhph_note_number_of_periods`
- :func:`bhph_note_periodic_payment`
- :func:`bhph_note_schedule`
- :data:`BHPH_PAYMENT_FREQUENCY_CHOICES` vocab
- :class:`UnknownBhphFrequencyError`

Standard-loan math + M2 customer-shopping BHPH estimator remain
covered by existing tests; this module only exercises the note-side
math.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import SimpleTestCase

from dealer_ai.services.payment_engine import (
    UnknownBhphFrequencyError,
    bhph_note_number_of_periods,
    bhph_note_periodic_payment,
    bhph_note_schedule,
)


class BhphNoteNumberOfPeriods(SimpleTestCase):
    def test_weekly_equals_term_weeks(self):
        self.assertEqual(
            bhph_note_number_of_periods(130, "weekly"), 130
        )

    def test_biweekly_halves_term_weeks(self):
        # 130 weeks / 2 = 65 biweekly periods.
        self.assertEqual(
            bhph_note_number_of_periods(130, "biweekly"), 65
        )

    def test_semi_monthly_uses_24_over_52_ratio(self):
        # 130 * 24 / 52 = 60 semi-monthly periods.
        self.assertEqual(
            bhph_note_number_of_periods(130, "semi_monthly"), 60
        )

    def test_unknown_frequency_raises(self):
        with self.assertRaises(UnknownBhphFrequencyError):
            bhph_note_number_of_periods(52, "monthly")

    def test_short_term_rounds_up_to_at_least_one(self):
        # 1-week term against a semi_monthly cadence is nonsensical but
        # the math must not return 0 periods — the verb clamps.
        self.assertGreaterEqual(
            bhph_note_number_of_periods(1, "semi_monthly"), 1
        )


class BhphNotePeriodicPayment(SimpleTestCase):
    def test_zero_apr_produces_flat_amortization(self):
        # $10,000 / 100 weekly payments = $100.00/week.
        payment = bhph_note_periodic_payment(
            Decimal("10000.00"), Decimal("0.00"), 100, "weekly"
        )
        self.assertEqual(payment, Decimal("100.00"))

    def test_positive_apr_produces_higher_payment_than_zero(self):
        zero = bhph_note_periodic_payment(
            Decimal("10000.00"), Decimal("0.00"), 130, "weekly"
        )
        with_apr = bhph_note_periodic_payment(
            Decimal("10000.00"), Decimal("21.90"), 130, "weekly"
        )
        self.assertGreater(with_apr, zero)

    def test_result_is_decimal_quantized_to_cents(self):
        payment = bhph_note_periodic_payment(
            Decimal("8500.00"), Decimal("21.90"), 130, "weekly"
        )
        self.assertIsInstance(payment, Decimal)
        # Two-place quantization: no fractional cent below .01.
        self.assertEqual(payment.as_tuple().exponent, -2)

    def test_biweekly_payment_roughly_double_weekly_same_terms(self):
        weekly = bhph_note_periodic_payment(
            Decimal("10000.00"), Decimal("21.90"), 130, "weekly"
        )
        biweekly = bhph_note_periodic_payment(
            Decimal("10000.00"), Decimal("21.90"), 130, "biweekly"
        )
        ratio = biweekly / weekly
        # Should sit near 2.0 — same principal amortized over half the
        # payments with a per-period rate that is twice as large.
        self.assertGreater(ratio, Decimal("1.95"))
        self.assertLess(ratio, Decimal("2.10"))

    def test_zero_principal_raises_value_error(self):
        with self.assertRaises(ValueError):
            bhph_note_periodic_payment(
                Decimal("0.00"), Decimal("21.90"), 130, "weekly"
            )

    def test_negative_apr_raises_value_error(self):
        with self.assertRaises(ValueError):
            bhph_note_periodic_payment(
                Decimal("10000.00"), Decimal("-1.00"), 130, "weekly"
            )

    def test_zero_term_raises_value_error(self):
        with self.assertRaises(ValueError):
            bhph_note_periodic_payment(
                Decimal("10000.00"), Decimal("21.90"), 0, "weekly"
            )

    def test_unknown_frequency_raises(self):
        with self.assertRaises(UnknownBhphFrequencyError):
            bhph_note_periodic_payment(
                Decimal("10000.00"), Decimal("21.90"), 130, "monthly"
            )


class BhphNoteSchedule(SimpleTestCase):
    FIRST_DUE = dt.date(2026, 9, 1)

    def test_weekly_schedule_spaced_seven_days(self):
        schedule = bhph_note_schedule(
            Decimal("5000.00"),
            Decimal("21.90"),
            10,
            "weekly",
            self.FIRST_DUE,
        )
        self.assertEqual(len(schedule), 10)
        self.assertEqual(schedule[0][0], self.FIRST_DUE)
        self.assertEqual(schedule[1][0], self.FIRST_DUE + dt.timedelta(days=7))
        self.assertEqual(schedule[9][0], self.FIRST_DUE + dt.timedelta(days=63))

    def test_biweekly_schedule_spaced_fourteen_days(self):
        schedule = bhph_note_schedule(
            Decimal("5000.00"),
            Decimal("21.90"),
            20,
            "biweekly",
            self.FIRST_DUE,
        )
        self.assertEqual(len(schedule), 10)
        self.assertEqual(schedule[1][0], self.FIRST_DUE + dt.timedelta(days=14))

    def test_semi_monthly_schedule_spaced_fifteen_days(self):
        schedule = bhph_note_schedule(
            Decimal("5000.00"),
            Decimal("21.90"),
            26,
            "semi_monthly",
            self.FIRST_DUE,
        )
        # 26 weeks * 24 / 52 = 12 periods.
        self.assertEqual(len(schedule), 12)
        self.assertEqual(schedule[1][0], self.FIRST_DUE + dt.timedelta(days=15))

    def test_all_installments_equal_payment_amount(self):
        schedule = bhph_note_schedule(
            Decimal("5000.00"),
            Decimal("21.90"),
            10,
            "weekly",
            self.FIRST_DUE,
        )
        amounts = {amount for _, amount in schedule}
        # Equal-installment schedule per M12.1 §7 — final-period rounding
        # drift is settled at closeout by a future payoff verb, not
        # quoted to the buyer.
        self.assertEqual(len(amounts), 1)

    def test_schedule_amount_matches_periodic_payment_verb(self):
        principal = Decimal("8500.00")
        apr = Decimal("21.90")
        expected = bhph_note_periodic_payment(principal, apr, 130, "weekly")
        schedule = bhph_note_schedule(
            principal, apr, 130, "weekly", self.FIRST_DUE
        )
        self.assertEqual(schedule[0][1], expected)

"""Milestone 12 · Increment 3 (SESSION_123) — delinquency-math tests.

Locks the pure verbs in
:mod:`dealer_ai.services.bhph_delinquency.compute`:

- :func:`bucket_for_days` — 7-value vocab boundaries.
- :func:`next_expected_due` — cadence-aware next-due projection.
- :func:`days_past_due_for` — grace-respecting date arithmetic.
"""

from __future__ import annotations

import datetime as dt

from django.test import SimpleTestCase

from dealer_ai.models import (
    BHPH_AGING_BUCKET_1_15,
    BHPH_AGING_BUCKET_16_30,
    BHPH_AGING_BUCKET_31_60,
    BHPH_AGING_BUCKET_61_90,
    BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
    BHPH_AGING_BUCKET_CHOICES,
    BHPH_AGING_BUCKET_CURRENT,
    BHPH_AGING_BUCKET_OVER_90,
)
from dealer_ai.services.bhph_delinquency.compute import (
    bucket_for_days,
    days_past_due_for,
    next_expected_due,
)
from dealer_ai.services.payment_engine import UnknownBhphFrequencyError


class BucketForDaysBoundaries(SimpleTestCase):
    def test_zero_is_current(self):
        self.assertEqual(bucket_for_days(0), BHPH_AGING_BUCKET_CURRENT)

    def test_negative_collapses_to_current(self):
        # Defensive clamp — callers should have returned 0 already.
        self.assertEqual(bucket_for_days(-5), BHPH_AGING_BUCKET_CURRENT)

    def test_one_day_late_is_1_15(self):
        self.assertEqual(bucket_for_days(1), BHPH_AGING_BUCKET_1_15)

    def test_fifteen_days_is_1_15_upper_bound(self):
        self.assertEqual(bucket_for_days(15), BHPH_AGING_BUCKET_1_15)

    def test_sixteen_days_flips_to_16_30(self):
        self.assertEqual(bucket_for_days(16), BHPH_AGING_BUCKET_16_30)

    def test_thirty_days_is_16_30_upper_bound(self):
        self.assertEqual(bucket_for_days(30), BHPH_AGING_BUCKET_16_30)

    def test_thirty_one_flips_to_31_60(self):
        self.assertEqual(bucket_for_days(31), BHPH_AGING_BUCKET_31_60)

    def test_sixty_days_is_31_60_upper_bound(self):
        self.assertEqual(bucket_for_days(60), BHPH_AGING_BUCKET_31_60)

    def test_sixty_one_flips_to_61_90(self):
        self.assertEqual(bucket_for_days(61), BHPH_AGING_BUCKET_61_90)

    def test_ninety_days_is_61_90_upper_bound(self):
        self.assertEqual(bucket_for_days(90), BHPH_AGING_BUCKET_61_90)

    def test_ninety_one_flips_to_over_90(self):
        self.assertEqual(bucket_for_days(91), BHPH_AGING_BUCKET_OVER_90)

    def test_one_hundred_nineteen_is_over_90(self):
        self.assertEqual(bucket_for_days(119), BHPH_AGING_BUCKET_OVER_90)

    def test_one_hundred_twenty_is_charge_off_candidate(self):
        self.assertEqual(
            bucket_for_days(120),
            BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
        )

    def test_large_days_is_charge_off_candidate(self):
        self.assertEqual(
            bucket_for_days(500),
            BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
        )


class BucketVocab(SimpleTestCase):
    def test_vocab_exact_seven_value_set(self):
        vocab = {key for key, _ in BHPH_AGING_BUCKET_CHOICES}
        self.assertEqual(
            vocab,
            {
                BHPH_AGING_BUCKET_CURRENT,
                BHPH_AGING_BUCKET_1_15,
                BHPH_AGING_BUCKET_16_30,
                BHPH_AGING_BUCKET_31_60,
                BHPH_AGING_BUCKET_61_90,
                BHPH_AGING_BUCKET_OVER_90,
                BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
            },
        )


class NextExpectedDue(SimpleTestCase):
    FIRST = dt.date(2026, 9, 1)

    def test_zero_payments_returns_first_due(self):
        self.assertEqual(
            next_expected_due(self.FIRST, "weekly", 0), self.FIRST
        )

    def test_weekly_advances_by_seven_days(self):
        self.assertEqual(
            next_expected_due(self.FIRST, "weekly", 4),
            self.FIRST + dt.timedelta(days=28),
        )

    def test_biweekly_advances_by_fourteen_days(self):
        self.assertEqual(
            next_expected_due(self.FIRST, "biweekly", 2),
            self.FIRST + dt.timedelta(days=28),
        )

    def test_semi_monthly_advances_by_fifteen_days(self):
        self.assertEqual(
            next_expected_due(self.FIRST, "semi_monthly", 4),
            self.FIRST + dt.timedelta(days=60),
        )

    def test_unknown_frequency_raises(self):
        with self.assertRaises(UnknownBhphFrequencyError):
            next_expected_due(self.FIRST, "monthly", 4)

    def test_negative_payments_made_raises(self):
        with self.assertRaises(ValueError):
            next_expected_due(self.FIRST, "weekly", -1)


class DaysPastDueFor(SimpleTestCase):
    DUE = dt.date(2026, 9, 1)

    def test_before_due_returns_zero(self):
        self.assertEqual(
            days_past_due_for(
                next_expected=self.DUE,
                grace_days=5,
                as_of=dt.date(2026, 8, 31),
            ),
            0,
        )

    def test_on_due_returns_zero(self):
        self.assertEqual(
            days_past_due_for(
                next_expected=self.DUE,
                grace_days=5,
                as_of=self.DUE,
            ),
            0,
        )

    def test_within_grace_returns_zero(self):
        # 3 days after due, grace is 5 → still within grace.
        self.assertEqual(
            days_past_due_for(
                next_expected=self.DUE,
                grace_days=5,
                as_of=self.DUE + dt.timedelta(days=3),
            ),
            0,
        )

    def test_at_grace_expiry_returns_zero(self):
        # Grace expires ON grace_days after due (inclusive).
        self.assertEqual(
            days_past_due_for(
                next_expected=self.DUE,
                grace_days=5,
                as_of=self.DUE + dt.timedelta(days=5),
            ),
            0,
        )

    def test_past_grace_measures_from_original_due(self):
        # 10 days after due, grace 5. Aging measured from due, not from
        # grace expiry — matches BHPH portfolio reporting.
        self.assertEqual(
            days_past_due_for(
                next_expected=self.DUE,
                grace_days=5,
                as_of=self.DUE + dt.timedelta(days=10),
            ),
            10,
        )

    def test_negative_grace_treated_as_zero(self):
        # Defensive — should never happen in real data.
        self.assertEqual(
            days_past_due_for(
                next_expected=self.DUE,
                grace_days=-3,
                as_of=self.DUE + dt.timedelta(days=1),
            ),
            1,
        )

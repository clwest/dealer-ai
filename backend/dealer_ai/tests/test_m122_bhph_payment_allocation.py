"""Milestone 12 · Increment 2 (SESSION_122) — allocation-math tests.

Locks the pure verbs added to
:mod:`dealer_ai.services.bhph_payments.apply`:

- :func:`allocate_payment` — fees → interest → principal splitter.
- :func:`interest_owed_for_period` — per-period accrual.
- :func:`outstanding_balance` — remaining principal.
- :class:`OverpaymentError`.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase

from dealer_ai.services.bhph_payments.apply import (
    OverpaymentError,
    PaymentAllocation,
    allocate_payment,
    interest_owed_for_period,
    outstanding_balance,
)
from dealer_ai.services.payment_engine import UnknownBhphFrequencyError


class OutstandingBalance(SimpleTestCase):
    def test_no_payments_returns_full_principal(self):
        self.assertEqual(
            outstanding_balance(Decimal("8000.00"), Decimal("0.00")),
            Decimal("8000.00"),
        )

    def test_prior_payments_reduce_balance(self):
        self.assertEqual(
            outstanding_balance(Decimal("8000.00"), Decimal("500.00")),
            Decimal("7500.00"),
        )

    def test_overpaid_principal_clamps_to_zero(self):
        # Historical rounding drift can produce principal_paid > financed
        # by a cent; balance must not go negative.
        self.assertEqual(
            outstanding_balance(Decimal("8000.00"), Decimal("8001.00")),
            Decimal("0.00"),
        )


class InterestOwedForPeriod(SimpleTestCase):
    def test_zero_apr_yields_zero_interest(self):
        self.assertEqual(
            interest_owed_for_period(
                Decimal("5000.00"), Decimal("0.00"), "weekly"
            ),
            Decimal("0.00"),
        )

    def test_zero_balance_yields_zero_interest(self):
        self.assertEqual(
            interest_owed_for_period(
                Decimal("0.00"), Decimal("21.90"), "weekly"
            ),
            Decimal("0.00"),
        )

    def test_positive_apr_and_balance_yields_positive_interest(self):
        # 5000 * (21.9 / 52 / 100) ≈ 21.06
        interest = interest_owed_for_period(
            Decimal("5000.00"), Decimal("21.90"), "weekly"
        )
        self.assertGreater(interest, Decimal("0.00"))
        # Sanity band — should be in the neighborhood of $21/week.
        self.assertLess(interest, Decimal("25.00"))
        self.assertGreater(interest, Decimal("15.00"))

    def test_biweekly_interest_is_roughly_double_weekly(self):
        weekly = interest_owed_for_period(
            Decimal("5000.00"), Decimal("21.90"), "weekly"
        )
        biweekly = interest_owed_for_period(
            Decimal("5000.00"), Decimal("21.90"), "biweekly"
        )
        ratio = biweekly / weekly
        self.assertGreater(ratio, Decimal("1.95"))
        self.assertLess(ratio, Decimal("2.05"))

    def test_unknown_frequency_raises(self):
        with self.assertRaises(UnknownBhphFrequencyError):
            interest_owed_for_period(
                Decimal("5000.00"), Decimal("21.90"), "monthly"
            )


class AllocatePayment(SimpleTestCase):
    def test_split_returns_named_tuple(self):
        allocation = allocate_payment(
            Decimal("100.00"),
            outstanding_balance_now=Decimal("5000.00"),
            interest_owed=Decimal("21.06"),
        )
        self.assertIsInstance(allocation, PaymentAllocation)

    def test_fees_are_zero_when_no_outstanding_fees(self):
        allocation = allocate_payment(
            Decimal("100.00"),
            outstanding_balance_now=Decimal("5000.00"),
            interest_owed=Decimal("21.06"),
        )
        self.assertEqual(allocation.fees, Decimal("0.00"))

    def test_interest_allocated_before_principal(self):
        allocation = allocate_payment(
            Decimal("100.00"),
            outstanding_balance_now=Decimal("5000.00"),
            interest_owed=Decimal("21.06"),
        )
        # Interest first, principal is remainder.
        self.assertEqual(allocation.interest, Decimal("21.06"))
        self.assertEqual(allocation.principal, Decimal("78.94"))

    def test_split_components_sum_to_amount(self):
        allocation = allocate_payment(
            Decimal("125.00"),
            outstanding_balance_now=Decimal("5000.00"),
            interest_owed=Decimal("21.06"),
        )
        self.assertEqual(
            allocation.fees + allocation.interest + allocation.principal,
            Decimal("125.00"),
        )

    def test_fees_first_when_outstanding(self):
        # 100 payment, 30 fees outstanding, 20 interest owed, 5000 balance.
        # Expected: fees=30, interest=20, principal=50.
        allocation = allocate_payment(
            Decimal("100.00"),
            outstanding_balance_now=Decimal("5000.00"),
            interest_owed=Decimal("20.00"),
            outstanding_fees=Decimal("30.00"),
        )
        self.assertEqual(allocation.fees, Decimal("30.00"))
        self.assertEqual(allocation.interest, Decimal("20.00"))
        self.assertEqual(allocation.principal, Decimal("50.00"))

    def test_undershoot_interest_allocates_less_than_owed(self):
        # 15 payment, 20 interest owed → interest=15, principal=0.
        allocation = allocate_payment(
            Decimal("15.00"),
            outstanding_balance_now=Decimal("5000.00"),
            interest_owed=Decimal("20.00"),
        )
        self.assertEqual(allocation.interest, Decimal("15.00"))
        self.assertEqual(allocation.principal, Decimal("0.00"))

    def test_overpayment_raises(self):
        # 100 payment but only 20 principal + 5 interest available.
        with self.assertRaises(OverpaymentError):
            allocate_payment(
                Decimal("100.00"),
                outstanding_balance_now=Decimal("20.00"),
                interest_owed=Decimal("5.00"),
            )

    def test_exact_payoff_allowed(self):
        # 25 payment for exactly 20 principal + 5 interest.
        allocation = allocate_payment(
            Decimal("25.00"),
            outstanding_balance_now=Decimal("20.00"),
            interest_owed=Decimal("5.00"),
        )
        self.assertEqual(allocation.interest, Decimal("5.00"))
        self.assertEqual(allocation.principal, Decimal("20.00"))

    def test_zero_amount_raises_value_error(self):
        with self.assertRaises(ValueError):
            allocate_payment(
                Decimal("0.00"),
                outstanding_balance_now=Decimal("5000.00"),
                interest_owed=Decimal("21.06"),
            )

    def test_negative_amount_raises_value_error(self):
        with self.assertRaises(ValueError):
            allocate_payment(
                Decimal("-10.00"),
                outstanding_balance_now=Decimal("5000.00"),
                interest_owed=Decimal("21.06"),
            )

    def test_negative_balance_raises_value_error(self):
        with self.assertRaises(ValueError):
            allocate_payment(
                Decimal("100.00"),
                outstanding_balance_now=Decimal("-1.00"),
                interest_owed=Decimal("21.06"),
            )

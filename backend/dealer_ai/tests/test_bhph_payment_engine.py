"""SESSION_030 pivot: BHPH (buy-here-pay-here) payment engine variant.

Locks the deterministic math for in-house-financed indie deals so
Copper Canyon-style scenarios can quote weekly / biweekly payments
without going through an LLM. Standard-loan math is unchanged and
covered by existing tests; this module only exercises the BHPH path.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from dealer_ai.services.payment_engine import (
    BHPH_APR_DEFAULT,
    BHPH_MIN_DOWN_PAYMENT_PCT,
    BHPH_TERM_MONTHS_DEFAULT,
    BHPHPaymentEstimate,
    bhph_min_down_payment,
    estimate_bhph_payment,
)


class BHPHMinDownPayment(SimpleTestCase):
    def test_uses_default_percentage(self):
        # $10,000 * 20% = $2,000
        self.assertAlmostEqual(bhph_min_down_payment(10_000), 2000.0)

    def test_custom_percentage(self):
        self.assertAlmostEqual(
            bhph_min_down_payment(10_000, down_pct=25.0), 2500.0
        )


class EstimateBHPHPayment(SimpleTestCase):
    def test_default_cadence_is_weekly(self):
        est = estimate_bhph_payment(10_000)
        self.assertEqual(est.cadence, "weekly")

    def test_weekly_payment_uses_52_periods_per_year(self):
        # 30-month term × (52/12) weeks per month = 130 weekly payments.
        est = estimate_bhph_payment(10_000, cadence="weekly")
        self.assertEqual(est.number_of_payments, 130)

    def test_biweekly_payment_uses_26_periods_per_year(self):
        # 30-month term × (26/12) = 65 biweekly payments.
        est = estimate_bhph_payment(10_000, cadence="biweekly")
        self.assertEqual(est.number_of_payments, 65)

    def test_monthly_equivalent_is_periodic_times_periods_per_month(self):
        est = estimate_bhph_payment(10_000, cadence="weekly")
        self.assertAlmostEqual(
            est.monthly_equivalent,
            est.periodic_payment * (52.0 / 12.0),
            places=6,
        )

    def test_biweekly_payment_is_roughly_2x_weekly_same_terms(self):
        weekly = estimate_bhph_payment(10_000, cadence="weekly")
        biweekly = estimate_bhph_payment(10_000, cadence="biweekly")
        # Biweekly payment should be within a couple % of 2× weekly —
        # they amortize the same principal + interest over the same
        # term, just different cadence granularity.
        ratio = biweekly.periodic_payment / weekly.periodic_payment
        self.assertGreater(ratio, 1.95)
        self.assertLess(ratio, 2.10)

    def test_positive_payment_for_realistic_deal(self):
        est = estimate_bhph_payment(
            8_500,
            cadence="weekly",
            down_payment=1_500,
            apr=BHPH_APR_DEFAULT,
            term_months=BHPH_TERM_MONTHS_DEFAULT,
        )
        # Sanity: sub-$100/week for a small used vehicle at 21.9% is
        # in the ballpark for real BHPH lots.
        self.assertGreater(est.periodic_payment, 0.0)
        self.assertLess(est.periodic_payment, 200.0)
        self.assertEqual(est.apr, BHPH_APR_DEFAULT)
        self.assertEqual(est.term_months, BHPH_TERM_MONTHS_DEFAULT)

    def test_trade_in_and_down_payment_reduce_financed(self):
        base = estimate_bhph_payment(10_000, cadence="weekly")
        with_down = estimate_bhph_payment(
            10_000, cadence="weekly", down_payment=2_000
        )
        with_trade = estimate_bhph_payment(
            10_000, cadence="weekly", trade_in_value=2_000
        )
        self.assertLess(with_down.total_financed, base.total_financed)
        self.assertLess(with_trade.total_financed, base.total_financed)
        self.assertLess(with_down.periodic_payment, base.periodic_payment)
        self.assertLess(with_trade.periodic_payment, base.periodic_payment)

    def test_zero_apr_produces_flat_amortization(self):
        est = estimate_bhph_payment(
            5_000,
            cadence="weekly",
            apr=0.0,
            term_months=12,
            tax_rate=0.0,
            fees=0.0,
        )
        # 12 months * (52/12) = 52 weekly payments; $5000/52 ≈ $96.15
        self.assertEqual(est.number_of_payments, 52)
        self.assertAlmostEqual(est.periodic_payment, 5000.0 / 52.0, places=2)

    def test_min_down_payment_reported_alongside_estimate(self):
        est = estimate_bhph_payment(10_000)
        self.assertAlmostEqual(
            est.min_down_payment_required,
            10_000 * (BHPH_MIN_DOWN_PAYMENT_PCT / 100.0),
        )

    def test_invalid_cadence_raises(self):
        with self.assertRaises(ValueError):
            estimate_bhph_payment(10_000, cadence="monthly")  # type: ignore[arg-type]

    def test_to_dict_shape_is_serializable(self):
        est = estimate_bhph_payment(10_000)
        payload = est.to_dict()

        for key in (
            "periodic_payment",
            "cadence",
            "monthly_equivalent",
            "total_financed",
            "apr",
            "term_months",
            "number_of_payments",
            "down_payment",
            "trade_in_value",
            "taxes",
            "fees",
            "min_down_payment_required",
        ):
            self.assertIn(key, payload)
        self.assertEqual(payload["cadence"], "weekly")

    def test_estimate_is_a_dataclass_instance(self):
        est = estimate_bhph_payment(10_000)
        self.assertIsInstance(est, BHPHPaymentEstimate)

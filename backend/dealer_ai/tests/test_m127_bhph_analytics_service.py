"""Milestone 12 · Increment 7 (SESSION_127) — BHPH analytics service tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_AGING_BUCKET_1_15,
    BHPH_AGING_BUCKET_31_60,
    BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
    BHPH_AGING_BUCKET_CURRENT,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PROMISE_REASON_PAYCHECK,
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_KEPT,
    BHPH_PROMISE_STATE_PROMISED,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    BhphPromiseToPay,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_analytics import (
    bucket_histogram,
    cure_rate,
    portfolio_summary,
    ptp_kept_ratio,
    weighted_average_apr,
    weighted_average_days_past_due,
)


def _make_note(
    dealership: Dealership,
    *,
    stock: str,
    principal: Decimal = Decimal("8000.00"),
    apr: Decimal = Decimal("21.90"),
    bucket: str = BHPH_AGING_BUCKET_CURRENT,
    days_past_due: int = 0,
) -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Kia",
        price=Decimal("10500.00"),
        dealership=dealership,
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("10500.00"),
        finance_type=SALE_FINANCE_TYPE_BHPH,
        gross_realized=Decimal("1200.00"),
    )
    return BhphNote.objects.create(
        dealership=dealership,
        sale=sale,
        principal_financed=principal,
        apr=apr,
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=dt.date(2026, 9, 1),
        current_bucket=bucket,
        days_past_due=days_past_due,
    )


class BucketHistogramTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m127-hist", name="M127 Hist"
        )

    def test_empty_portfolio_returns_seven_zero_rows(self) -> None:
        rows = bucket_histogram(self.dealership)
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row.note_count == 0 for row in rows))
        self.assertTrue(
            all(row.principal_total == Decimal("0.00") for row in rows)
        )

    def test_row_order_matches_vocab_order(self) -> None:
        rows = bucket_histogram(self.dealership)
        buckets = [row.bucket for row in rows]
        self.assertEqual(
            buckets,
            [
                BHPH_AGING_BUCKET_CURRENT,
                "1_15",
                "16_30",
                "31_60",
                "61_90",
                "over_90",
                BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
            ],
        )

    def test_counts_and_totals_per_bucket(self) -> None:
        _make_note(
            self.dealership,
            stock="M127-HIST-C1",
            principal=Decimal("8000.00"),
            bucket=BHPH_AGING_BUCKET_CURRENT,
        )
        _make_note(
            self.dealership,
            stock="M127-HIST-C2",
            principal=Decimal("5000.00"),
            bucket=BHPH_AGING_BUCKET_CURRENT,
        )
        _make_note(
            self.dealership,
            stock="M127-HIST-D",
            principal=Decimal("12000.00"),
            bucket=BHPH_AGING_BUCKET_31_60,
            days_past_due=45,
        )
        rows = {row.bucket: row for row in bucket_histogram(self.dealership)}
        self.assertEqual(rows[BHPH_AGING_BUCKET_CURRENT].note_count, 2)
        self.assertEqual(
            rows[BHPH_AGING_BUCKET_CURRENT].principal_total,
            Decimal("13000.00"),
        )
        self.assertEqual(rows[BHPH_AGING_BUCKET_31_60].note_count, 1)
        self.assertEqual(
            rows[BHPH_AGING_BUCKET_31_60].principal_total, Decimal("12000.00")
        )

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="m127-hist-other", name="M127 Other"
        )
        _make_note(other, stock="M127-HIST-X")
        rows = {row.bucket: row for row in bucket_histogram(self.dealership)}
        self.assertEqual(rows[BHPH_AGING_BUCKET_CURRENT].note_count, 0)


class CureRateTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m127-cure", name="M127 Cure"
        )

    def test_empty_portfolio_returns_none(self) -> None:
        self.assertIsNone(cure_rate(self.dealership))

    def test_all_current_returns_one(self) -> None:
        for i in range(3):
            _make_note(
                self.dealership,
                stock=f"M127-CURE-C{i}",
                bucket=BHPH_AGING_BUCKET_CURRENT,
            )
        self.assertEqual(cure_rate(self.dealership), Decimal("1.0000"))

    def test_half_current_returns_point_five(self) -> None:
        _make_note(
            self.dealership,
            stock="M127-CURE-C",
            bucket=BHPH_AGING_BUCKET_CURRENT,
        )
        _make_note(
            self.dealership,
            stock="M127-CURE-D",
            bucket=BHPH_AGING_BUCKET_1_15,
            days_past_due=5,
        )
        self.assertEqual(cure_rate(self.dealership), Decimal("0.5000"))


class WeightedAverageAprTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m127-apr", name="M127 APR"
        )

    def test_empty_portfolio_returns_none(self) -> None:
        self.assertIsNone(weighted_average_apr(self.dealership))

    def test_uniform_apr_returns_uniform_average(self) -> None:
        for i in range(3):
            _make_note(
                self.dealership,
                stock=f"M127-APR-U{i}",
                principal=Decimal("5000.00"),
                apr=Decimal("21.90"),
            )
        self.assertEqual(
            weighted_average_apr(self.dealership), Decimal("21.90")
        )

    def test_principal_weighting_favors_larger_note(self) -> None:
        # $10k @ 22%, $2k @ 30% → weighted APR closer to 22% than 26%.
        _make_note(
            self.dealership,
            stock="M127-APR-BIG",
            principal=Decimal("10000.00"),
            apr=Decimal("22.00"),
        )
        _make_note(
            self.dealership,
            stock="M127-APR-SMALL",
            principal=Decimal("2000.00"),
            apr=Decimal("30.00"),
        )
        result = weighted_average_apr(self.dealership)
        # Expected: (10000*22 + 2000*30) / 12000 = 260000 / 12000 ≈ 23.33
        self.assertEqual(result, Decimal("23.33"))


class WeightedAverageDaysPastDueTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m127-dpd", name="M127 DPD"
        )

    def test_empty_portfolio_returns_none(self) -> None:
        self.assertIsNone(
            weighted_average_days_past_due(self.dealership)
        )

    def test_all_current_returns_zero(self) -> None:
        _make_note(
            self.dealership,
            stock="M127-DPD-C",
            bucket=BHPH_AGING_BUCKET_CURRENT,
            days_past_due=0,
        )
        self.assertEqual(
            weighted_average_days_past_due(self.dealership),
            Decimal("0.00"),
        )

    def test_weighted_by_principal(self) -> None:
        # $10k @ 30 dpd, $5k @ 0 dpd → weighted DPD = 300000/15000 = 20.
        _make_note(
            self.dealership,
            stock="M127-DPD-DEL",
            principal=Decimal("10000.00"),
            bucket=BHPH_AGING_BUCKET_1_15,
            days_past_due=30,
        )
        _make_note(
            self.dealership,
            stock="M127-DPD-CUR",
            principal=Decimal("5000.00"),
            bucket=BHPH_AGING_BUCKET_CURRENT,
            days_past_due=0,
        )
        self.assertEqual(
            weighted_average_days_past_due(self.dealership),
            Decimal("20.00"),
        )


class PtpKeptRatioTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m127-ptp", name="M127 PTP"
        )
        self.note = _make_note(self.dealership, stock="M127-PTP-1")

    def _mk(self, state: str) -> BhphPromiseToPay:
        return BhphPromiseToPay.objects.create(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now(),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
            state=state,
        )

    def test_no_resolved_returns_none(self) -> None:
        # Only open promises → denominator zero → None.
        self._mk(BHPH_PROMISE_STATE_PROMISED)
        self.assertIsNone(ptp_kept_ratio(self.dealership))

    def test_all_kept_returns_one(self) -> None:
        for _ in range(3):
            self._mk(BHPH_PROMISE_STATE_KEPT)
        self.assertEqual(
            ptp_kept_ratio(self.dealership), Decimal("1.0000")
        )

    def test_mixed_kept_and_broken(self) -> None:
        self._mk(BHPH_PROMISE_STATE_KEPT)
        self._mk(BHPH_PROMISE_STATE_KEPT)
        self._mk(BHPH_PROMISE_STATE_BROKEN)
        # Still-open promise doesn't affect ratio.
        self._mk(BHPH_PROMISE_STATE_PROMISED)
        self.assertEqual(
            ptp_kept_ratio(self.dealership), Decimal("0.6667")
        )


class PortfolioSummaryTests(TestCase):
    def test_empty_portfolio_bundles_zeros_and_nones(self) -> None:
        dealership = Dealership.objects.create(
            slug="m127-sum-empty", name="M127 Sum Empty"
        )
        summary = portfolio_summary(dealership)
        self.assertEqual(summary.total_note_count, 0)
        self.assertEqual(
            summary.total_principal_financed, Decimal("0.00")
        )
        self.assertIsNone(summary.cure_rate)
        self.assertIsNone(summary.weighted_average_apr)
        self.assertIsNone(summary.weighted_average_days_past_due)
        self.assertIsNone(summary.ptp_kept_ratio)
        self.assertEqual(len(summary.bucket_histogram), 7)

    def test_populated_portfolio_totals(self) -> None:
        dealership = Dealership.objects.create(
            slug="m127-sum-pop", name="M127 Sum Pop"
        )
        _make_note(dealership, stock="M127-SUM-1", principal=Decimal("6000.00"))
        _make_note(dealership, stock="M127-SUM-2", principal=Decimal("9000.00"))
        summary = portfolio_summary(dealership)
        self.assertEqual(summary.total_note_count, 2)
        self.assertEqual(
            summary.total_principal_financed, Decimal("15000.00")
        )

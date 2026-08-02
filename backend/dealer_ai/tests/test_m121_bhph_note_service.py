"""Milestone 12 · Increment 1 (SESSION_121) — BhphNote service tests.

Locks :mod:`dealer_ai.services.bhph_notes` verbs per §7 M12.1.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_notes import (
    CrossTenantBhphNoteError,
    DuplicateBhphNoteError,
    NonBhphSaleError,
    get_bhph_note,
    get_payment_schedule,
    record_bhph_note,
)
from dealer_ai.services.payment_engine import (
    UnknownBhphFrequencyError,
    bhph_note_periodic_payment,
)


def _make_sale(
    dealership: Dealership,
    stock: str = "BHPH-SVC",
    finance_type: str = SALE_FINANCE_TYPE_BHPH,
) -> Sale:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Civic",
        price=Decimal("11000.00"),
        dealership=dealership,
    )
    return Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("11000.00"),
        finance_type=finance_type,
        gross_realized=Decimal("1200.00"),
    )


class RecordBhphNoteHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bhph-svc-hp", name="BHPH Svc HP"
        )
        self.sale = _make_sale(self.dealership, stock="BHPH-SVC-HP")

    def test_persists_row_and_computes_payment_amount(self) -> None:
        note = record_bhph_note(
            dealership=self.dealership,
            sale=self.sale,
            principal_financed=Decimal("8500.00"),
            apr=Decimal("21.90"),
            term_weeks=130,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            first_payment_due=dt.date(2026, 9, 1),
        )
        self.assertIsInstance(note, BhphNote)
        self.assertEqual(note.dealership_id, self.dealership.pk)
        self.assertEqual(note.sale_id, self.sale.pk)
        expected = bhph_note_periodic_payment(
            Decimal("8500.00"), Decimal("21.90"), 130, "weekly"
        )
        self.assertEqual(note.payment_amount, expected)

    def test_default_grace_days_when_omitted(self) -> None:
        note = record_bhph_note(
            dealership=self.dealership,
            sale=self.sale,
            principal_financed=Decimal("5000.00"),
            apr=Decimal("0.00"),
            term_weeks=52,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            first_payment_due=dt.date(2026, 9, 1),
        )
        self.assertEqual(note.default_grace_days, 5)


class RecordBhphNoteErrorPathsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bhph-svc-err", name="BHPH Svc Err"
        )
        self.other = Dealership.objects.create(
            slug="bhph-svc-err-other", name="BHPH Other"
        )
        self.sale = _make_sale(self.dealership, stock="BHPH-SVC-ERR")
        self.cross_sale = _make_sale(self.other, stock="BHPH-SVC-ERR-X")
        self.cash_sale = _make_sale(
            self.dealership,
            stock="BHPH-SVC-ERR-CASH",
            finance_type=SALE_FINANCE_TYPE_CASH,
        )

    def _call(self, sale: Sale, **kwargs) -> BhphNote:
        payload = {
            "dealership": self.dealership,
            "sale": sale,
            "principal_financed": Decimal("8500.00"),
            "apr": Decimal("21.90"),
            "term_weeks": 130,
            "payment_frequency": BHPH_PAYMENT_FREQUENCY_WEEKLY,
            "first_payment_due": dt.date(2026, 9, 1),
        }
        payload.update(kwargs)
        return record_bhph_note(**payload)

    def test_cross_tenant_sale_raises(self) -> None:
        with self.assertRaises(CrossTenantBhphNoteError):
            self._call(self.cross_sale)

    def test_non_bhph_sale_raises(self) -> None:
        with self.assertRaises(NonBhphSaleError):
            self._call(self.cash_sale)

    def test_duplicate_note_raises(self) -> None:
        self._call(self.sale)
        with self.assertRaises(DuplicateBhphNoteError):
            self._call(self.sale)

    def test_unknown_frequency_raises(self) -> None:
        with self.assertRaises(UnknownBhphFrequencyError):
            self._call(self.sale, payment_frequency="monthly")


class GetBhphNoteTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bhph-svc-get", name="BHPH Svc Get"
        )
        self.other = Dealership.objects.create(
            slug="bhph-svc-get-other", name="BHPH Other"
        )
        self.sale = _make_sale(self.dealership, stock="BHPH-SVC-GET")
        self.note = record_bhph_note(
            dealership=self.dealership,
            sale=self.sale,
            principal_financed=Decimal("5000.00"),
            apr=Decimal("21.90"),
            term_weeks=52,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            first_payment_due=dt.date(2026, 9, 1),
        )

    def test_returns_note_in_tenant(self) -> None:
        result = get_bhph_note(pk=self.note.pk, dealership=self.dealership)
        self.assertEqual(result, self.note)

    def test_returns_none_for_other_tenant(self) -> None:
        result = get_bhph_note(pk=self.note.pk, dealership=self.other)
        self.assertIsNone(result)

    def test_returns_none_for_missing_pk(self) -> None:
        self.assertIsNone(
            get_bhph_note(pk=999_999, dealership=self.dealership)
        )


class GetPaymentScheduleTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bhph-svc-sched", name="BHPH Svc Sched"
        )
        self.sale = _make_sale(self.dealership, stock="BHPH-SVC-SCHED")
        self.note = record_bhph_note(
            dealership=self.dealership,
            sale=self.sale,
            principal_financed=Decimal("5000.00"),
            apr=Decimal("21.90"),
            term_weeks=52,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            first_payment_due=dt.date(2026, 9, 1),
        )

    def test_schedule_length_matches_term_weeks_for_weekly(self) -> None:
        schedule = get_payment_schedule(self.note)
        self.assertEqual(len(schedule), 52)

    def test_first_installment_falls_on_first_payment_due(self) -> None:
        schedule = get_payment_schedule(self.note)
        self.assertEqual(schedule[0][0], dt.date(2026, 9, 1))

    def test_each_installment_equals_payment_amount(self) -> None:
        schedule = get_payment_schedule(self.note)
        for _, amount in schedule:
            self.assertEqual(amount, self.note.payment_amount)

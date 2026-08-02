"""Milestone 12 · Increment 3 (SESSION_123) — BhphNote aging-column tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    BHPH_AGING_BUCKET_CURRENT,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)


def _make_note(dealership: Dealership, stock: str = "M123-1") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Focus",
        price=Decimal("10000.00"),
        dealership=dealership,
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("10000.00"),
        finance_type=SALE_FINANCE_TYPE_BHPH,
        gross_realized=Decimal("1000.00"),
    )
    return BhphNote.objects.create(
        dealership=dealership,
        sale=sale,
        principal_financed=Decimal("8000.00"),
        apr=Decimal("21.90"),
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=dt.date(2026, 9, 1),
    )


class BhphNoteAgingColumnDefaultsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m123-def", name="M123 Defaults"
        )
        self.note = _make_note(self.dealership, stock="M123-DEF")

    def test_new_note_defaults_to_current_bucket(self) -> None:
        self.assertEqual(
            self.note.current_bucket, BHPH_AGING_BUCKET_CURRENT
        )

    def test_new_note_defaults_to_zero_days_past_due(self) -> None:
        self.assertEqual(self.note.days_past_due, 0)

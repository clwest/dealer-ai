"""Milestone 12 · Increment 2 (SESSION_122) — BhphPayment model tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_ACH,
    BHPH_PAYMENT_METHOD_CASH,
    BHPH_PAYMENT_METHOD_CHECK,
    BHPH_PAYMENT_METHOD_CHOICES,
    BHPH_PAYMENT_METHOD_DEBIT,
    BHPH_PAYMENT_METHOD_OTHER,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    BhphPayment,
    Dealership,
    Sale,
    Vehicle,
)


def _make_note(dealership: Dealership, stock: str = "M122-1") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Elantra",
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
        principal_financed=Decimal("8000.00"),
        apr=Decimal("21.90"),
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=dt.date(2026, 9, 1),
    )


class BhphPaymentDefaultsAndOrderingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m122-def", name="M122 Defaults"
        )
        self.note = _make_note(self.dealership, stock="M122-DEF")

    def test_defaults(self) -> None:
        payment = BhphPayment.objects.create(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
            applied_to_fees=Decimal("0.00"),
            applied_to_interest=Decimal("33.69"),
            applied_to_principal=Decimal("61.31"),
        )
        self.assertIsNotNone(payment.created_at)
        self.assertIsNotNone(payment.updated_at)

    def test_ordering_is_reverse_paid_at(self) -> None:
        earlier = BhphPayment.objects.create(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
            applied_to_fees=Decimal("0.00"),
            applied_to_interest=Decimal("33.69"),
            applied_to_principal=Decimal("61.31"),
        )
        later = BhphPayment.objects.create(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now() + dt.timedelta(days=7),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_ACH,
            applied_to_fees=Decimal("0.00"),
            applied_to_interest=Decimal("33.43"),
            applied_to_principal=Decimal("61.57"),
        )
        self.assertEqual(list(BhphPayment.objects.all()), [later, earlier])


class BhphPaymentCleanAndCascadeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m122-clean", name="M122 Clean"
        )
        self.other = Dealership.objects.create(
            slug="m122-clean-other", name="M122 Other"
        )
        self.note = _make_note(self.dealership, stock="M122-CLEAN")
        self.cross_note = _make_note(self.other, stock="M122-CLEAN-X")

    def test_clean_rejects_cross_tenant_note(self) -> None:
        payment = BhphPayment(
            dealership=self.dealership,
            note=self.cross_note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
            applied_to_fees=Decimal("0.00"),
            applied_to_interest=Decimal("33.69"),
            applied_to_principal=Decimal("61.31"),
        )
        with self.assertRaises(ValidationError) as ctx:
            payment.clean()
        self.assertIn("note", ctx.exception.message_dict)

    def test_note_delete_cascades(self) -> None:
        payment = BhphPayment.objects.create(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
            applied_to_fees=Decimal("0.00"),
            applied_to_interest=Decimal("33.69"),
            applied_to_principal=Decimal("61.31"),
        )
        self.note.delete()
        self.assertFalse(BhphPayment.objects.filter(pk=payment.pk).exists())


class BhphPaymentVocabTests(TestCase):
    def test_method_vocab_exact_set(self) -> None:
        vocab = {key for key, _ in BHPH_PAYMENT_METHOD_CHOICES}
        self.assertEqual(
            vocab,
            {
                BHPH_PAYMENT_METHOD_CASH,
                BHPH_PAYMENT_METHOD_CHECK,
                BHPH_PAYMENT_METHOD_DEBIT,
                BHPH_PAYMENT_METHOD_ACH,
                BHPH_PAYMENT_METHOD_OTHER,
            },
        )

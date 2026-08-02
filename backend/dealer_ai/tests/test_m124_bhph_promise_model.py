"""Milestone 12 · Increment 4 (SESSION_124) — BhphPromiseToPay model tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_CASH,
    BHPH_PROMISE_REASON_CHOICES,
    BHPH_PROMISE_REASON_FAMILY_HELP,
    BHPH_PROMISE_REASON_OTHER,
    BHPH_PROMISE_REASON_PAYCHECK,
    BHPH_PROMISE_REASON_TAX_REFUND,
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_CHOICES,
    BHPH_PROMISE_STATE_KEPT,
    BHPH_PROMISE_STATE_PROMISED,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
    Dealership,
    Sale,
    Vehicle,
)


def _make_note(dealership: Dealership, stock: str = "M124-1") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Altima",
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


class BhphPromiseDefaultsAndOrderingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m124-def", name="M124 Defaults"
        )
        self.note = _make_note(self.dealership, stock="M124-DEF")

    def test_defaults(self) -> None:
        promise = BhphPromiseToPay.objects.create(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now() + dt.timedelta(days=3),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
        )
        self.assertEqual(promise.state, BHPH_PROMISE_STATE_PROMISED)
        self.assertIsNone(promise.actual_payment)
        self.assertEqual(promise.notes, "")

    def test_ordering_is_reverse_promised_at(self) -> None:
        earlier = BhphPromiseToPay.objects.create(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now(),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
        )
        later = BhphPromiseToPay.objects.create(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now() + dt.timedelta(days=1),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_TAX_REFUND,
        )
        self.assertEqual(
            list(BhphPromiseToPay.objects.all()), [later, earlier]
        )


class BhphPromiseCleanAndCascadeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m124-clean", name="M124 Clean"
        )
        self.other = Dealership.objects.create(
            slug="m124-clean-other", name="M124 Other"
        )
        self.note = _make_note(self.dealership, stock="M124-CLEAN")
        self.cross_note = _make_note(self.other, stock="M124-CLEAN-X")

    def test_clean_rejects_cross_tenant_note(self) -> None:
        promise = BhphPromiseToPay(
            dealership=self.dealership,
            note=self.cross_note,
            promised_at=timezone.now(),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
        )
        with self.assertRaises(ValidationError) as ctx:
            promise.clean()
        self.assertIn("note", ctx.exception.message_dict)

    def test_clean_rejects_cross_tenant_payment(self) -> None:
        cross_payment = BhphPayment.objects.create(
            dealership=self.other,
            note=self.cross_note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
            applied_to_fees=Decimal("0.00"),
            applied_to_interest=Decimal("33.69"),
            applied_to_principal=Decimal("61.31"),
        )
        promise = BhphPromiseToPay(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now(),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
            actual_payment=cross_payment,
        )
        with self.assertRaises(ValidationError) as ctx:
            promise.clean()
        self.assertIn("actual_payment", ctx.exception.message_dict)

    def test_note_delete_cascades(self) -> None:
        promise = BhphPromiseToPay.objects.create(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now(),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
        )
        self.note.delete()
        self.assertFalse(
            BhphPromiseToPay.objects.filter(pk=promise.pk).exists()
        )


class BhphPromiseVocabTests(TestCase):
    def test_reason_vocab_exact_set(self) -> None:
        vocab = {key for key, _ in BHPH_PROMISE_REASON_CHOICES}
        self.assertEqual(
            vocab,
            {
                BHPH_PROMISE_REASON_PAYCHECK,
                BHPH_PROMISE_REASON_TAX_REFUND,
                BHPH_PROMISE_REASON_FAMILY_HELP,
                BHPH_PROMISE_REASON_OTHER,
            },
        )

    def test_state_vocab_exact_set(self) -> None:
        vocab = {key for key, _ in BHPH_PROMISE_STATE_CHOICES}
        self.assertEqual(
            vocab,
            {
                BHPH_PROMISE_STATE_PROMISED,
                BHPH_PROMISE_STATE_KEPT,
                BHPH_PROMISE_STATE_BROKEN,
            },
        )

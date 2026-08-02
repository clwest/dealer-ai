"""Milestone 12 · Increment 4 (SESSION_124) — BhphPromiseToPay service tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_CASH,
    BHPH_PROMISE_REASON_PAYCHECK,
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_KEPT,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_payments import record_payment
from dealer_ai.services.bhph_promises import (
    CrossPromisePaymentError,
    CrossTenantBhphPromiseError,
    PromiseAlreadyTerminalError,
    UnknownReasonError,
    mark_broken,
    mark_kept,
    record_promise,
)


def _make_note(dealership: Dealership, stock: str = "M124-SVC") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Sentra",
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


class RecordPromiseTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m124-svc-rp", name="M124 Svc RP"
        )
        self.other = Dealership.objects.create(
            slug="m124-svc-rp-other", name="M124 Other"
        )
        self.note = _make_note(self.dealership, stock="M124-SVC-RP")
        self.cross_note = _make_note(self.other, stock="M124-SVC-RP-X")

    def test_happy_path(self) -> None:
        promise = record_promise(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now() + dt.timedelta(days=3),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
        )
        self.assertIsInstance(promise, BhphPromiseToPay)
        self.assertEqual(promise.dealership_id, self.dealership.pk)
        self.assertEqual(promise.note_id, self.note.pk)

    def test_cross_tenant_note_raises(self) -> None:
        with self.assertRaises(CrossTenantBhphPromiseError):
            record_promise(
                dealership=self.dealership,
                note=self.cross_note,
                promised_at=timezone.now(),
                promised_amount=Decimal("95.00"),
                promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
            )

    def test_unknown_reason_raises(self) -> None:
        with self.assertRaises(UnknownReasonError):
            record_promise(
                dealership=self.dealership,
                note=self.note,
                promised_at=timezone.now(),
                promised_amount=Decimal("95.00"),
                promised_reason="unemployment_check",
            )


class MarkKeptTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m124-svc-mk", name="M124 Svc MK"
        )
        self.other = Dealership.objects.create(
            slug="m124-svc-mk-other", name="M124 Other"
        )
        self.note = _make_note(self.dealership, stock="M124-SVC-MK")
        self.other_note = _make_note(
            self.dealership, stock="M124-SVC-MK-OTHERNOTE"
        )
        self.cross_note = _make_note(self.other, stock="M124-SVC-MK-X")
        self.promise = record_promise(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now() + dt.timedelta(days=3),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
        )
        self.payment = record_payment(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        self.other_note_payment = record_payment(
            dealership=self.dealership,
            note=self.other_note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        self.cross_payment = record_payment(
            dealership=self.other,
            note=self.cross_note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )

    def test_happy_path_transitions_and_links_payment(self) -> None:
        result = mark_kept(
            dealership=self.dealership,
            promise=self.promise,
            payment=self.payment,
        )
        self.assertEqual(result.state, BHPH_PROMISE_STATE_KEPT)
        self.assertEqual(result.actual_payment_id, self.payment.pk)

    def test_cross_tenant_promise_raises(self) -> None:
        with self.assertRaises(CrossTenantBhphPromiseError):
            mark_kept(
                dealership=self.other,
                promise=self.promise,
                payment=self.payment,
            )

    def test_cross_tenant_payment_raises(self) -> None:
        with self.assertRaises(CrossPromisePaymentError):
            mark_kept(
                dealership=self.dealership,
                promise=self.promise,
                payment=self.cross_payment,
            )

    def test_payment_against_wrong_note_raises(self) -> None:
        with self.assertRaises(CrossPromisePaymentError):
            mark_kept(
                dealership=self.dealership,
                promise=self.promise,
                payment=self.other_note_payment,
            )

    def test_already_terminal_raises(self) -> None:
        mark_kept(
            dealership=self.dealership,
            promise=self.promise,
            payment=self.payment,
        )
        with self.assertRaises(PromiseAlreadyTerminalError):
            mark_kept(
                dealership=self.dealership,
                promise=self.promise,
                payment=self.payment,
            )


class MarkBrokenTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m124-svc-mb", name="M124 Svc MB"
        )
        self.note = _make_note(self.dealership, stock="M124-SVC-MB")
        self.promise = record_promise(
            dealership=self.dealership,
            note=self.note,
            promised_at=timezone.now() + dt.timedelta(days=3),
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
        )

    def test_happy_path(self) -> None:
        result = mark_broken(
            dealership=self.dealership, promise=self.promise
        )
        self.assertEqual(result.state, BHPH_PROMISE_STATE_BROKEN)
        self.assertIsNone(result.actual_payment_id)

    def test_already_terminal_raises(self) -> None:
        mark_broken(dealership=self.dealership, promise=self.promise)
        with self.assertRaises(PromiseAlreadyTerminalError):
            mark_broken(
                dealership=self.dealership, promise=self.promise
            )

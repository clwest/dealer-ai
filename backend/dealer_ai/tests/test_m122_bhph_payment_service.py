"""Milestone 12 · Increment 2 (SESSION_122) — BhphPayment service tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_CASH,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_payments import (
    CrossTenantBhphPaymentError,
    OverpaymentError,
    list_payments,
    record_payment,
)
from dealer_ai.services.bhph_payments.bhph_payment import (
    UnknownPaymentMethodError,
)


def _make_note(
    dealership: Dealership,
    stock: str = "M122-SVC",
    principal: Decimal = Decimal("8000.00"),
) -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Sonata",
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
        apr=Decimal("21.90"),
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=dt.date(2026, 9, 1),
    )


class RecordPaymentHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m122-svc-hp", name="M122 Svc HP"
        )
        self.note = _make_note(self.dealership, stock="M122-SVC-HP")

    def test_first_payment_allocation(self) -> None:
        payment = record_payment(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        # 8000 * 21.9 / 52 / 100 ≈ 33.69 interest.
        self.assertEqual(payment.applied_to_fees, Decimal("0.00"))
        self.assertEqual(payment.applied_to_interest, Decimal("33.69"))
        self.assertEqual(payment.applied_to_principal, Decimal("61.31"))
        self.assertEqual(
            payment.applied_to_fees
            + payment.applied_to_interest
            + payment.applied_to_principal,
            Decimal("95.00"),
        )

    def test_sequential_payments_reduce_balance(self) -> None:
        # First payment.
        p1 = record_payment(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        # Second payment — same amount, but interest should be lower
        # because principal_paid reduces outstanding_balance.
        p2 = record_payment(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now() + dt.timedelta(days=7),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        self.assertLess(
            p2.applied_to_interest, p1.applied_to_interest
        )
        self.assertGreater(
            p2.applied_to_principal, p1.applied_to_principal
        )


class RecordPaymentErrorPathsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m122-svc-err", name="M122 Svc Err"
        )
        self.other = Dealership.objects.create(
            slug="m122-svc-err-other", name="M122 Other"
        )
        self.note = _make_note(self.dealership, stock="M122-SVC-ERR")
        self.cross_note = _make_note(self.other, stock="M122-SVC-ERR-X")

    def test_cross_tenant_note_raises(self) -> None:
        with self.assertRaises(CrossTenantBhphPaymentError):
            record_payment(
                dealership=self.dealership,
                note=self.cross_note,
                paid_at=timezone.now(),
                amount=Decimal("95.00"),
                method=BHPH_PAYMENT_METHOD_CASH,
            )

    def test_unknown_method_raises(self) -> None:
        with self.assertRaises(UnknownPaymentMethodError):
            record_payment(
                dealership=self.dealership,
                note=self.note,
                paid_at=timezone.now(),
                amount=Decimal("95.00"),
                method="crypto",
            )

    def test_overpayment_raises(self) -> None:
        # 999999 payment against 8000 principal + ~34 interest.
        with self.assertRaises(OverpaymentError):
            record_payment(
                dealership=self.dealership,
                note=self.note,
                paid_at=timezone.now(),
                amount=Decimal("99999.99"),
                method=BHPH_PAYMENT_METHOD_CASH,
            )


class ListPaymentsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m122-svc-list", name="M122 Svc List"
        )
        self.other = Dealership.objects.create(
            slug="m122-svc-list-other", name="M122 Other"
        )
        self.note = _make_note(self.dealership, stock="M122-SVC-LIST")
        self.cross_note = _make_note(self.other, stock="M122-SVC-LIST-X")
        # Record two payments on the local note.
        record_payment(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        record_payment(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now() + dt.timedelta(days=7),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )

    def test_returns_all_payments_for_note(self) -> None:
        payments = list_payments(
            dealership=self.dealership, note=self.note
        )
        self.assertEqual(len(payments), 2)

    def test_returns_empty_for_cross_tenant_note(self) -> None:
        payments = list_payments(
            dealership=self.dealership, note=self.cross_note
        )
        self.assertEqual(payments, [])

    def test_returns_empty_for_note_with_no_payments(self) -> None:
        fresh_note = _make_note(self.dealership, stock="M122-SVC-LIST-EMPTY")
        payments = list_payments(
            dealership=self.dealership, note=fresh_note
        )
        self.assertEqual(payments, [])

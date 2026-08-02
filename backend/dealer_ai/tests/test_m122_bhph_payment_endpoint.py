"""Milestone 12 · Increment 2 (SESSION_122) — BhphPayment endpoint tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_CASH,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_payments import record_payment
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CREATE = "dealer_ai:admin-bhph-payment-create"
LIST = "dealer_ai:admin-bhph-payment-list"


def _post(client, url, body):
    return client.post(url, body, format="json")


def _make_note(dealership: Dealership, stock: str = "M122-EP") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Impreza",
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


def _valid_body() -> dict:
    return {
        "paid_at": timezone.now().isoformat(),
        "amount": "95.00",
        "method": BHPH_PAYMENT_METHOD_CASH,
    }


class BhphPaymentCreateAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M122-EP-AUTH")

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_body(),
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="m122-ep-adv")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = _post(
            authenticated_client(user),
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_body(),
        )
        self.assertEqual(response.status_code, 403)


class BhphPaymentCreateHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M122-EP-HP")
        self.user = make_user(username="m122-ep-hp-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_sales_manager_201_and_response_shape(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_body(),
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["bhph_payment"]
        for key in (
            "id",
            "note_id",
            "dealership_id",
            "paid_at",
            "amount",
            "method",
            "applied_to_fees",
            "applied_to_interest",
            "applied_to_principal",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["applied_to_fees"], "0.00")
        self.assertGreater(
            Decimal(body["applied_to_principal"]), Decimal("0.00")
        )


class BhphPaymentCreateErrorMappingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="m122-ep-em-other", name="M122 EP EM Other"
        )
        self.note = _make_note(self.dealership, stock="M122-EP-EM")
        self.cross_note = _make_note(self.other, stock="M122-EP-EM-X")
        self.user = make_user(username="m122-ep-em")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_cross_tenant_note_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE, kwargs={"pk": self.cross_note.pk}),
            _valid_body(),
        )
        self.assertEqual(response.status_code, 404)

    def test_missing_note_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE, kwargs={"pk": 999_999}),
            _valid_body(),
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_method_returns_400(self) -> None:
        body = _valid_body()
        body["method"] = "crypto"
        response = _post(
            self.client, reverse(CREATE, kwargs={"pk": self.note.pk}), body
        )
        # ChoiceField serializer rejects → 400 before verb runs.
        self.assertEqual(response.status_code, 400)

    def test_overpayment_returns_400(self) -> None:
        body = _valid_body()
        body["amount"] = "999999.99"
        response = _post(
            self.client, reverse(CREATE, kwargs={"pk": self.note.pk}), body
        )
        # DecimalField max_digits=8 → serializer 400 before verb.
        self.assertEqual(response.status_code, 400)

    def test_overpayment_within_field_bounds_returns_400_from_verb(
        self,
    ) -> None:
        # Amount fits DecimalField(8,2) but exceeds note balance —
        # OverpaymentError from allocate_payment maps to 400.
        body = _valid_body()
        body["amount"] = "99999.99"
        response = _post(
            self.client, reverse(CREATE, kwargs={"pk": self.note.pk}), body
        )
        self.assertEqual(response.status_code, 400)


class BhphPaymentListTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M122-EP-LIST")
        self.user = make_user(username="m122-ep-list")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        record_payment(
            dealership=self.dealership,
            note=self.note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )

    def test_returns_payments_for_note(self) -> None:
        response = self.client.get(reverse(LIST, kwargs={"pk": self.note.pk}))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(len(payload["results"]), 1)

    def test_missing_note_returns_404(self) -> None:
        response = self.client.get(reverse(LIST, kwargs={"pk": 999_999}))
        self.assertEqual(response.status_code, 404)

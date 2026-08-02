"""Milestone 12 · Increment 1 (SESSION_121) — BhphNote endpoint tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_notes import record_bhph_note
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CREATE = "dealer_ai:admin-bhph-note-create"
RETRIEVE = "dealer_ai:admin-bhph-note-retrieve"


def _post(client, url, body):
    return client.post(url, body, format="json")


def _make_sale(
    dealership: Dealership,
    stock: str = "BHPH-EP",
    finance_type: str = SALE_FINANCE_TYPE_BHPH,
) -> Sale:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Corolla",
        price=Decimal("9500.00"),
        dealership=dealership,
    )
    return Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("9500.00"),
        finance_type=finance_type,
        gross_realized=Decimal("1000.00"),
    )


def _valid_body(sale: Sale) -> dict:
    return {
        "sale_id": sale.pk,
        "principal_financed": "8500.00",
        "apr": "21.90",
        "term_weeks": 130,
        "payment_frequency": BHPH_PAYMENT_FREQUENCY_WEEKLY,
        "first_payment_due": "2026-09-01",
    }


class BhphNoteCreateAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.sale = _make_sale(self.dealership, stock="BHPH-EP-AUTH")
        self.body = _valid_body(self.sale)

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(reverse(CREATE), self.body, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="bhph-ep-adv")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = _post(authenticated_client(user), reverse(CREATE), self.body)
        self.assertEqual(response.status_code, 403)


class BhphNoteCreateHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.sale = _make_sale(self.dealership, stock="BHPH-EP-HP")
        self.user = make_user(username="bhph-ep-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_sales_manager_201_and_response_shape(self) -> None:
        response = _post(self.client, reverse(CREATE), _valid_body(self.sale))
        self.assertEqual(response.status_code, 201)
        body = response.json()["bhph_note"]
        for key in (
            "id",
            "sale_id",
            "dealership_id",
            "principal_financed",
            "apr",
            "term_weeks",
            "payment_frequency",
            "payment_amount",
            "first_payment_due",
            "default_grace_days",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, body)
        # payment_amount populated from amortization — must be > 0.
        self.assertGreater(Decimal(body["payment_amount"]), Decimal("0.00"))


class BhphNoteCreateErrorMappingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="bhph-ep-em-other", name="BHPH EP EM Other"
        )
        self.sale = _make_sale(self.dealership, stock="BHPH-EP-EM")
        self.cross_sale = _make_sale(self.other, stock="BHPH-EP-EM-X")
        self.cash_sale = _make_sale(
            self.dealership,
            stock="BHPH-EP-EM-CASH",
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        self.user = make_user(username="bhph-ep-em")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_cross_tenant_sale_returns_404(self) -> None:
        response = _post(
            self.client, reverse(CREATE), _valid_body(self.cross_sale)
        )
        self.assertEqual(response.status_code, 404)

    def test_non_bhph_sale_returns_400(self) -> None:
        response = _post(
            self.client, reverse(CREATE), _valid_body(self.cash_sale)
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_note_returns_409(self) -> None:
        # First succeeds.
        _post(self.client, reverse(CREATE), _valid_body(self.sale))
        # Second is the duplicate.
        response = _post(
            self.client, reverse(CREATE), _valid_body(self.sale)
        )
        self.assertEqual(response.status_code, 409)

    def test_unknown_frequency_returns_400(self) -> None:
        body = _valid_body(self.sale)
        body["payment_frequency"] = "monthly"
        response = _post(self.client, reverse(CREATE), body)
        # ChoiceField serializer rejects → 400 before verb runs.
        self.assertEqual(response.status_code, 400)

    def test_missing_sale_returns_404(self) -> None:
        body = _valid_body(self.sale)
        body["sale_id"] = 999_999
        response = _post(self.client, reverse(CREATE), body)
        self.assertEqual(response.status_code, 404)


class BhphNoteRetrieveTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="bhph-ep-ret-other", name="BHPH EP Ret Other"
        )
        self.sale = _make_sale(self.dealership, stock="BHPH-EP-RET")
        self.note = record_bhph_note(
            dealership=self.dealership,
            sale=self.sale,
            principal_financed=Decimal("5000.00"),
            apr=Decimal("21.90"),
            term_weeks=52,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            first_payment_due=dt.date(2026, 9, 1),
        )
        self.user = make_user(username="bhph-ep-ret")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_retrieve_returns_note_and_schedule(self) -> None:
        response = self.client.get(reverse(RETRIEVE, kwargs={"pk": self.note.pk}))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["bhph_note"]["id"], self.note.pk)
        # Weekly + term_weeks=52 → 52 scheduled installments.
        self.assertEqual(len(payload["payment_schedule"]), 52)
        first = payload["payment_schedule"][0]
        self.assertEqual(first["due_date"], "2026-09-01")

    def test_retrieve_missing_returns_404(self) -> None:
        response = self.client.get(reverse(RETRIEVE, kwargs={"pk": 999_999}))
        self.assertEqual(response.status_code, 404)

    def test_retrieve_cross_tenant_returns_404(self) -> None:
        # Sanity — a note created in `other` shouldn't leak through
        # the default-dealership session's auth. Using a fresh sale
        # in `other` because the current session lives in
        # `get_default_dealership()`.
        cross_sale = _make_sale(self.other, stock="BHPH-EP-RET-X")
        cross_note = record_bhph_note(
            dealership=self.other,
            sale=cross_sale,
            principal_financed=Decimal("5000.00"),
            apr=Decimal("21.90"),
            term_weeks=52,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            first_payment_due=dt.date(2026, 9, 1),
        )
        response = self.client.get(reverse(RETRIEVE, kwargs={"pk": cross_note.pk}))
        self.assertEqual(response.status_code, 404)

"""Milestone 12 · Increment 4 (SESSION_124) — BhphPromiseToPay endpoint tests."""

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
    BHPH_PROMISE_REASON_PAYCHECK,
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_KEPT,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_payments import record_payment
from dealer_ai.services.bhph_promises import record_promise
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CREATE = "dealer_ai:admin-bhph-promise-create"
LIST = "dealer_ai:admin-bhph-promise-list"
KEPT = "dealer_ai:admin-bhph-promise-mark-kept"
BROKEN = "dealer_ai:admin-bhph-promise-mark-broken"


def _post(client, url, body):
    return client.post(url, body, format="json")


def _make_note(dealership: Dealership, stock: str = "M124-EP") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Corolla",
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


def _valid_create_body() -> dict:
    return {
        "promised_at": (
            timezone.now() + dt.timedelta(days=3)
        ).isoformat(),
        "promised_amount": "95.00",
        "promised_reason": BHPH_PROMISE_REASON_PAYCHECK,
    }


class PromiseCreateAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M124-EP-AUTH")

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_create_body(),
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="m124-ep-adv")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = _post(
            authenticated_client(user),
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_create_body(),
        )
        self.assertEqual(response.status_code, 403)


class PromiseCreateHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M124-EP-HP")
        self.user = make_user(username="m124-ep-hp")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_sales_manager_201_and_response_shape(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_create_body(),
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["bhph_promise"]
        for key in (
            "id",
            "note_id",
            "dealership_id",
            "promised_at",
            "promised_amount",
            "promised_reason",
            "actual_payment_id",
            "state",
            "notes",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["state"], "promised")
        self.assertIsNone(body["actual_payment_id"])


class PromiseCreateErrorMappingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="m124-ep-em-other", name="M124 EP EM Other"
        )
        self.note = _make_note(self.dealership, stock="M124-EP-EM")
        self.cross_note = _make_note(self.other, stock="M124-EP-EM-X")
        self.user = make_user(username="m124-ep-em")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_cross_tenant_note_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE, kwargs={"pk": self.cross_note.pk}),
            _valid_create_body(),
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_reason_returns_400(self) -> None:
        body = _valid_create_body()
        body["promised_reason"] = "unemployment_check"
        response = _post(
            self.client, reverse(CREATE, kwargs={"pk": self.note.pk}), body
        )
        self.assertEqual(response.status_code, 400)


class PromiseTransitionEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M124-EP-TRANS")
        self.user = make_user(username="m124-ep-trans")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
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

    def test_mark_kept_happy_returns_200_with_payment_link(self) -> None:
        response = _post(
            self.client,
            reverse(KEPT, kwargs={"pk": self.promise.pk}),
            {"bhph_payment_id": self.payment.pk},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["bhph_promise"]
        self.assertEqual(body["state"], BHPH_PROMISE_STATE_KEPT)
        self.assertEqual(body["actual_payment_id"], self.payment.pk)

    def test_mark_broken_happy(self) -> None:
        response = _post(
            self.client,
            reverse(BROKEN, kwargs={"pk": self.promise.pk}),
            {"notes": "customer no longer answering"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["bhph_promise"]
        self.assertEqual(body["state"], BHPH_PROMISE_STATE_BROKEN)
        self.assertIsNone(body["actual_payment_id"])

    def test_re_transition_after_terminal_returns_409(self) -> None:
        _post(
            self.client,
            reverse(BROKEN, kwargs={"pk": self.promise.pk}),
            {},
        )
        response = _post(
            self.client,
            reverse(BROKEN, kwargs={"pk": self.promise.pk}),
            {},
        )
        self.assertEqual(response.status_code, 409)

    def test_nonexistent_promise_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(BROKEN, kwargs={"pk": 999_999}),
            {},
        )
        self.assertEqual(response.status_code, 404)

    def test_mark_kept_with_nonexistent_payment_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(KEPT, kwargs={"pk": self.promise.pk}),
            {"bhph_payment_id": 999_999},
        )
        self.assertEqual(response.status_code, 404)


class PromiseListEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M124-EP-LIST")
        self.user = make_user(username="m124-ep-list")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        for _ in range(2):
            record_promise(
                dealership=self.dealership,
                note=self.note,
                promised_at=timezone.now() + dt.timedelta(days=3),
                promised_amount=Decimal("95.00"),
                promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
            )

    def test_list_returns_promises_for_note(self) -> None:
        response = self.client.get(
            reverse(LIST, kwargs={"pk": self.note.pk})
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(len(payload["results"]), 2)

    def test_list_missing_note_returns_404(self) -> None:
        response = self.client.get(reverse(LIST, kwargs={"pk": 999_999}))
        self.assertEqual(response.status_code, 404)

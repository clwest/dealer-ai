"""Milestone 12 · Increment 5 (SESSION_125) — CollectionContact endpoint tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    BHPH_CONTACT_CHANNEL_PHONE,
    BHPH_CONTACT_OUTCOME_CONTACT_MADE,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.collection_contacts import record_contact
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CREATE = "dealer_ai:admin-collection-contact-create"
LIST = "dealer_ai:admin-collection-contact-list"


def _post(client, url, body):
    return client.post(url, body, format="json")


def _make_note(dealership: Dealership, stock: str = "M125-EP") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Mazda3",
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
        "contacted_at": timezone.now().isoformat(),
        "channel": BHPH_CONTACT_CHANNEL_PHONE,
        "outcome": BHPH_CONTACT_OUTCOME_CONTACT_MADE,
    }


class ContactCreateAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M125-EP-AUTH")

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_body(),
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="m125-ep-adv")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = _post(
            authenticated_client(user),
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_body(),
        )
        self.assertEqual(response.status_code, 403)


class ContactCreateHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M125-EP-HP")
        self.user = make_user(username="m125-ep-hp")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_sales_manager_201_and_response_shape(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_body(),
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["collection_contact"]
        for key in (
            "id",
            "note_id",
            "dealership_id",
            "contacted_at",
            "contacted_by_user_id",
            "channel",
            "outcome",
            "notes",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["channel"], BHPH_CONTACT_CHANNEL_PHONE)
        # Endpoint records the calling user as contacted_by_user.
        self.assertEqual(body["contacted_by_user_id"], self.user.pk)


class ContactCreateErrorMappingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="m125-ep-em-other", name="M125 EP EM Other"
        )
        self.note = _make_note(self.dealership, stock="M125-EP-EM")
        self.cross_note = _make_note(self.other, stock="M125-EP-EM-X")
        self.user = make_user(username="m125-ep-em")
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

    def test_invalid_channel_returns_400(self) -> None:
        body = _valid_body()
        body["channel"] = "morse_code"
        response = _post(
            self.client, reverse(CREATE, kwargs={"pk": self.note.pk}), body
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_outcome_returns_400(self) -> None:
        body = _valid_body()
        body["outcome"] = "confused_hangup"
        response = _post(
            self.client, reverse(CREATE, kwargs={"pk": self.note.pk}), body
        )
        self.assertEqual(response.status_code, 400)


class ContactListEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M125-EP-LIST")
        self.user = make_user(username="m125-ep-list")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        for _ in range(2):
            record_contact(
                dealership=self.dealership,
                note=self.note,
                contacted_at=timezone.now(),
                channel=BHPH_CONTACT_CHANNEL_PHONE,
                outcome=BHPH_CONTACT_OUTCOME_CONTACT_MADE,
            )

    def test_list_returns_contacts_for_note(self) -> None:
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

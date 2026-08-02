"""Milestone 12 · Increment 6 (SESSION_126) — Repossession endpoint tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_REPO_STATE_RE_INTAKED,
    BHPH_REPO_STATE_RECOVERED,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    ConditionReport,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.repossessions import (
    mark_recovered,
    record_repossession,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CREATE = "dealer_ai:admin-repossession-create"
LIST = "dealer_ai:admin-repossession-list"
RECOVERED = "dealer_ai:admin-repossession-mark-recovered"
RE_INTAKED = "dealer_ai:admin-repossession-mark-re-intaked"


def _post(client, url, body):
    return client.post(url, body, format="json")


def _make_note(dealership: Dealership, stock: str = "M126-EP") -> BhphNote:
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


def _make_condition_report(
    dealership: Dealership, vehicle: Vehicle
) -> ConditionReport:
    return ConditionReport.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        inspector_name="Post-Repo",
        inspected_at=timezone.now(),
        mileage_at_inspection=52000,
    )


def _valid_create_body() -> dict:
    return {
        "ordered_at": timezone.now().isoformat(),
        "agent_name": "Ace Recovery",
    }


class RepossessionCreateAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M126-EP-AUTH")

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_create_body(),
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="m126-ep-adv")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = _post(
            authenticated_client(user),
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_create_body(),
        )
        self.assertEqual(response.status_code, 403)


class RepossessionCreateHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M126-EP-HP")
        self.user = make_user(username="m126-ep-hp")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_201_and_response_shape(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE, kwargs={"pk": self.note.pk}),
            _valid_create_body(),
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["repossession"]
        for key in (
            "id",
            "note_id",
            "dealership_id",
            "ordered_at",
            "ordered_by_user_id",
            "agent_name",
            "recovered_at",
            "recovery_location",
            "intake_condition_report_id",
            "state",
            "notes",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["state"], "ordered")
        self.assertEqual(body["ordered_by_user_id"], self.user.pk)
        self.assertIsNone(body["recovered_at"])


class RepossessionTransitionTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M126-EP-TRANS")
        self.vehicle = Vehicle.objects.get(stock_number="M126-EP-TRANS")
        self.report = _make_condition_report(self.dealership, self.vehicle)
        self.user = make_user(username="m126-ep-trans")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.repo = record_repossession(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Ace",
        )

    def test_mark_recovered_happy(self) -> None:
        response = _post(
            self.client,
            reverse(RECOVERED, kwargs={"pk": self.repo.pk}),
            {"recovery_location": "Owner residence"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["repossession"]
        self.assertEqual(body["state"], BHPH_REPO_STATE_RECOVERED)
        self.assertIsNotNone(body["recovered_at"])
        self.assertEqual(body["recovery_location"], "Owner residence")

    def test_mark_re_intaked_after_recovered_happy(self) -> None:
        mark_recovered(
            dealership=self.dealership, repossession=self.repo
        )
        response = _post(
            self.client,
            reverse(RE_INTAKED, kwargs={"pk": self.repo.pk}),
            {"condition_report_id": self.report.pk},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["repossession"]
        self.assertEqual(body["state"], BHPH_REPO_STATE_RE_INTAKED)
        self.assertEqual(
            body["intake_condition_report_id"], self.report.pk
        )

    def test_mark_re_intaked_before_recovered_returns_409(self) -> None:
        response = _post(
            self.client,
            reverse(RE_INTAKED, kwargs={"pk": self.repo.pk}),
            {"condition_report_id": self.report.pk},
        )
        self.assertEqual(response.status_code, 409)

    def test_missing_condition_report_returns_404(self) -> None:
        mark_recovered(
            dealership=self.dealership, repossession=self.repo
        )
        response = _post(
            self.client,
            reverse(RE_INTAKED, kwargs={"pk": self.repo.pk}),
            {"condition_report_id": 999_999},
        )
        self.assertEqual(response.status_code, 404)

    def test_missing_repossession_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(RECOVERED, kwargs={"pk": 999_999}),
            {},
        )
        self.assertEqual(response.status_code, 404)


class RepossessionListTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.note = _make_note(self.dealership, stock="M126-EP-LIST")
        self.user = make_user(username="m126-ep-list")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        for _ in range(2):
            record_repossession(
                dealership=self.dealership,
                note=self.note,
                ordered_at=timezone.now(),
                agent_name="Ace",
            )

    def test_list_returns_repos_for_note(self) -> None:
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


class RepossessionCrossTenantEndpointTests(TestCase):
    def test_cross_tenant_note_returns_404(self) -> None:
        dealership = get_default_dealership()
        other = Dealership.objects.create(
            slug="m126-ep-x-other", name="M126 X Other"
        )
        cross_note = _make_note(other, stock="M126-EP-X")
        user = make_user(username="m126-ep-x")
        make_membership(user, dealership, ROLE_SALES_MANAGER)
        response = _post(
            authenticated_client(user),
            reverse(CREATE, kwargs={"pk": cross_note.pk}),
            _valid_create_body(),
        )
        self.assertEqual(response.status_code, 404)

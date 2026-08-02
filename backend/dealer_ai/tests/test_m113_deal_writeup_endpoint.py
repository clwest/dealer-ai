"""Milestone 11 · Increment 3 (SESSION_116) — DealWriteup endpoint tests.

Locks the HTTP surface of the three
:mod:`views_deal_writeups` endpoints per
``MILESTONE_11_PLANNING.md`` §7 M11.3 + §1.9.

Coverage:

- Auth gates on create (unauth / no membership / advisor /
  f_and_i_manager forbidden).
- 201 create + response shape under sales_manager and dealer_owner.
- Cross-tenant lead / vehicle → 404 on create.
- Approve happy path → 200; nonexistent → 404.
- Handoff pre-approval → 409; happy path → 201 with CA in body;
  re-handoff → 409.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_SALES_MANAGER,
    CreditApplication,
    CustomerLead,
    Dealership,
    DealWriteup,
    Vehicle,
)
from dealer_ai.services.deal_writeups import (
    approve_deal_writeup,
    record_deal_writeup,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CREATE_ENDPOINT = "dealer_ai:admin-deal-writeup-create"
APPROVE_ENDPOINT = "dealer_ai:admin-deal-writeup-approve"
HANDOFF_ENDPOINT = "dealer_ai:admin-deal-writeup-hand-off"


def _post(client, url, body):
    return client.post(url, body, format="json")


def _make_vehicle(dealership: Dealership, stock: str = "EP-DW-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("38500.00"),
        dealership=dealership,
    )


class DealWriteupCreateAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Auth Lead"
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.body = {"lead_id": self.lead.pk, "vehicle_id": self.vehicle.pk}

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(
            reverse(CREATE_ENDPOINT), self.body, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_no_membership_returns_403(self) -> None:
        user = make_user(username="dw-nomem")
        response = _post(
            authenticated_client(user), reverse(CREATE_ENDPOINT), self.body
        )
        self.assertEqual(response.status_code, 403)

    def _role_forbidden(self, role: str) -> None:
        user = make_user(username=f"dw-{role}")
        make_membership(user, self.dealership, role)
        response = _post(
            authenticated_client(user), reverse(CREATE_ENDPOINT), self.body
        )
        self.assertEqual(response.status_code, 403)

    def test_advisor_forbidden(self) -> None:
        self._role_forbidden(ROLE_ADVISOR)

    def test_f_and_i_manager_forbidden(self) -> None:
        self._role_forbidden(ROLE_F_AND_I_MANAGER)


class DealWriteupCreateHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Happy Lead"
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.user = make_user(username="dw-hp-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_sales_manager_201_and_response_shape(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE_ENDPOINT),
            {
                "lead_id": self.lead.pk,
                "vehicle_id": self.vehicle.pk,
                "vehicle_price": "28995.00",
                "monthly_payment_target": "450.00",
                "term_months_target": 72,
                "apr_target": "7.49",
                "notes": "Test writeup",
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["deal_writeup"]
        for key in (
            "id",
            "lead_id",
            "vehicle_id",
            "dealership_id",
            "vehicle_price",
            "monthly_payment_target",
            "term_months_target",
            "apr_target",
            "write_up_at",
            "written_up_by_user_id",
            "sales_manager_approved_at",
            "handed_off_to_fandi_at",
            "notes",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["lead_id"], self.lead.pk)
        self.assertEqual(body["written_up_by_user_id"], self.user.id)
        self.assertIsNone(body["sales_manager_approved_at"])
        self.assertIsNone(body["handed_off_to_fandi_at"])

    def test_dealer_owner_201(self) -> None:
        owner = make_user(username="dw-hp-owner")
        make_membership(owner, self.dealership, ROLE_DEALER_OWNER)
        response = _post(
            authenticated_client(owner),
            reverse(CREATE_ENDPOINT),
            {"lead_id": self.lead.pk, "vehicle_id": self.vehicle.pk},
        )
        self.assertEqual(response.status_code, 201)


class DealWriteupCreateErrorMappingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="dw-em-other", name="DW EM Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Local"
        )
        self.vehicle = _make_vehicle(self.dealership, "EP-DW-EM-1")
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross"
        )
        self.cross_vehicle = _make_vehicle(self.other, "EP-DW-EM-2")
        self.user = make_user(username="dw-em-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_missing_lead_id_returns_400(self) -> None:
        response = _post(
            self.client, reverse(CREATE_ENDPOINT), {"vehicle_id": self.vehicle.pk}
        )
        self.assertEqual(response.status_code, 400)

    def test_cross_tenant_lead_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE_ENDPOINT),
            {"lead_id": self.cross_lead.pk, "vehicle_id": self.vehicle.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_vehicle_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE_ENDPOINT),
            {"lead_id": self.lead.pk, "vehicle_id": self.cross_vehicle.pk},
        )
        self.assertEqual(response.status_code, 404)


class DealWriteupApproveEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Approve Lead"
        )
        self.vehicle = _make_vehicle(self.dealership, "EP-DW-AP-1")
        self.user = make_user(username="dw-ap-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.writeup = record_deal_writeup(
            dealership=self.dealership, lead=self.lead, vehicle=self.vehicle
        )

    def test_approve_happy_path(self) -> None:
        response = _post(
            self.client,
            reverse(APPROVE_ENDPOINT, kwargs={"pk": self.writeup.pk}),
            {},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["deal_writeup"]
        self.assertIsNotNone(body["sales_manager_approved_at"])
        self.assertEqual(body["sales_manager_approved_by_user_id"], self.user.id)

    def test_approve_nonexistent_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(APPROVE_ENDPOINT, kwargs={"pk": 999_999}),
            {},
        )
        self.assertEqual(response.status_code, 404)


class DealWriteupHandoffEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Handoff Hank"
        )
        self.vehicle = _make_vehicle(self.dealership, "EP-DW-HO-1")
        self.user = make_user(username="dw-ho-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.writeup = record_deal_writeup(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            vehicle_price=Decimal("28000.00"),
            monthly_payment_target=Decimal("450.00"),
        )

    def _approve(self):
        approve_deal_writeup(writeup=self.writeup, approved_by_user=self.user)
        self.writeup.refresh_from_db()

    def test_handoff_before_approval_returns_409(self) -> None:
        response = _post(
            self.client,
            reverse(HANDOFF_ENDPOINT, kwargs={"pk": self.writeup.pk}),
            {},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            CreditApplication.objects.filter(dealership=self.dealership).count(),
            0,
        )

    def test_handoff_happy_path_creates_ca(self) -> None:
        self._approve()
        response = _post(
            self.client,
            reverse(HANDOFF_ENDPOINT, kwargs={"pk": self.writeup.pk}),
            {},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIn("deal_writeup", body)
        self.assertIn("credit_application", body)
        ca = body["credit_application"]
        self.assertEqual(ca["lead_id"], self.lead.pk)
        # Writeup now has handoff timestamp.
        self.assertIsNotNone(body["deal_writeup"]["handed_off_to_fandi_at"])
        # CA row was persisted for real.
        self.assertEqual(
            CreditApplication.objects.filter(dealership=self.dealership).count(),
            1,
        )

    def test_re_handoff_returns_409(self) -> None:
        self._approve()
        _post(
            self.client,
            reverse(HANDOFF_ENDPOINT, kwargs={"pk": self.writeup.pk}),
            {},
        )
        response = _post(
            self.client,
            reverse(HANDOFF_ENDPOINT, kwargs={"pk": self.writeup.pk}),
            {},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            CreditApplication.objects.filter(dealership=self.dealership).count(),
            1,
        )

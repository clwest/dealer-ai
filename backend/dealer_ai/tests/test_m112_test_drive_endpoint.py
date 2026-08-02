"""Milestone 11 · Increment 2 (SESSION_115) — TestDrive endpoint tests.

Locks :func:`views_test_drives.admin_test_drive_create` per
``MILESTONE_11_PLANNING.md`` §1.2 + §5.c + §7 M11.2 + §1.9.

Coverage:

- Unauthenticated → 401 / 403.
- Authenticated with no dealership membership → 403.
- Authenticated with disallowed role (advisor / f_and_i_manager) →
  403.
- Authenticated with allowed role (sales_manager / dealer_owner) →
  201 on success.
- Missing lead_id / vehicle_id → 400 (serializer validation).
- Cross-tenant lead_id → 404 (fail-closed).
- Cross-tenant vehicle_id → 404 (fail-closed).
- Nonexistent lead_id → 404.
- ``driven_by_user`` auto-populated from request.user.
- Response shape assertion.
"""

from __future__ import annotations

import datetime as dt
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
    CustomerLead,
    Dealership,
    TestDrive,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


ENDPOINT = "dealer_ai:admin-test-drive-create"


def _post(client, body):
    return client.post(reverse(ENDPOINT), body, format="json")


def _make_vehicle(dealership: Dealership, stock: str = "EP-TD-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("38500.00"),
        dealership=dealership,
    )


class TestDriveEndpointAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Ep Lead"
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.body = {
            "lead_id": self.lead.pk,
            "vehicle_id": self.vehicle.pk,
        }

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(reverse(ENDPOINT), self.body, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_no_membership_returns_403(self) -> None:
        user = make_user(username="td-nomem")
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 403)

    def _role_forbidden(self, role: str) -> None:
        user = make_user(username=f"td-{role}")
        make_membership(user, self.dealership, role)
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 403)

    def test_advisor_forbidden(self) -> None:
        self._role_forbidden(ROLE_ADVISOR)

    def test_f_and_i_manager_forbidden(self) -> None:
        self._role_forbidden(ROLE_F_AND_I_MANAGER)


class TestDriveEndpointHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Happy Hank"
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.user = make_user(username="td-hp-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_sales_manager_201_and_response_shape(self) -> None:
        when = timezone.now() - dt.timedelta(minutes=30)
        response = _post(
            self.client,
            {
                "lead_id": self.lead.pk,
                "vehicle_id": self.vehicle.pk,
                "driven_at": when.isoformat(),
                "duration_minutes": 25,
                "route_notes": "Loop",
                "customer_reaction": "Positive",
                "objections_captured": ["Wants leather"],
                "next_action": "Send pricing",
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        drive = body["test_drive"]
        for key in (
            "id",
            "lead_id",
            "vehicle_id",
            "dealership_id",
            "driven_by_user_id",
            "driven_at",
            "duration_minutes",
            "route_notes",
            "customer_reaction",
            "objections_captured",
            "next_action",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, drive)
        self.assertEqual(drive["lead_id"], self.lead.pk)
        self.assertEqual(drive["vehicle_id"], self.vehicle.pk)
        self.assertEqual(drive["dealership_id"], self.dealership.id)
        self.assertEqual(drive["driven_by_user_id"], self.user.id)
        self.assertEqual(drive["duration_minutes"], 25)
        self.assertEqual(drive["objections_captured"], ["Wants leather"])

    def test_dealer_owner_201(self) -> None:
        owner = make_user(username="td-hp-owner")
        make_membership(owner, self.dealership, ROLE_DEALER_OWNER)
        response = _post(
            authenticated_client(owner),
            {"lead_id": self.lead.pk, "vehicle_id": self.vehicle.pk},
        )
        self.assertEqual(response.status_code, 201)


class TestDriveEndpointErrorMappingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="td-em-other", name="TD EM Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Local"
        )
        self.vehicle = _make_vehicle(self.dealership, "EP-EM-1")
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross"
        )
        self.cross_vehicle = _make_vehicle(self.other, "EP-EM-2")
        self.user = make_user(username="td-em-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_missing_lead_id_returns_400(self) -> None:
        response = _post(self.client, {"vehicle_id": self.vehicle.pk})
        self.assertEqual(response.status_code, 400)

    def test_missing_vehicle_id_returns_400(self) -> None:
        response = _post(self.client, {"lead_id": self.lead.pk})
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_lead_returns_404(self) -> None:
        response = _post(
            self.client,
            {"lead_id": 999_999, "vehicle_id": self.vehicle.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_lead_returns_404(self) -> None:
        response = _post(
            self.client,
            {"lead_id": self.cross_lead.pk, "vehicle_id": self.vehicle.pk},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            TestDrive.objects.filter(dealership=self.dealership).count(), 0
        )

    def test_cross_tenant_vehicle_returns_404(self) -> None:
        response = _post(
            self.client,
            {"lead_id": self.lead.pk, "vehicle_id": self.cross_vehicle.pk},
        )
        self.assertEqual(response.status_code, 404)

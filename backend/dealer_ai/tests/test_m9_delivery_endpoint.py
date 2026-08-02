"""Milestone 9 · Increment 2 (SESSION_101) — Delivery endpoint tests.

Locks the HTTP surface of
:func:`views_delivery.admin_delivery_create` and
:func:`views_delivery.admin_delivery_update` per
``MILESTONE_9_PLANNING.md`` §1.2 + §5.d.

Coverage:

- Unauthenticated → 401/403.
- Disallowed role → 403.
- POST 201 create.
- POST 404 unknown vehicle / cross-tenant vehicle.
- POST 409 when Vehicle has no Sale
  (`SaleNotFoundForDeliveryError`).
- POST 409 when Delivery already exists for the Sale.
- PATCH 200 update column fields.
- PATCH 200 toggle checklist item.
- PATCH 200 verify insurance (column + key + timestamp).
- PATCH 400 unknown checklist key.
- PATCH 400 checklist_key without checklist_value.
- PATCH 404 unknown / cross-tenant delivery.
- Response shape correct (checklist as dict, dates as ISO strings).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import (
    DELIVERY_CHECKLIST_FUELED,
    DELIVERY_CHECKLIST_INSURANCE_VERIFIED,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_CASH,
    Delivery,
    Sale,
    Vehicle,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


CREATE_URL = "dealer_ai:admin-delivery-create"
UPDATE_URL = "dealer_ai:admin-delivery-update"


def _seed_vehicle_with_sale(
    dealership, *, stock: str = "EP-1"
) -> tuple[Vehicle, Sale]:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28000.00"),
        dealership=dealership,
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("32000.00"),
        finance_type=SALE_FINANCE_TYPE_CASH,
        gross_realized=Decimal("3500.00"),
    )
    return vehicle, sale


class DeliveryEndpointAuthTests(TestCase):

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m92-ep-auth")
        self.vehicle, _sale = _seed_vehicle_with_sale(self.dealership)
        self.url = reverse(CREATE_URL, args=[self.vehicle.stock_number])

    def test_unauthenticated_forbidden(self) -> None:
        client = APIClient()
        response = client.post(self.url, {}, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_role_forbidden(self) -> None:
        user = make_user(username="del-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_dealer_owner_can_post(self) -> None:
        user = make_user(username="del-owner")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        client = authenticated_client(user)
        response = client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 201)


class DeliveryCreateBehaviorTests(TestCase):

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m92-ep-create")
        self.user = make_user(username="ep-create")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle, self.sale = _seed_vehicle_with_sale(self.dealership)
        self.url = reverse(CREATE_URL, args=[self.vehicle.stock_number])

    def test_success_returns_delivery_projection(self) -> None:
        response = self.client.post(
            self.url,
            {
                "delivery_date": "2026-08-05",
                "temp_tag_number": "AZ-123",
                "notes": "Weekend pickup.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIn("delivery", body)
        delivery = body["delivery"]
        self.assertEqual(delivery["sale_id"], self.sale.pk)
        self.assertEqual(delivery["vehicle_stock"], self.vehicle.stock_number)
        self.assertEqual(delivery["delivery_date"], "2026-08-05")
        self.assertEqual(delivery["temp_tag_number"], "AZ-123")
        self.assertFalse(delivery["insurance_verified"])
        # Checklist dict shipped with all keys defaulted False.
        self.assertIsInstance(delivery["checklist"], dict)
        self.assertFalse(delivery["checklist"][DELIVERY_CHECKLIST_FUELED])

    def test_success_without_optional_fields(self) -> None:
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIsNone(body["delivery"]["delivery_date"])

    def test_404_unknown_vehicle(self) -> None:
        url = reverse(CREATE_URL, args=["DOES-NOT-EXIST"])
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_409_when_vehicle_has_no_sale(self) -> None:
        # Vehicle exists but no Sale row — the workflow-ordering
        # check surfaces as 409, not 404 (vehicle isn't missing).
        v = Vehicle.objects.create(
            stock_number="NO-SALE",
            year=2024,
            model="Ranger",
            price=Decimal("28000.00"),
            dealership=self.dealership,
        )
        url = reverse(CREATE_URL, args=[v.stock_number])
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 409)

    def test_409_on_duplicate_delivery(self) -> None:
        r1 = self.client.post(self.url, {}, format="json")
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post(self.url, {}, format="json")
        self.assertEqual(r2.status_code, 409)


class DeliveryPatchBehaviorTests(TestCase):

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m92-ep-patch")
        self.user = make_user(username="ep-patch")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle, self.sale = _seed_vehicle_with_sale(self.dealership)
        create_response = self.client.post(
            reverse(CREATE_URL, args=[self.vehicle.stock_number]),
            {},
            format="json",
        )
        assert create_response.status_code == 201
        self.delivery_id = create_response.json()["delivery"]["id"]
        self.url = reverse(UPDATE_URL, args=[self.delivery_id])

    def test_update_column_fields(self) -> None:
        response = self.client.patch(
            self.url,
            {
                "delivery_date": "2026-08-05",
                "temp_tag_number": "AZ-999",
                "notes": "Rescheduled.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["delivery"]
        self.assertEqual(body["delivery_date"], "2026-08-05")
        self.assertEqual(body["temp_tag_number"], "AZ-999")
        self.assertEqual(body["notes"], "Rescheduled.")

    def test_toggle_checklist_item(self) -> None:
        response = self.client.patch(
            self.url,
            {
                "checklist_key": DELIVERY_CHECKLIST_FUELED,
                "checklist_value": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["delivery"]
        self.assertTrue(body["checklist"][DELIVERY_CHECKLIST_FUELED])

    def test_verify_insurance_via_patch(self) -> None:
        response = self.client.patch(
            self.url,
            {"verify_insurance": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["delivery"]
        self.assertTrue(body["insurance_verified"])
        self.assertIsNotNone(body["insurance_verified_at"])
        self.assertTrue(
            body["checklist"][DELIVERY_CHECKLIST_INSURANCE_VERIFIED]
        )

    def test_400_unknown_checklist_key(self) -> None:
        # DRF ChoiceField will reject unknown values at serializer
        # validation → 400 with a serializer-shape body.
        response = self.client.patch(
            self.url,
            {
                "checklist_key": "not_a_real_key",
                "checklist_value": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_400_when_checklist_key_without_value(self) -> None:
        response = self.client.patch(
            self.url,
            {"checklist_key": DELIVERY_CHECKLIST_FUELED},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_400_direct_insurance_checklist_toggle_rejected(self) -> None:
        # The ChoiceField accepts the key (it IS in the vocabulary),
        # but the service verb refuses direct toggling — surfaces as
        # 400 via UnknownChecklistKeyError mapping.
        response = self.client.patch(
            self.url,
            {
                "checklist_key": DELIVERY_CHECKLIST_INSURANCE_VERIFIED,
                "checklist_value": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_404_unknown_delivery(self) -> None:
        url = reverse(UPDATE_URL, args=[999_999])
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, 404)


class DeliveryCrossTenantEndpointTests(TestCase):
    """Tenant B's vehicle/delivery must be invisible to tenant A's caller."""

    def setUp(self) -> None:
        self.tenant_a = make_dealership(slug="m92-ep-xt-a")
        self.tenant_b = make_dealership(slug="m92-ep-xt-b")
        self.vehicle_b, self.sale_b = _seed_vehicle_with_sale(
            self.tenant_b, stock="B-XT-1"
        )
        self.delivery_b = Delivery.objects.create(
            dealership=self.tenant_b, sale=self.sale_b
        )

        self.user_a = make_user(username="ep-xt-user-a")
        make_membership(self.user_a, self.tenant_a, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(self.user_a)

    def test_cross_tenant_vehicle_returns_404(self) -> None:
        url = reverse(CREATE_URL, args=[self.vehicle_b.stock_number])
        response = self.client_a.post(url, {}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_delivery_returns_404_on_patch(self) -> None:
        url = reverse(UPDATE_URL, args=[self.delivery_b.pk])
        response = self.client_a.patch(url, {}, format="json")
        self.assertEqual(response.status_code, 404)

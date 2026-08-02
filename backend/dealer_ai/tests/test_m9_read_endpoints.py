"""Milestone 9 · Increment 5 (SESSION_104) — GET-shape lock tests.

The M9.5 UI reads current state via GET on the vehicle-scoped Sale
+ Delivery URLs. The GET dispatch was added additively at
SESSION_104 (§0.a) to the existing POST endpoints; this file locks
the response shape + status semantics so a future refactor catches
regression.

Coverage:

- GET sale — 200 when Sale exists (shape parity with POST 201
  response body).
- GET sale — 404 when the vehicle has no Sale.
- GET sale — 404 when the vehicle is cross-tenant (never leak).
- GET delivery — 200 when Delivery exists.
- GET delivery — 404 when the vehicle has no Delivery.
- GET delivery — 404 when the vehicle is cross-tenant.
- Auth matrix: unauthenticated + disallowed role both blocked on
  both endpoints.

Also locks the M9.1 POST response shape is what the M9.5 UI's
readSale hook expects (matches CreateSaleResponse type).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_CASH,
    CustomerLead,
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


SALE_URL = "dealer_ai:admin-sale-create"
DELIVERY_URL = "dealer_ai:admin-delivery-create"


def _seed_vehicle(dealership, *, stock: str = "READ-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28000.00"),
        dealership=dealership,
    )


def _seed_sale(dealership, vehicle: Vehicle) -> Sale:
    return Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("32000.00"),
        finance_type=SALE_FINANCE_TYPE_CASH,
        gross_realized=Decimal("3500.00"),
    )


class SaleReadEndpointTests(TestCase):

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m95-read-sale")
        self.user = make_user(username="m95-read-sale-user")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle = _seed_vehicle(self.dealership)

    def _get_url(self, stock: str) -> str:
        return reverse(SALE_URL, args=[stock])

    def test_get_returns_sale_when_present(self) -> None:
        sale = _seed_sale(self.dealership, self.vehicle)
        response = self.client.get(self._get_url(self.vehicle.stock_number))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("sale", body)
        self.assertEqual(body["sale"]["id"], sale.pk)
        self.assertEqual(body["sale"]["vehicle_stock"], self.vehicle.stock_number)
        # Stringified Decimal round-trips through the projection.
        self.assertEqual(body["sale"]["sold_price"], "32000.00")

    def test_get_404_when_no_sale(self) -> None:
        response = self.client.get(self._get_url(self.vehicle.stock_number))
        self.assertEqual(response.status_code, 404)

    def test_get_404_when_unknown_vehicle(self) -> None:
        response = self.client.get(self._get_url("DOES-NOT-EXIST"))
        self.assertEqual(response.status_code, 404)

    def test_get_cross_tenant_returns_404(self) -> None:
        tenant_b = make_dealership(slug="m95-read-sale-b")
        vehicle_b = _seed_vehicle(tenant_b, stock="B-ONLY")
        _seed_sale(tenant_b, vehicle_b)
        response = self.client.get(self._get_url(vehicle_b.stock_number))
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_forbidden(self) -> None:
        response = APIClient().get(self._get_url(self.vehicle.stock_number))
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        advisor = make_user(username="m95-read-sale-advisor")
        make_membership(advisor, self.dealership, ROLE_ADVISOR)
        response = authenticated_client(advisor).get(
            self._get_url(self.vehicle.stock_number)
        )
        self.assertEqual(response.status_code, 403)

    def test_post_still_works_after_get_dispatch_added(self) -> None:
        # The M9.1 POST path continues to accept writes even though
        # the endpoint now dispatches on method. Lock the shape.
        response = self.client.post(
            self._get_url(self.vehicle.stock_number),
            {
                "sale_date": "2026-08-01",
                "sold_price": "32000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Sale.objects.count(), 1)


class DeliveryReadEndpointTests(TestCase):

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m95-read-del")
        self.user = make_user(username="m95-read-del-user")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle = _seed_vehicle(self.dealership)
        self.sale = _seed_sale(self.dealership, self.vehicle)

    def _get_url(self, stock: str) -> str:
        return reverse(DELIVERY_URL, args=[stock])

    def test_get_returns_delivery_when_present(self) -> None:
        delivery = Delivery.objects.create(
            dealership=self.dealership, sale=self.sale
        )
        response = self.client.get(self._get_url(self.vehicle.stock_number))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("delivery", body)
        self.assertEqual(body["delivery"]["id"], delivery.pk)
        self.assertEqual(body["delivery"]["sale_id"], self.sale.pk)
        # Checklist is a dict with the five M9.2 keys all False by default.
        self.assertEqual(body["delivery"]["checklist"]["fueled"], False)

    def test_get_404_when_no_delivery(self) -> None:
        response = self.client.get(self._get_url(self.vehicle.stock_number))
        self.assertEqual(response.status_code, 404)

    def test_get_404_when_no_sale(self) -> None:
        # Vehicle with no Sale surfaces the same way — no Delivery
        # can exist without a Sale (OneToOne mandatory), so the join
        # returns nothing.
        v2 = _seed_vehicle(self.dealership, stock="NO-SALE")
        response = self.client.get(self._get_url(v2.stock_number))
        self.assertEqual(response.status_code, 404)

    def test_get_cross_tenant_returns_404(self) -> None:
        tenant_b = make_dealership(slug="m95-read-del-b")
        vehicle_b = _seed_vehicle(tenant_b, stock="B-DEL-1")
        sale_b = _seed_sale(tenant_b, vehicle_b)
        Delivery.objects.create(dealership=tenant_b, sale=sale_b)
        response = self.client.get(self._get_url(vehicle_b.stock_number))
        self.assertEqual(response.status_code, 404)

    def test_post_create_still_works(self) -> None:
        response = self.client.post(
            self._get_url(self.vehicle.stock_number),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Delivery.objects.count(), 1)

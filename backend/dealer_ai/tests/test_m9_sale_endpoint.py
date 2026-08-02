"""Milestone 9 · Increment 1 (SESSION_100) — Sale endpoint tests.

Locks the HTTP surface of :func:`views_sale.admin_sale_create` per
``MILESTONE_9_PLANNING.md`` §1.6.

Coverage:

- Unauthenticated → 401 / 403.
- Authenticated with no dealership membership → 403.
- Authenticated with disallowed role (advisor / porter /
  f_and_i_manager / collections) → 403.
- Authenticated with allowed role (recon_manager / sales_manager /
  dealer_owner) → 201 on success.
- Cross-tenant isolation via the endpoint — a Sale POST for a
  vehicle owned by tenant B never lands from a request in tenant A
  (surfaces as 404, not 403).
- 409 Conflict on duplicate Sale for the same vehicle.
- 404 on unknown buyer / cross-tenant buyer.
- 400 on invalid finance_type / missing required field.
- Response shape (``sale`` dict with stringified Decimals).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_PARTS,
    ROLE_ADVISOR,
    ROLE_COLLECTIONS,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_CASH,
    SALE_FINANCE_TYPE_RETAIL,
    SOURCE_AUCTION,
    CustomerLead,
    Sale,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


URL_NAME = "dealer_ai:admin-sale-create"


def _seed_vehicle(
    dealership,
    *,
    stock: str = "EP-1",
    purchase_price: str = "20000.00",
    add_actual_cost: bool = True,
) -> Vehicle:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28000.00"),
        dealership=dealership,
    )
    VehicleAcquisition.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=Decimal(purchase_price),
        purchase_date=dt.date(2026, 6, 1),
    )
    if add_actual_cost:
        VehicleCost.objects.create(
            vehicle=vehicle,
            dealership=dealership,
            category=CATEGORY_PARTS,
            amount=Decimal("500.00"),
            incurred_at=timezone.now(),
            is_estimate=False,
        )
    return vehicle


class SaleEndpointAuthTests(TestCase):
    """Auth + role-gate matrix."""

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m91-ep-auth")
        self.vehicle = _seed_vehicle(self.dealership, stock="AUTH-1")
        self.payload = {
            "sale_date": "2026-08-01",
            "sold_price": "25000.00",
            "finance_type": SALE_FINANCE_TYPE_CASH,
        }
        self.url = reverse(URL_NAME, args=[self.vehicle.stock_number])

    def test_unauthenticated_forbidden(self) -> None:
        client = APIClient()
        response = client.post(self.url, self.payload, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_no_membership_forbidden(self) -> None:
        user = make_user(username="ep-no-mem")
        client = authenticated_client(user)
        response = client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_advisor_role_forbidden(self) -> None:
        user = make_user(username="ep-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_porter_role_forbidden(self) -> None:
        user = make_user(username="ep-porter")
        make_membership(user, self.dealership, ROLE_PORTER)
        client = authenticated_client(user)
        response = client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_f_and_i_role_forbidden(self) -> None:
        user = make_user(username="ep-fi")
        make_membership(user, self.dealership, ROLE_F_AND_I_MANAGER)
        client = authenticated_client(user)
        response = client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_collections_role_forbidden(self) -> None:
        user = make_user(username="ep-coll")
        make_membership(user, self.dealership, ROLE_COLLECTIONS)
        client = authenticated_client(user)
        response = client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 403)

    def test_recon_manager_can_post(self) -> None:
        user = make_user(username="ep-recon")
        make_membership(user, self.dealership, ROLE_RECON_MANAGER)
        client = authenticated_client(user)
        response = client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_sales_manager_can_post(self) -> None:
        user = make_user(username="ep-sales")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        client = authenticated_client(user)
        response = client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_dealer_owner_can_post(self) -> None:
        user = make_user(username="ep-owner")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        client = authenticated_client(user)
        response = client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 201)


class SaleEndpointBehaviorTests(TestCase):
    """Success + domain-error mapping."""

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m91-ep-behavior")
        self.user = make_user(username="ep-behavior")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle = _seed_vehicle(self.dealership, stock="BEH-1")
        self.url = reverse(URL_NAME, args=[self.vehicle.stock_number])

    def test_success_returns_sale_projection(self) -> None:
        buyer = CustomerLead.objects.create(
            dealership=self.dealership, name="Endpoint Buyer"
        )
        response = self.client.post(
            self.url,
            {
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_RETAIL,
                "buyer_id": buyer.pk,
                "lender_name": "First National",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIn("sale", body)
        sale = body["sale"]
        # Response uses stringified Decimals per M2/M4/M8 convention.
        self.assertEqual(sale["sold_price"], "25000.00")
        # 25,000 - (20,000 + 500) = 4,500.
        self.assertEqual(sale["gross_realized"], "4500.00")
        self.assertEqual(sale["vehicle_stock"], self.vehicle.stock_number)
        self.assertEqual(sale["buyer_id"], buyer.pk)
        self.assertEqual(sale["finance_type"], SALE_FINANCE_TYPE_RETAIL)
        self.assertEqual(sale["lender_name"], "First National")

    def test_success_without_buyer(self) -> None:
        response = self.client.post(
            self.url,
            {
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIsNone(body["sale"]["buyer_id"])

    def test_404_on_unknown_vehicle(self) -> None:
        url = reverse(URL_NAME, args=["NONEXISTENT-1"])
        response = self.client.post(
            url,
            {
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_404_on_unknown_buyer(self) -> None:
        response = self.client.post(
            self.url,
            {
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
                "buyer_id": 999_999,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_409_on_duplicate_sale(self) -> None:
        # First sale — succeeds.
        response1 = self.client.post(
            self.url,
            {
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
            },
            format="json",
        )
        self.assertEqual(response1.status_code, 201)
        # Second sale on same vehicle — 409 Conflict.
        response2 = self.client.post(
            self.url,
            {
                "sale_date": "2026-08-15",
                "sold_price": "27000.00",
                "finance_type": SALE_FINANCE_TYPE_RETAIL,
            },
            format="json",
        )
        self.assertEqual(response2.status_code, 409)

    def test_400_on_invalid_finance_type(self) -> None:
        response = self.client.post(
            self.url,
            {
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": "lease",  # Not in Option A vocabulary.
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_400_on_missing_required_field(self) -> None:
        response = self.client.post(
            self.url,
            {
                # Missing sale_date.
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class SaleEndpointCrossTenantTests(TestCase):
    """Tenant B's vehicle must be invisible to tenant A's caller."""

    def setUp(self) -> None:
        self.tenant_a = make_dealership(slug="m91-ep-tenant-a")
        self.tenant_b = make_dealership(slug="m91-ep-tenant-b")
        self.vehicle_b = _seed_vehicle(self.tenant_b, stock="BONLY-1")

        self.user_a = make_user(username="ep-user-a")
        make_membership(self.user_a, self.tenant_a, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(self.user_a)

    def test_cross_tenant_vehicle_returns_404(self) -> None:
        url = reverse(URL_NAME, args=[self.vehicle_b.stock_number])
        response = self.client_a.post(
            url,
            {
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
            },
            format="json",
        )
        # Fail-closed: 404 (never leak cross-tenant existence via 403).
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Sale.objects.count(), 0)

    def test_cross_tenant_buyer_returns_404(self) -> None:
        # Vehicle in tenant A; buyer in tenant B.
        vehicle_a = _seed_vehicle(self.tenant_a, stock="ATA-1")
        buyer_b = CustomerLead.objects.create(
            dealership=self.tenant_b, name="B-only Buyer"
        )
        url = reverse(URL_NAME, args=[vehicle_a.stock_number])
        response = self.client_a.post(
            url,
            {
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
                "buyer_id": buyer_b.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Sale.objects.count(), 0)

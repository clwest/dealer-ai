"""Milestone 8 · Increment 4 (SESSION_097) — vehicle-type-recon-cost endpoint tests.

Shape-level auth + response shape. Full auth matrix locked by M8.1.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_PARTS,
    ROLE_ADVISOR,
    ROLE_RECON_MANAGER,
    Vehicle,
    VehicleCost,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


URL_NAME = "dealer_ai:admin-analytics-vehicle-type-recon-cost"


def _seed(dealership, stock: str, *, make="Ford", model="F-150", amount="500.00"):
    v = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        make=make,
        model=model,
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    VehicleCost.objects.create(
        vehicle=v,
        dealership=dealership,
        category=CATEGORY_PARTS,
        amount=Decimal(amount),
        incurred_at=timezone.now(),
    )


class VehicleTypeReconCostEndpointAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="vtre-auth")

    def test_unauthenticated_forbidden(self) -> None:
        client = APIClient()
        response = client.get(reverse(URL_NAME))
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="vtre-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_recon_manager_allowed(self) -> None:
        user = make_user(username="vtre-recon")
        make_membership(user, self.dealership, ROLE_RECON_MANAGER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)


class VehicleTypeReconCostEndpointShapeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="vtre-shape")
        self.user = make_user(username="vtre-shape-user")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)

    def test_empty_tenant_returns_empty_rows(self) -> None:
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": []})

    def test_response_row_shape(self) -> None:
        _seed(
            self.dealership,
            "F1",
            make="Ford",
            model="F-150",
            amount="800.00",
        )
        _seed(
            self.dealership,
            "F2",
            make="Ford",
            model="F-150",
            amount="1200.00",
        )
        response = self.client.get(reverse(URL_NAME))
        payload = response.json()
        self.assertEqual(len(payload["rows"]), 1)
        row = payload["rows"][0]
        self.assertEqual(row["make"], "Ford")
        self.assertEqual(row["model"], "F-150")
        self.assertEqual(row["vehicle_count"], 2)
        self.assertEqual(row["total_recon_cost"], "2000.00")
        self.assertEqual(row["mean_recon_cost"], "1000.00")

    def test_cross_tenant_isolation(self) -> None:
        other = make_dealership(slug="vtre-other")
        _seed(other, "O1", model="F-150", amount="9999.00")
        _seed(self.dealership, "M1", model="F-150", amount="150.00")
        response = self.client.get(reverse(URL_NAME))
        rows = response.json()["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_recon_cost"], "150.00")

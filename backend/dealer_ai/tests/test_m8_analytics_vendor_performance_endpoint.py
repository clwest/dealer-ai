"""Milestone 8 · Increment 2 (SESSION_095) — vendor-performance endpoint tests.

Locks the HTTP surface of
:func:`views_analytics.admin_analytics_vendor_performance`.

Coverage discipline mirrors M8.1 (see
``test_m8_analytics_endpoint.py``): auth matrix at the shape level
(one allowed role + one denied role each), response shape, cross-
tenant isolation, window query args, malformed date → 400. The full
role matrix is covered by M8.1's endpoint tests + the shared
``IsReconManagerSalesManagerOrOwnerAtActiveDealership`` permission
class the endpoint composes.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_VENUE_OUTSOURCED,
    Vehicle,
    Vendor,
    WorkOrder,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


URL_NAME = "dealer_ai:admin-analytics-vendor-performance"


_STOCK_COUNTER = {"n": 0}


def _next_stock() -> str:
    _STOCK_COUNTER["n"] += 1
    return f"VPE-{_STOCK_COUNTER['n']:04d}"


def _aware(y: int, m: int, d: int) -> dt.datetime:
    return timezone.make_aware(dt.datetime(y, m, d, 12, 0))


def _seed_completed_wo(
    dealership,
    vendor,
    *,
    approved_at,
    completed_at,
    estimated_cost: str | None = None,
    authorized_cost: str | None = None,
    actual_cost: str | None = None,
) -> None:
    vehicle = Vehicle.objects.create(
        stock_number=_next_stock(),
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        vendor=vendor,
        category=CONDITION_CATEGORY_BODY,
        venue=WORK_ORDER_VENUE_OUTSOURCED,
        status=WORK_ORDER_STATUS_COMPLETED,
        approved_at=approved_at,
        completed_at=completed_at,
        estimated_cost=(
            Decimal(estimated_cost) if estimated_cost is not None else None
        ),
        authorized_cost=(
            Decimal(authorized_cost) if authorized_cost is not None else None
        ),
        actual_cost=(
            Decimal(actual_cost) if actual_cost is not None else None
        ),
    )


class VendorPerformanceEndpointAuthTests(TestCase):
    """Shape-level auth check — full matrix lives in M8.1 tests."""

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="vpe-auth")

    def test_unauthenticated_forbidden(self) -> None:
        client = APIClient()
        response = client.get(reverse(URL_NAME))
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_role_forbidden(self) -> None:
        user = make_user(username="vpe-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_recon_manager_role_allowed(self) -> None:
        user = make_user(username="vpe-recon")
        make_membership(user, self.dealership, ROLE_RECON_MANAGER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)

    def test_sales_manager_role_allowed(self) -> None:
        user = make_user(username="vpe-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)

    def test_dealer_owner_role_allowed(self) -> None:
        user = make_user(username="vpe-do")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)


class VendorPerformanceEndpointShapeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="vpe-shape")
        self.user = make_user(username="vpe-shape-user")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)

    def test_empty_tenant_returns_empty_rows(self) -> None:
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": []})

    def test_response_row_shape(self) -> None:
        vendor = Vendor.objects.create(
            dealership=self.dealership,
            slug="acme-body",
            name="ACME Body Shop",
        )
        _seed_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 5),
            estimated_cost="1000.00",
            authorized_cost="1200.00",
            actual_cost="1100.00",
        )
        _seed_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 10),
            completed_at=_aware(2026, 8, 14),
            estimated_cost="500.00",
            authorized_cost="600.00",
            actual_cost="700.00",
        )
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["rows"]), 1)
        row = payload["rows"][0]
        self.assertEqual(row["vendor_slug"], "acme-body")
        self.assertEqual(row["vendor_name"], "ACME Body Shop")
        self.assertEqual(row["completed_count"], 2)
        self.assertEqual(row["mean_completion_days"], 4)
        # |1100-1000|/1000*100 = 10%, |700-500|/500*100 = 40%, mean 25.
        self.assertEqual(row["mean_variance_pct"], "25.00")
        # 700 > 600 → over-budget; 1100 < 1200 → not.
        self.assertEqual(row["over_budget_count"], 1)

    def test_null_metrics_render_as_json_null(self) -> None:
        # Vendor with a completed WO but neither approved_at nor
        # estimated_cost — mean_completion_days AND
        # mean_variance_pct should both render as null.
        vendor = Vendor.objects.create(
            dealership=self.dealership,
            slug="skeletal",
            name="Skeletal Shop",
        )
        _seed_completed_wo(
            self.dealership,
            vendor,
            approved_at=None,
            completed_at=_aware(2026, 8, 5),
            estimated_cost=None,
            actual_cost="500.00",
        )
        response = self.client.get(reverse(URL_NAME))
        row = response.json()["rows"][0]
        self.assertIsNone(row["mean_completion_days"])
        self.assertIsNone(row["mean_variance_pct"])
        self.assertEqual(row["over_budget_count"], 0)

    def test_window_start_query_arg(self) -> None:
        vendor = Vendor.objects.create(
            dealership=self.dealership, slug="win", name="Win Shop"
        )
        _seed_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 7, 1),
            completed_at=_aware(2026, 7, 5),
        )
        _seed_completed_wo(
            self.dealership,
            vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 5),
        )
        response = self.client.get(
            reverse(URL_NAME), {"window_start": "2026-08-01"}
        )
        rows = response.json()["rows"]
        self.assertEqual(rows[0]["completed_count"], 1)

    def test_malformed_window_start_returns_400(self) -> None:
        response = self.client.get(
            reverse(URL_NAME), {"window_start": "not-a-date"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("window_start", response.json()["detail"])

    def test_cross_tenant_isolation(self) -> None:
        other = make_dealership(slug="vpe-other")
        other_vendor = Vendor.objects.create(
            dealership=other, slug="other-shop", name="Other Shop"
        )
        _seed_completed_wo(
            other,
            other_vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 5),
        )
        mine_vendor = Vendor.objects.create(
            dealership=self.dealership, slug="mine", name="Mine"
        )
        _seed_completed_wo(
            self.dealership,
            mine_vendor,
            approved_at=_aware(2026, 8, 1),
            completed_at=_aware(2026, 8, 5),
        )
        response = self.client.get(reverse(URL_NAME))
        rows = response.json()["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["vendor_slug"], "mine")

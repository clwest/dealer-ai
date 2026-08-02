"""Milestone 8 · Increment 1 (SESSION_094) — analytics endpoint tests.

Locks the HTTP surface of
:func:`views_analytics.admin_analytics_recon_cost_per_source` per
``MILESTONE_8_PLANNING.md`` §1.9.

Coverage:

- Unauthenticated → 401 / 403.
- Authenticated with no dealership membership → 403.
- Authenticated with disallowed role (advisor / porter /
  f_and_i_manager / collections) → 403.
- Authenticated with allowed role (recon_manager / sales_manager /
  dealer_owner) → 200.
- Cross-tenant isolation via the endpoint — recon spend on tenant B
  is never returned to a request from tenant A.
- Response shape (``rows`` array of source-performance dicts).
- ``window_start`` / ``window_end`` query args accepted and applied.
- Malformed date query arg → 400.
- Response uses stringified Decimals.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_PARTS,
    ROLE_ADVISOR,
    ROLE_COLLECTIONS,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    SOURCE_AUCTION,
    SOURCE_TRADE,
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


URL_NAME = "dealer_ai:admin-analytics-recon-cost-per-source"


def _seed_recon_row(
    dealership,
    stock: str,
    *,
    source: str = SOURCE_AUCTION,
    amount: str = "500.00",
    category: str = CATEGORY_PARTS,
    incurred_at: dt.datetime | None = None,
) -> None:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    VehicleAcquisition.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        source=source,
        purchase_price=Decimal("18000.00"),
        purchase_date=dt.date(2026, 6, 1),
    )
    VehicleCost.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=category,
        amount=Decimal(amount),
        incurred_at=incurred_at or timezone.now(),
    )


class AnalyticsEndpointAuthTests(TestCase):
    """Auth + role-gate matrix."""

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m81-auth")
        _seed_recon_row(self.dealership, "AUTH-1")

    def test_unauthenticated_forbidden(self) -> None:
        client = APIClient()
        response = client.get(reverse(URL_NAME))
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_no_membership_forbidden(self) -> None:
        user = make_user(username="no-membership")
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_advisor_role_forbidden(self) -> None:
        user = make_user(username="advisor-u")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_porter_role_forbidden(self) -> None:
        user = make_user(username="porter-u")
        make_membership(user, self.dealership, ROLE_PORTER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_f_and_i_manager_role_forbidden(self) -> None:
        user = make_user(username="fi-u")
        make_membership(user, self.dealership, ROLE_F_AND_I_MANAGER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_collections_role_forbidden(self) -> None:
        user = make_user(username="coll-u")
        make_membership(user, self.dealership, ROLE_COLLECTIONS)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_recon_manager_role_allowed(self) -> None:
        user = make_user(username="recon-u")
        make_membership(user, self.dealership, ROLE_RECON_MANAGER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)

    def test_sales_manager_role_allowed(self) -> None:
        user = make_user(username="sm-u")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)

    def test_dealer_owner_role_allowed(self) -> None:
        user = make_user(username="do-u")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)


class AnalyticsEndpointShapeTests(TestCase):
    """Response shape + query-arg semantics."""

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m81-shape")
        self.user = make_user(username="shape-user")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)

    def test_empty_tenant_returns_empty_rows(self) -> None:
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": []})

    def test_response_row_shape(self) -> None:
        _seed_recon_row(
            self.dealership, "S-1", source=SOURCE_AUCTION, amount="500.00"
        )
        _seed_recon_row(
            self.dealership,
            "S-2",
            source=SOURCE_AUCTION,
            amount="1000.00",
            category=CATEGORY_MECHANICAL_LABOR,
        )
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["rows"]), 1)
        row = payload["rows"][0]
        self.assertEqual(row["source"], "auction")
        self.assertEqual(row["source_display"], "Auction")
        self.assertEqual(row["vehicle_count"], 2)
        # Stringified Decimals — see view module docstring for the
        # precision rationale.
        self.assertEqual(row["total_recon_cost"], "1500.00")
        self.assertEqual(row["mean_recon_cost"], "750.00")

    def test_window_start_query_arg(self) -> None:
        aware = timezone.make_aware
        _seed_recon_row(
            self.dealership,
            "WIN-JUL",
            amount="100.00",
            incurred_at=aware(dt.datetime(2026, 7, 1, 12, 0)),
        )
        _seed_recon_row(
            self.dealership,
            "WIN-AUG",
            amount="200.00",
            incurred_at=aware(dt.datetime(2026, 8, 15, 12, 0)),
        )
        response = self.client.get(
            reverse(URL_NAME), {"window_start": "2026-08-01"}
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()["rows"]
        self.assertEqual(rows[0]["total_recon_cost"], "200.00")
        self.assertEqual(rows[0]["vehicle_count"], 1)

    def test_window_end_query_arg(self) -> None:
        aware = timezone.make_aware
        _seed_recon_row(
            self.dealership,
            "WIN-JUL",
            amount="100.00",
            incurred_at=aware(dt.datetime(2026, 7, 1, 12, 0)),
        )
        _seed_recon_row(
            self.dealership,
            "WIN-AUG",
            amount="200.00",
            incurred_at=aware(dt.datetime(2026, 8, 15, 12, 0)),
        )
        response = self.client.get(
            reverse(URL_NAME), {"window_end": "2026-07-31"}
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()["rows"]
        self.assertEqual(rows[0]["total_recon_cost"], "100.00")

    def test_malformed_window_start_returns_400(self) -> None:
        response = self.client.get(
            reverse(URL_NAME), {"window_start": "not-a-date"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("window_start", response.json()["detail"])

    def test_malformed_window_end_returns_400(self) -> None:
        response = self.client.get(
            reverse(URL_NAME), {"window_end": "2026-13-40"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("window_end", response.json()["detail"])

    def test_cross_tenant_response_isolation(self) -> None:
        # A recon-manager at tenant A must not see tenant B's recon
        # spend even when that spend dwarfs their own.
        other = make_dealership(slug="m81-other")
        _seed_recon_row(other, "OTHER-1", amount="9999.00")
        _seed_recon_row(self.dealership, "MINE-1", amount="120.00")

        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        rows = response.json()["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_recon_cost"], "120.00")

    def test_sorted_by_total_desc(self) -> None:
        # Two sources — trade at $300, auction at $800. Auction wins.
        _seed_recon_row(
            self.dealership, "SRT-1", source=SOURCE_AUCTION, amount="800.00"
        )
        _seed_recon_row(
            self.dealership, "SRT-2", source=SOURCE_TRADE, amount="300.00"
        )
        response = self.client.get(reverse(URL_NAME))
        rows = response.json()["rows"]
        self.assertEqual([r["source"] for r in rows], ["auction", "trade"])

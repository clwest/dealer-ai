"""Milestone 25 · Increment 2 (SESSION_187) — admin vehicle list endpoint.

Additive `GET /admin/vehicles/` added at M25.2 open to unblock the
M25.2 test-drive form's vehicle picker per MILESTONE_25_PLANNING.md
§5.e. Empirical discovery at open (see SESSION_187 handoff): no
tenant-wide admin vehicle-list endpoint existed on the shipped
surface — every `admin/vehicles/*` route was stock-scoped.

Coverage:

- Auth / permission (401 anonymous; 403 wrong role; 200 sales_manager
  + dealer_owner).
- Tenant scoping (cross-tenant vehicles never leak).
- Projection shape (id, stock_number, year/make/model/trim,
  condition, price, image_url, is_available, display_name).
- Optional filters (search, condition, is_available).
- Pagination (limit/offset, honest count, next/previous URLs) — the
  pre-2026-09-01 shape returned ``count: len(rows)`` under a silent
  100-row cap, which lied the moment the dataset crossed 100.
  Superseded by TASK_vehicle_list_caps_and_miscounts.
- Ordering matches Vehicle.Meta (`-year, model`).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_SALES_MANAGER,
    Dealership,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


ENDPOINT = "dealer_ai:admin-vehicle-list"


def _make_vehicle(
    dealership: Dealership,
    *,
    stock: str,
    year: int = 2024,
    make: str = "Ford",
    model: str = "F-150",
    trim: str = "XLT",
    condition: str = "new",
    price: str = "45000.00",
    is_available: bool = True,
    image_url: str = "",
) -> Vehicle:
    return Vehicle.objects.create(
        dealership=dealership,
        stock_number=stock,
        year=year,
        make=make,
        model=model,
        trim=trim,
        condition=condition,
        price=Decimal(price),
        is_available=is_available,
        image_url=image_url,
    )


class AdminVehicleListAuthTests(TestCase):
    """M25.2 auth matrix — matches M11.6 list-endpoint precedent."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.url = reverse(ENDPOINT)

    def test_anonymous_gets_403(self) -> None:
        # DRF returns 403 for anonymous on IsAuthenticated-gated
        # endpoints (matches M11.6 precedent).
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_role_denied(self) -> None:
        user = make_user(username="m252-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = authenticated_client(user).get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_sales_manager_allowed(self) -> None:
        user = make_user(username="m252-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        response = authenticated_client(user).get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_dealer_owner_allowed(self) -> None:
        user = make_user(username="m252-owner")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        response = authenticated_client(user).get(self.url)
        self.assertEqual(response.status_code, 200)


class AdminVehicleListShapeTests(TestCase):
    """Projection shape + tenant scoping + happy-path filters."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other_dealership = Dealership.objects.create(
            slug="m252-other", name="Other Dealer"
        )
        user = make_user(username="m252-shape-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(user)
        self.url = reverse(ENDPOINT)

    def test_returns_tenant_vehicles_only(self) -> None:
        mine = _make_vehicle(self.dealership, stock="MINE-1")
        _make_vehicle(
            self.other_dealership, stock="THEIRS-1", make="Toyota", model="Camry"
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        stocks = [r["stock_number"] for r in body["results"]]
        self.assertIn("MINE-1", stocks)
        self.assertNotIn(
            "THEIRS-1",
            stocks,
            "cross-tenant vehicle must never appear in the list",
        )
        self.assertEqual(body["count"], len(body["results"]))
        # Projection shape: every documented field present on the row.
        row = next(r for r in body["results"] if r["stock_number"] == "MINE-1")
        for key in (
            "id",
            "stock_number",
            "year",
            "make",
            "model",
            "trim",
            "condition",
            "price",
            "image_url",
            "is_available",
            "display_name",
        ):
            self.assertIn(key, row)
        self.assertEqual(row["id"], mine.pk)
        self.assertEqual(row["price"], "45000.00")
        self.assertTrue(row["is_available"])

    def test_search_matches_stock_year_make_model_trim(self) -> None:
        _make_vehicle(self.dealership, stock="F150-2024", year=2024, model="F-150")
        _make_vehicle(
            self.dealership,
            stock="RANGER-2023",
            year=2023,
            model="Ranger",
            trim="Lariat",
        )
        _make_vehicle(
            self.dealership,
            stock="EDGE-2024",
            year=2024,
            model="Edge",
            make="Ford",
        )
        # Substring on model.
        rangers = self.client.get(self.url, {"search": "Ranger"}).json()
        self.assertEqual(len(rangers["results"]), 1)
        self.assertEqual(rangers["results"][0]["stock_number"], "RANGER-2023")
        # Substring on trim.
        lariats = self.client.get(self.url, {"search": "Lariat"}).json()
        self.assertEqual(len(lariats["results"]), 1)
        # Exact year match.
        y2023 = self.client.get(self.url, {"search": "2023"}).json()
        self.assertEqual(len(y2023["results"]), 1)
        self.assertEqual(y2023["results"][0]["stock_number"], "RANGER-2023")
        # Stock-number substring.
        edges = self.client.get(self.url, {"search": "EDGE"}).json()
        self.assertEqual(len(edges["results"]), 1)
        self.assertEqual(edges["results"][0]["stock_number"], "EDGE-2024")

    def test_condition_filter(self) -> None:
        _make_vehicle(self.dealership, stock="NEW-1", condition="new")
        _make_vehicle(self.dealership, stock="USED-1", condition="used")
        _make_vehicle(
            self.dealership, stock="CPO-1", condition="certified"
        )
        used = self.client.get(self.url, {"condition": "used"}).json()
        self.assertEqual(len(used["results"]), 1)
        self.assertEqual(used["results"][0]["stock_number"], "USED-1")
        cpo = self.client.get(self.url, {"condition": "certified"}).json()
        self.assertEqual(len(cpo["results"]), 1)
        self.assertEqual(cpo["results"][0]["stock_number"], "CPO-1")

    def test_is_available_filter(self) -> None:
        _make_vehicle(self.dealership, stock="AVAIL-1", is_available=True)
        _make_vehicle(self.dealership, stock="SOLD-1", is_available=False)
        avail = self.client.get(self.url, {"is_available": "true"}).json()
        stocks = [r["stock_number"] for r in avail["results"]]
        self.assertIn("AVAIL-1", stocks)
        self.assertNotIn("SOLD-1", stocks)
        sold = self.client.get(self.url, {"is_available": "false"}).json()
        stocks_sold = [r["stock_number"] for r in sold["results"]]
        self.assertIn("SOLD-1", stocks_sold)
        self.assertNotIn("AVAIL-1", stocks_sold)

    def test_garbage_filters_are_silently_ignored(self) -> None:
        _make_vehicle(self.dealership, stock="ANY-1")
        response = self.client.get(
            self.url,
            {
                "condition": "not-a-choice",
                "is_available": "maybe",
                "search": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Non-matching filters silently ignored; row still appears.
        stocks = [r["stock_number"] for r in response.json()["results"]]
        self.assertIn("ANY-1", stocks)

    def test_default_page_size_is_100_but_count_is_honest(self) -> None:
        """TASK_vehicle_list_caps_and_miscounts (2026-09-01) — the
        previous shape truncated at 100 and reported ``count: 100``
        regardless of true total. The default page size stays 100
        for wire-compat, but ``count`` now reports the real total
        and ``has_more`` / ``next`` name the truncation explicitly.
        """
        for i in range(150):
            _make_vehicle(self.dealership, stock=f"CAP-{i:03d}")
        body = self.client.get(self.url).json()
        self.assertEqual(len(body["results"]), 100)
        self.assertEqual(
            body["count"],
            150,
            "count must reflect the true total, not the page length",
        )
        self.assertTrue(body["has_more"])
        self.assertIsNotNone(body["next"])
        self.assertIsNone(body["previous"])
        self.assertEqual(body["limit"], 100)
        self.assertEqual(body["offset"], 0)

    def test_limit_and_offset_paginate(self) -> None:
        for i in range(15):
            _make_vehicle(self.dealership, stock=f"PG-{i:03d}")
        page1 = self.client.get(self.url, {"limit": 5, "offset": 0}).json()
        page2 = self.client.get(self.url, {"limit": 5, "offset": 5}).json()
        page3 = self.client.get(self.url, {"limit": 5, "offset": 10}).json()
        self.assertEqual(page1["count"], 15)
        self.assertEqual(page2["count"], 15)
        self.assertEqual(page3["count"], 15)
        self.assertEqual(len(page1["results"]), 5)
        self.assertEqual(len(page2["results"]), 5)
        self.assertEqual(len(page3["results"]), 5)
        self.assertTrue(page1["has_more"])
        self.assertTrue(page2["has_more"])
        self.assertFalse(page3["has_more"])
        self.assertIsNone(page1["previous"])
        self.assertIsNotNone(page2["previous"])
        self.assertIsNotNone(page3["previous"])
        # Pages must not overlap and must cover the full set.
        seen = (
            [r["stock_number"] for r in page1["results"]]
            + [r["stock_number"] for r in page2["results"]]
            + [r["stock_number"] for r in page3["results"]]
        )
        self.assertEqual(len(seen), 15)
        self.assertEqual(len(set(seen)), 15)

    def test_limit_is_capped_and_garbage_clamped(self) -> None:
        for i in range(5):
            _make_vehicle(self.dealership, stock=f"CLAMP-{i:03d}")
        # Over-max clamps to default (not to max — deliberate: a caller
        # asking for 5,000 rows almost certainly meant a bug, not a
        # 200-row page. Silently clamping to default is the safer read.)
        big = self.client.get(self.url, {"limit": 9999}).json()
        self.assertEqual(big["limit"], 100)
        # Non-numeric garbage.
        junk = self.client.get(self.url, {"limit": "yes-please"}).json()
        self.assertEqual(junk["limit"], 100)
        # Negative offset clamps to 0.
        neg = self.client.get(self.url, {"offset": -50}).json()
        self.assertEqual(neg["offset"], 0)

    def test_ordering_matches_meta(self) -> None:
        # Vehicle.Meta orders `-year, model` — newest year first, then
        # alphabetical model.
        _make_vehicle(self.dealership, stock="OLD-1", year=2019, model="Focus")
        _make_vehicle(self.dealership, stock="NEW-1", year=2025, model="Bronco")
        _make_vehicle(
            self.dealership, stock="MID-1", year=2022, model="Explorer"
        )
        rows = self.client.get(self.url).json()["results"]
        years = [r["year"] for r in rows]
        self.assertEqual(years, sorted(years, reverse=True))

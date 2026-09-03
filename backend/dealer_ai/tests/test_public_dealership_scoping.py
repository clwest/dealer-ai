"""SESSION_232 addendum — public chat + showroom scope by
``X-Dealership-Slug`` (or auth) so multi-store installs stop routing
anonymous callers to the single-tenant default."""

from __future__ import annotations

from decimal import Decimal

from django.test import Client, TestCase

from dealer_ai.models import Dealership, Vehicle
from dealer_ai.services.inventory_search import (
    invalidate_inventory_vocabulary,
)
from dealer_ai.services.tenancy import get_default_dealership


HDR = "HTTP_X_DEALERSHIP_SLUG"


def _mk(dealership, stock, model, make="Chevrolet", body="truck", price="16000"):
    return Vehicle.objects.create(
        dealership=dealership,
        stock_number=stock,
        year=2020,
        make=make,
        model=model,
        body_style=body,
        condition="used",
        price=Decimal(price),
        drivetrain="4WD",
    )


class PublicShowroomScopingTests(TestCase):
    def setUp(self):
        self.store_a = get_default_dealership()
        self.store_b = Dealership.objects.create(
            name="Copper Canyon", slug="copper-canyon-scoping"
        )
        _mk(self.store_a, "A-1", "F-150", make="Ford")
        _mk(self.store_b, "B-1", "Silverado 1500")
        _mk(self.store_b, "B-2", "Camry", make="Toyota", body="car", price="12000")
        invalidate_inventory_vocabulary(self.store_a.pk)
        invalidate_inventory_vocabulary(self.store_b.pk)

    def test_showroom_list_scopes_by_header(self):
        client = Client()
        resp = client.get(
            "/api/dealer-ai/showroom/vehicles/?limit=50",
            **{HDR: self.store_b.slug},
        )
        self.assertEqual(resp.status_code, 200)
        stocks = {row["stock_number"] for row in resp.json()["results"]}
        self.assertEqual(stocks, {"B-1", "B-2"})

    def test_showroom_list_no_header_returns_default_store_only(self):
        client = Client()
        resp = client.get("/api/dealer-ai/showroom/vehicles/?limit=50")
        self.assertEqual(resp.status_code, 200)
        stocks = {row["stock_number"] for row in resp.json()["results"]}
        self.assertEqual(stocks, {"A-1"})


class PublicChatScopingTests(TestCase):
    def setUp(self):
        self.store_a = get_default_dealership()
        self.store_b = Dealership.objects.create(
            name="Copper Canyon Chat", slug="copper-canyon-chat"
        )
        self.silverado = _mk(self.store_b, "CB-1", "Silverado 1500")
        invalidate_inventory_vocabulary(self.store_a.pk)
        invalidate_inventory_vocabulary(self.store_b.pk)

    def test_start_chat_with_slug_header_binds_to_that_store(self):
        client = Client()
        resp = client.post(
            "/api/dealer-ai/chat/start/",
            data={"initial_message": "got any silverados?"},
            content_type="application/json",
            **{HDR: self.store_b.slug},
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        session_id = body["session"]["id"]
        from dealer_ai.models import ChatSession

        session = ChatSession.objects.get(id=session_id)
        self.assertEqual(session.dealership_id, self.store_b.pk)
        matched_stocks = {v["stock_number"] for v in body["matched_vehicles"]}
        self.assertIn("CB-1", matched_stocks)

    def test_start_chat_without_header_binds_to_default(self):
        client = Client()
        resp = client.post(
            "/api/dealer-ai/chat/start/",
            data={},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        from dealer_ai.models import ChatSession

        session = ChatSession.objects.get(id=resp.json()["session"]["id"])
        self.assertEqual(session.dealership_id, self.store_a.pk)

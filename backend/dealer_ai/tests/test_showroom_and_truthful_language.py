"""Milestone 6 · Increment 5 (SESSION_086) — showroom endpoint +
SESSION_075 §5.i truthful-language refactor tests.

Two concerns colocated because both consume the M6.5 retail-gate
helpers in ``services/chat_engine.py``:

- ``GET /showroom/vehicles/<stock>/`` — public showroom endpoint.
  Retail gate requires stage=frontline AND published listing.
- ``vehicle_detail`` / ``vehicle_ask`` — customer-facing stock-
  specific chat lookups. Refactored to return the SESSION_075 §5.i
  truthful copy on non-retail vehicles.

Locked invariants:

- Public showroom returns 200 with the projected shape for
  frontline + published vehicles.
- Non-retail vehicles (any missing condition) return 404 with the
  truthful "not currently available for retail" copy.
- vehicle_detail + vehicle_ask return the same truthful copy on
  non-retail vehicles (no leakage of stage / recon / etc.).
- Truthful copy is exactly the string per SESSION_075 §5.i.
"""

from __future__ import annotations

import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    VEHICLE_LISTING_STATUS_DRAFT,
    VEHICLE_LISTING_STATUS_PUBLISHED,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_LISTING,
    Vehicle,
    VehicleListing,
)
from dealer_ai.services.chat_engine import (
    CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY,
)
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.services.vehicle_lifecycle import (
    advance_stage,
    ensure_current_stage,
)


def _vehicle(dealership, stock="M65-SH", price="29500.00") -> Vehicle:
    return Vehicle.objects.create(
        dealership=dealership,
        stock_number=stock,
        year=2024,
        model="Escape",
        make="Ford",
        price=Decimal(price),
    )


def _publish_listing(vehicle, dealership) -> VehicleListing:
    now = timezone.now()
    return VehicleListing.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        status=VEHICLE_LISTING_STATUS_PUBLISHED,
        body="Nice vehicle.",
        drafted_at=now,
        approved_at=now,
        published_at=now,
    )


def _put_at_frontline(vehicle, dealership):
    """The M5.5 test-only auto-bootstrap seeds every new Vehicle at
    frontline. This helper is a no-op except as intent-marker.
    """
    ensure_current_stage(
        vehicle,
        dealership=dealership,
        initial_stage=VEHICLE_STAGE_FRONTLINE,
    )


# ============================================================================
# Public showroom endpoint
# ============================================================================


class ShowroomEndpoint(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        self.client_pub = APIClient()  # no auth — public endpoint

    def test_frontline_with_published_listing_returns_200(self):
        vehicle = _vehicle(self.default, "M65SH-OK")
        _put_at_frontline(vehicle, self.default)
        _publish_listing(vehicle, self.default)
        response = self.client_pub.get(
            reverse(
                "dealer_ai:showroom-vehicle-detail",
                args=[vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stock_number"], vehicle.stock_number)
        self.assertEqual(response.data["listing"]["body"], "Nice vehicle.")

    def test_nonexistent_vehicle_returns_truthful_404(self):
        response = self.client_pub.get(
            reverse(
                "dealer_ai:showroom-vehicle-detail",
                args=["DOES-NOT-EXIST"],
            )
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["detail"], CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY
        )

    def test_frontline_without_listing_returns_truthful_404(self):
        """Vehicle is at frontline but has no listing → refused."""
        vehicle = _vehicle(self.default, "M65SH-NOLIST")
        _put_at_frontline(vehicle, self.default)
        # NO listing created.
        response = self.client_pub.get(
            reverse(
                "dealer_ai:showroom-vehicle-detail",
                args=[vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["detail"], CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY
        )

    def test_frontline_with_draft_listing_returns_truthful_404(self):
        """Vehicle is at frontline but listing is draft (not published)
        → refused."""
        vehicle = _vehicle(self.default, "M65SH-DRAFT")
        _put_at_frontline(vehicle, self.default)
        VehicleListing.objects.create(
            vehicle=vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_DRAFT,
            body="Draft.",
            drafted_at=timezone.now(),
        )
        response = self.client_pub.get(
            reverse(
                "dealer_ai:showroom-vehicle-detail",
                args=[vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_non_frontline_returns_truthful_404(self):
        """Vehicle is not at frontline (e.g. still in listing stage)
        → refused even if published listing exists (defensive)."""
        vehicle = _vehicle(self.default, "M65SH-NOTFRONT")
        _put_at_frontline(vehicle, self.default)
        _publish_listing(vehicle, self.default)
        # Move OFF frontline to listing stage (this is a weird state
        # but locks the retail-gate semantics).
        vehicle.stage.current_stage = VEHICLE_STAGE_LISTING
        vehicle.stage.save()
        response = self.client_pub.get(
            reverse(
                "dealer_ai:showroom-vehicle-detail",
                args=[vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_body_never_exposes_price_data(self):
        """The showroom response includes ``price`` but the projected
        vehicle dict deliberately excludes internal cost/margin
        fields. Basic guard: response contains ``price`` (public) but
        NOT any internal-cost keys."""
        vehicle = _vehicle(self.default, "M65SH-COST")
        _put_at_frontline(vehicle, self.default)
        _publish_listing(vehicle, self.default)
        response = self.client_pub.get(
            reverse(
                "dealer_ai:showroom-vehicle-detail",
                args=[vehicle.stock_number],
            )
        )
        self.assertIn("price", response.data)
        # Basic guard against future refactors adding cost leakage.
        response_str = json.dumps(response.data, default=str)
        self.assertNotIn("dealer_cost", response_str)
        self.assertNotIn("purchase_price", response_str)


# ============================================================================
# Public showroom list endpoint (SESSION_226,
# TASK_walkable-demo-and-servers-up 1d).
# ============================================================================


class ShowroomListEndpoint(TestCase):
    """Public list endpoint added so the customer-facing showroom /
    homepage teaser / hero visuals can render live inventory instead
    of importing the deleted ``sampleInventory.ts`` snapshot.

    Retail gate: ``customer_visible_vehicles()`` — frontline stage,
    debug stocks excluded. Publish requirement is NOT applied here
    (see the module docstring). This class locks the endpoint's
    filter surface + response shape + pagination behavior.
    """

    def setUp(self):
        self.default = get_default_dealership()
        self.client_pub = APIClient()  # no auth — public endpoint

    def _make_frontline(self, stock: str, **overrides) -> Vehicle:
        vehicle = Vehicle.objects.create(
            dealership=self.default,
            stock_number=stock,
            year=overrides.get("year", 2024),
            make=overrides.get("make", "Ford"),
            model=overrides.get("model", "Escape"),
            trim=overrides.get("trim", ""),
            price=Decimal(overrides.get("price", "29500.00")),
        )
        _put_at_frontline(vehicle, self.default)
        return vehicle

    def test_list_returns_only_frontline_vehicles(self):
        frontline_a = self._make_frontline("LIST-A")
        frontline_b = self._make_frontline("LIST-B")
        # Non-frontline vehicle should not appear. Frontline can move
        # to hold_reserved (per M5 transition table); that is the
        # simplest off-list path this test needs.
        off_lot = self._make_frontline("LIST-OFF")
        from dealer_ai.models import VEHICLE_STAGE_HOLD_RESERVED

        advance_stage(
            off_lot,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            trigger="manual",
        )
        response = self.client_pub.get(
            reverse("dealer_ai:showroom-vehicle-list")
        )
        self.assertEqual(response.status_code, 200)
        stocks = {row["stock_number"] for row in response.data["results"]}
        self.assertIn(frontline_a.stock_number, stocks)
        self.assertIn(frontline_b.stock_number, stocks)
        self.assertNotIn(off_lot.stock_number, stocks)

    def test_list_projection_includes_expected_public_fields(self):
        vehicle = self._make_frontline(
            "LIST-PROJ",
            trim="Titanium AWD",
            make="Ford",
            model="Escape",
        )
        vehicle.exterior_color = "Iconic Silver"
        vehicle.drivetrain = "AWD"
        vehicle.fuel_type = "Gasoline"
        vehicle.mileage = 12_345
        vehicle.image_url = "https://cdn.example/img/LIST-PROJ.jpg"
        vehicle.url = "https://dealer.example/vdp/LIST-PROJ"
        vehicle.save()
        response = self.client_pub.get(
            reverse("dealer_ai:showroom-vehicle-list")
        )
        row = next(
            r
            for r in response.data["results"]
            if r["stock_number"] == "LIST-PROJ"
        )
        self.assertEqual(row["year"], 2024)
        self.assertEqual(row["make"], "Ford")
        self.assertEqual(row["model"], "Escape")
        self.assertEqual(row["trim"], "Titanium AWD")
        self.assertEqual(row["exterior_color"], "Iconic Silver")
        self.assertEqual(row["drivetrain"], "AWD")
        self.assertEqual(row["fuel_type"], "Gasoline")
        self.assertEqual(row["mileage"], 12_345)
        self.assertEqual(row["image_url"], "https://cdn.example/img/LIST-PROJ.jpg")
        self.assertEqual(row["vdp_url"], "https://dealer.example/vdp/LIST-PROJ")
        self.assertIn("2024", row["display_name"])
        self.assertIn("Ford", row["display_name"])
        # Basic guard against leakage of internal cost keys.
        response_str = json.dumps(response.data, default=str)
        self.assertNotIn("dealer_cost", response_str)
        self.assertNotIn("purchase_price", response_str)

    def test_list_query_param_filters_by_substring(self):
        self._make_frontline("Q-FORD", make="Ford", model="Bronco")
        self._make_frontline("Q-TOYO", make="Toyota", model="Tacoma")
        response = self.client_pub.get(
            reverse("dealer_ai:showroom-vehicle-list") + "?q=tacoma"
        )
        stocks = [r["stock_number"] for r in response.data["results"]]
        self.assertIn("Q-TOYO", stocks)
        self.assertNotIn("Q-FORD", stocks)

    def test_list_limit_and_offset_paginate(self):
        for i in range(5):
            self._make_frontline(f"PAG-{i}")
        response = self.client_pub.get(
            reverse("dealer_ai:showroom-vehicle-list") + "?limit=2&offset=1"
        )
        self.assertEqual(response.data["limit"], 2)
        self.assertEqual(response.data["offset"], 1)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertGreaterEqual(response.data["count"], 5)

    def test_list_limit_clamped_to_max(self):
        response = self.client_pub.get(
            reverse("dealer_ai:showroom-vehicle-list") + "?limit=9999"
        )
        self.assertLessEqual(response.data["limit"], 200)


# ============================================================================
# Truthful customer-language refactor for vehicle_detail / vehicle_ask
# ============================================================================


class VehicleDetailTruthfulLanguage(TestCase):
    """SESSION_075 §5.i deferral: the stock-specific customer chat
    lookup path must return the truthful "not currently available"
    copy rather than exposing internal state (recon, stage, ETA,
    vendor)."""

    def setUp(self):
        self.default = get_default_dealership()
        self.client_pub = APIClient()

    def test_non_retail_vehicle_returns_truthful_copy(self):
        # Vehicle at frontline but no listing → not customer-visible
        # per M6.5 §5.i gate.
        vehicle = _vehicle(self.default, "M65DT-NOLIST")
        _put_at_frontline(vehicle, self.default)
        # NO listing.
        response = self.client_pub.get(
            reverse("dealer_ai:vehicle-detail", args=[vehicle.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["detail"], CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY
        )

    def test_retail_vehicle_returns_200(self):
        vehicle = _vehicle(self.default, "M65DT-OK")
        _put_at_frontline(vehicle, self.default)
        _publish_listing(vehicle, self.default)
        response = self.client_pub.get(
            reverse("dealer_ai:vehicle-detail", args=[vehicle.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_truthful_copy_matches_session075_language(self):
        """Locked exact wording per SESSION_075 §5.i."""
        self.assertEqual(
            CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY,
            "That vehicle is not currently available for retail.",
        )


class VehicleAskTruthfulLanguage(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        self.client_pub = APIClient()

    def test_non_retail_vehicle_ask_returns_truthful_copy(self):
        vehicle = _vehicle(self.default, "M65DA-NOLIST")
        _put_at_frontline(vehicle, self.default)
        # NO listing.
        response = self.client_pub.post(
            reverse("dealer_ai:vehicle-ask", args=[vehicle.pk]),
            data=json.dumps({"question": "How much?"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["detail"], CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY
        )

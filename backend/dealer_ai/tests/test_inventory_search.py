"""Inventory search regression tests — pluralization + price suffix parsing.

These cover the bugs found during Phase 8 live smoke testing where customer
prompts like "Show me F-150s under 65k" returned zero matches.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import Vehicle
from dealer_ai.services.inventory_search import parse_filters, search_vehicles


def _make_vehicle(stock, *, model, body_style="truck", condition="new", price="55000"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        make="Ford",
        model=model,
        body_style=body_style,
        condition=condition,
        price=Decimal(price),
    )


class ParseFiltersTests(TestCase):
    def test_plural_model_resolves_to_signal(self):
        f = parse_filters("Show me F-150s under 65k")
        self.assertEqual(f.model, "F-150")

    def test_plural_body_style_resolves(self):
        f = parse_filters("Looking at trucks for hauling")
        self.assertEqual(f.body_style, "truck")

    def test_price_with_k_suffix(self):
        f = parse_filters("Show me trucks under 65k")
        self.assertEqual(f.max_price, 65000.0)

    def test_price_with_dollar_and_commas(self):
        f = parse_filters("under $65,000")
        self.assertEqual(f.max_price, 65000.0)

    def test_price_below_keyword(self):
        f = parse_filters("anything below 30k")
        self.assertEqual(f.max_price, 30000.0)

    def test_price_less_than(self):
        f = parse_filters("less than 40k please")
        self.assertEqual(f.max_price, 40000.0)


class SearchVehiclesTests(TestCase):
    def test_plural_model_matches_real_inventory(self):
        v = _make_vehicle("S-1", model="F-150", price="62000")
        _make_vehicle("S-2", model="Maverick", price="33000")
        results = search_vehicles("Show me F-150s under 65k")
        ids = [r.id for r in results]
        self.assertIn(v.id, ids)
        self.assertEqual(results[0].model, "F-150")

    def test_price_ceiling_with_k_filters_inventory(self):
        cheap = _make_vehicle("S-CHEAP", model="Ranger", price="38000")
        _make_vehicle("S-EXP", model="F-150", price="78000")
        results = search_vehicles("trucks under 50k")
        ids = [r.id for r in results]
        self.assertIn(cheap.id, ids)
        # Expensive truck should fall outside the band.
        for r in results:
            self.assertLessEqual(float(r.price), 50000)

    def test_truck_keyword_alone_matches_truck_inventory(self):
        truck = _make_vehicle("T-1", model="Ranger", body_style="truck")
        _make_vehicle("S-1", model="Escape", body_style="suv")
        results = search_vehicles("Looking for trucks")
        ids = [r.id for r in results]
        self.assertIn(truck.id, ids)

"""Phase 8j — multi-brand used inventory tests.

Rules:
  - Default behavior: include all brands in inventory results.
  - Explicit "Ford only" / "I want a Ford" / "just Ford" locks make=Ford.
  - Ford vehicles always rank first; non-Ford brands appear below.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import ChatEngine, build_budget_context
from dealer_ai.services.intent_parser import parse_intent, regex_extract
from dealer_ai.services.inventory_search import search_vehicles

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(stock, *, make="Ford", model="F-150", price="40000",
                  body="truck", condition="used"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2022,
        make=make,
        model=model,
        body_style=body,
        condition=condition,
        price=Decimal(price),
    )


# ---- regex_extract / parse_intent — make_lock detection -------------------


class MakeLockParserTests(SimpleTestCase):
    def test_ford_only_locks_make(self):
        out = regex_extract("I want Ford only please")
        self.assertEqual(out.get("make"), "Ford")
        self.assertTrue(out.get("make_lock"))

    def test_only_ford_locks_make(self):
        out = regex_extract("Only Ford works for me")
        self.assertEqual(out.get("make"), "Ford")
        self.assertTrue(out.get("make_lock"))

    def test_just_ford_locks_make(self):
        out = regex_extract("Just Ford trucks please")
        self.assertEqual(out.get("make"), "Ford")
        self.assertTrue(out.get("make_lock"))

    def test_i_want_a_ford_locks_make(self):
        out = regex_extract("I want a Ford")
        self.assertEqual(out.get("make"), "Ford")
        self.assertTrue(out.get("make_lock"))

    def test_chevy_alias_normalizes(self):
        out = regex_extract("Just Chevy please")
        self.assertEqual(out.get("make"), "Chevrolet")
        self.assertTrue(out.get("make_lock"))

    def test_show_me_ford_models_does_not_lock(self):
        # Mentioning a Ford model is NOT a make lock — customer might still
        # be open to a comparable used Toyota.
        out = regex_extract("Show me F-150s under 65k")
        self.assertFalse(out.get("make_lock", False))

    def test_normal_browsing_no_lock(self):
        out = regex_extract("trucks under 30k for my family")
        self.assertFalse(out.get("make_lock", False))

    def test_parse_intent_includes_make_lock_without_llm(self):
        out = parse_intent("Ford only, used trucks", use_llm=False)
        self.assertEqual(out.get("make"), "Ford")
        self.assertTrue(out.get("make_lock"))


# ---- search_vehicles default behavior includes all brands -----------------


class SearchVehiclesMixedBrandTests(TestCase):
    def test_used_search_returns_mixed_brands_by_default(self):
        ford = _make_vehicle("F1", make="Ford", model="Ranger", price="26000")
        toyota = _make_vehicle("T1", make="Toyota", model="Tacoma", price="27000")
        chevy = _make_vehicle("C1", make="Chevrolet", model="Colorado", price="25000")

        results = search_vehicles("used trucks under 30k")
        ids = {r.id for r in results}
        self.assertIn(ford.id, ids)
        self.assertIn(toyota.id, ids)
        self.assertIn(chevy.id, ids)

    def test_ford_appears_first_when_mixed_brands_match(self):
        toyota = _make_vehicle("T2", make="Toyota", model="Tacoma", price="27000")
        ford = _make_vehicle("F2", make="Ford", model="Ranger", price="28000")

        results = search_vehicles("trucks under 30k")
        # Ford should rank first regardless of price/year tie.
        self.assertEqual(results[0].id, ford.id)

    def test_make_kwarg_filters_to_single_brand(self):
        ford = _make_vehicle("F3", make="Ford", model="Ranger", price="26000")
        toyota = _make_vehicle("T3", make="Toyota", model="Tacoma", price="27000")
        results = search_vehicles("trucks under 30k", make="Ford")
        ids = {r.id for r in results}
        self.assertIn(ford.id, ids)
        self.assertNotIn(toyota.id, ids)

    def test_empty_query_with_make_filter(self):
        _make_vehicle("F4", make="Ford", model="F-150", price="40000")
        _make_vehicle("T4", make="Toyota", model="Tundra", price="38000")
        results = search_vehicles("", limit=10, make="Ford")
        for r in results:
            self.assertEqual(r.make, "Ford")

    def test_empty_query_default_returns_mixed(self):
        _make_vehicle("F5", make="Ford", model="F-150", price="40000")
        _make_vehicle("T5", make="Toyota", model="Tundra", price="38000")
        results = search_vehicles("", limit=10)
        makes = {r.make for r in results}
        self.assertIn("Ford", makes)
        self.assertIn("Toyota", makes)


# ---- build_budget_context honours make_lock --------------------------------


class BudgetContextMakeLockTests(TestCase):
    def test_default_includes_all_brands(self):
        # Phase 8s cap: 1 fit + 2 near_fits. Seed Ford as the fit and
        # Toyota as a near_fit so both survive the cap; the contract
        # under test is "default does NOT filter by make" — that's still
        # the question this seed answers.
        ford = _make_vehicle("BF", make="Ford", model="Ranger", price="20000")
        toyota = _make_vehicle(
            "BT", make="Toyota", model="Tacoma", price="28000"
        )
        profile = {"target_monthly_payment": 500, "down_payment": 3000, "term_months": 60}
        ctx = build_budget_context(profile, "$500/mo, used trucks")
        all_ids = {v.id for v in ctx.matched_in_budget + ctx.near_fit}
        self.assertIn(ford.id, all_ids)
        self.assertIn(toyota.id, all_ids)

    def test_make_lock_filters_to_ford_only(self):
        ford = _make_vehicle("BF2", make="Ford", model="Ranger", price="20000")
        toyota = _make_vehicle("BT2", make="Toyota", model="Tacoma", price="20000")
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
            "make": "Ford",
            "make_lock": True,
        }
        ctx = build_budget_context(profile, "$500/mo, Ford only")
        ids = {v.id for v in ctx.matched_in_budget + ctx.near_fit}
        self.assertIn(ford.id, ids)
        self.assertNotIn(toyota.id, ids)

    def test_ford_first_in_budget_ranking(self):
        # Two equally-priced trucks — Ford should sort first.
        toyota = _make_vehicle("RT", make="Toyota", model="Tacoma", price="20000")
        ford = _make_vehicle("RF", make="Ford", model="Ranger", price="20000")
        profile = {"target_monthly_payment": 500, "down_payment": 3000, "term_months": 60}
        ctx = build_budget_context(profile, "$500/mo trucks")
        # First matched should be the Ford.
        ranked = ctx.matched_in_budget + ctx.near_fit
        self.assertGreater(len(ranked), 0)
        self.assertEqual(ranked[0].id, ford.id)


# ---- ChatEngine integration -----------------------------------------------


class ChatEngineMakeLockTests(TestCase):
    def test_ford_only_message_excludes_toyota(self):
        ford = _make_vehicle("CHF", make="Ford", model="Ranger", price="20000")
        _make_vehicle("CHT", make="Toyota", model="Tacoma", price="20000")
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}),  # regex picks up make_lock
                "Here's the Ford option.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Ford only please — used trucks under 30k"
        )
        ids = {v.id for v in result.matched_vehicles}
        self.assertIn(ford.id, ids)
        for v in result.matched_vehicles:
            self.assertEqual(v.make, "Ford")

    def test_default_request_includes_all_brands(self):
        ford = _make_vehicle("CHF2", make="Ford", model="Ranger", price="20000")
        toyota = _make_vehicle("CHT2", make="Toyota", model="Tacoma", price="20000")
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[json_reply({}), "Here are the trucks."]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Used trucks under 30k for my family")
        makes = {v.make for v in result.matched_vehicles}
        self.assertIn("Ford", makes)
        self.assertIn("Toyota", makes)
        # Ford ranks first.
        self.assertEqual(result.matched_vehicles[0].id, ford.id)
        # Sanity: Toyota IS in the list.
        self.assertIn(toyota.id, {v.id for v in result.matched_vehicles})

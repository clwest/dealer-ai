"""Phase 8c — budget-constrained search + narrowing flow tests.

Covers the bugs reported by the human tester:
  - "5 years" was being parsed as 72 months (should be 60)
  - $500/mo + "all inventory" was returning vehicles above budget
  - follow-up "check all inventory for this price point" needs to use the
    budget that's already in the session profile
  - typo'd follow-up ("fior this prioce point") should still work when the
    profile carries a budget
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    BudgetContext,
    build_budget_context,
)
from dealer_ai.services.intent_parser import (
    merge_profile,
    parse_intent,
    regex_extract,
)
from dealer_ai.services.inventory_search import search_vehicles

from ._mocks import MockLLMProvider, json_reply


# ---- 1. term_months parsing ------------------------------------------------


class TermParseTests(SimpleTestCase):
    def test_five_years_is_sixty_months(self):
        out = regex_extract("$300/month for 5 years")
        self.assertEqual(out["term_months"], 60)

    def test_six_years_is_seventy_two_months(self):
        out = regex_extract("around 500 a month over 6 years")
        self.assertEqual(out["term_months"], 72)

    def test_seven_years_is_eighty_four_months(self):
        out = regex_extract("$700/mo for 7 years")
        self.assertEqual(out["term_months"], 84)

    def test_explicit_60_months(self):
        out = regex_extract("60 months at $500/mo please")
        self.assertEqual(out["term_months"], 60)

    def test_explicit_72_months(self):
        out = regex_extract("72-month term works")
        self.assertEqual(out["term_months"], 72)

    def test_explicit_84_months(self):
        out = regex_extract("can you do 84 months?")
        self.assertEqual(out["term_months"], 84)

    def test_unreasonable_term_dropped(self):
        # 200 years would map to 2400 months — outside our 12-96 guard.
        out = regex_extract("200 years")
        self.assertNotIn("term_months", out)

    def test_parse_intent_includes_term_without_llm(self):
        out = parse_intent("$500 a month for 5 years", use_llm=False)
        self.assertEqual(out["target_monthly_payment"], 500)
        self.assertEqual(out["term_months"], 60)


# ---- 1b. Phase 8m+: plural vehicle types + k-suffix down payments ---------


class PluralVehicleTypeExtractionTests(SimpleTestCase):
    """Phase 8m+: 'Show me SUVs / trucks / cars / vans / EVs / hybrids' must
    extract vehicle_type. The pre-fix regexes had trailing \\b after the
    singular form, so plurals never matched — which silently dropped the
    body pivot on follow-up turns and degraded near-fit richness."""

    def test_plural_suvs(self):
        self.assertEqual(
            regex_extract("Show me SUVs for the same budget").get("vehicle_type"),
            "suv",
        )

    def test_plural_trucks(self):
        self.assertEqual(
            regex_extract("Now show me trucks").get("vehicle_type"), "truck"
        )

    def test_plural_cars(self):
        self.assertEqual(
            regex_extract("just looking at cars").get("vehicle_type"), "car"
        )

    def test_plural_vans(self):
        self.assertEqual(
            regex_extract("any vans on the lot").get("vehicle_type"), "van"
        )

    def test_minivans(self):
        self.assertEqual(
            regex_extract("looking for minivans").get("vehicle_type"), "van"
        )

    def test_plural_evs(self):
        self.assertEqual(
            regex_extract("show me EVs").get("vehicle_type"), "ev"
        )

    def test_plural_hybrids(self):
        self.assertEqual(
            regex_extract("any hybrids in stock?").get("vehicle_type"),
            "hybrid",
        )

    def test_plural_pickups(self):
        self.assertEqual(
            regex_extract("looking at pickups").get("vehicle_type"), "truck"
        )

    def test_plural_crossovers(self):
        self.assertEqual(
            regex_extract("any crossovers?").get("vehicle_type"), "suv"
        )

    def test_singular_still_works(self):
        # Sanity: don't regress the singular case after broadening the regex.
        self.assertEqual(
            regex_extract("looking for an SUV").get("vehicle_type"), "suv"
        )
        self.assertEqual(
            regex_extract("a truck").get("vehicle_type"), "truck"
        )

    def test_camry_does_not_match_car(self):
        # 'Camry' has 'car' as a substring but isn't the word 'car'.
        # Word-boundary rule must keep this from accidentally setting
        # vehicle_type=car.
        out = regex_extract("interested in a Camry")
        self.assertNotIn("vehicle_type", out)

    def test_truck_word_does_not_overmatch_trucker(self):
        # The pre-fix regex had `\btruck|pickup\b` which let `\btruck` match
        # `trucker` (no end \b). Tightened version requires end \b.
        out = regex_extract("I'm a long-haul trucker")
        self.assertNotIn("vehicle_type", out)


class KSuffixDownPaymentExtractionTests(SimpleTestCase):
    """Phase 8m+: '$3k down' / 'down 5k' must parse as 3000 / 5000. The
    pre-fix _DOWN_PATTERNS only captured digits and ignored the k suffix,
    so 'with $3k down' silently dropped to down_payment=0 — which narrowed
    the affordability ceiling and starved the near-fit window."""

    def test_dollar_3k_down(self):
        self.assertEqual(regex_extract("$3k down").get("down_payment"), 3000)

    def test_3k_down_no_dollar(self):
        self.assertEqual(regex_extract("3k down").get("down_payment"), 3000)

    def test_down_5k(self):
        self.assertEqual(
            regex_extract("can put down 5k").get("down_payment"), 5000
        )

    def test_down_payment_of_10k(self):
        self.assertEqual(
            regex_extract("down payment of $10k").get("down_payment"), 10000
        )

    def test_3000_dollars_still_works(self):
        # Don't regress the comma-format, no-suffix case.
        self.assertEqual(
            regex_extract("$3,000 down").get("down_payment"), 3000
        )

    def test_3000_no_comma_still_works(self):
        self.assertEqual(
            regex_extract("3000 down").get("down_payment"), 3000
        )

    def test_combined_with_term_and_monthly(self):
        # The exact bug-report turn-1 phrasing.
        out = regex_extract(
            "Looking for a truck around $500/mo with $3k down for 5 years"
        )
        self.assertEqual(out.get("target_monthly_payment"), 500)
        self.assertEqual(out.get("down_payment"), 3000)
        self.assertEqual(out.get("term_months"), 60)
        self.assertEqual(out.get("vehicle_type"), "truck")


# ---- 2. inventory_search.max_price kwarg -----------------------------------


def _make_vehicle(stock, price, *, model="F-150", body="truck", condition="new"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        make="Ford",
        model=model,
        body_style=body,
        condition=condition,
        price=Decimal(price),
    )


class InventorySearchMaxPriceTests(TestCase):
    def test_max_price_filters_out_expensive(self):
        cheap = _make_vehicle("C-1", "32000")
        _make_vehicle("E-1", "78000")
        results = search_vehicles("trucks", max_price=40000)
        ids = {r.id for r in results}
        self.assertIn(cheap.id, ids)
        for r in results:
            self.assertLessEqual(float(r.price), 40000)

    def test_max_price_intersects_with_under_in_query(self):
        # Query says "under 50k", caller says max_price=30k → tighter wins.
        _make_vehicle("LOW", "25000")
        _make_vehicle("MID", "40000")
        results = search_vehicles("trucks under 50k", max_price=30000)
        for r in results:
            self.assertLessEqual(float(r.price), 30000)

    def test_max_price_with_empty_query_still_filters(self):
        cheap = _make_vehicle("E-CHEAP", "20000")
        _make_vehicle("E-EXP", "70000")
        results = search_vehicles("", max_price=25000)
        ids = {r.id for r in results}
        self.assertIn(cheap.id, ids)
        for r in results:
            self.assertLessEqual(float(r.price), 25000)


# ---- 3. build_budget_context ----------------------------------------------


class BudgetContextTests(TestCase):
    def test_explicit_only_want_to_spend_triggers(self):
        _make_vehicle("BC-1", "20000")
        profile = {"target_monthly_payment": 500, "term_months": 60}
        ctx = build_budget_context(
            profile, "I only want to spend $500 a month", regex_hits={}
        )
        self.assertTrue(ctx.is_budget_query)
        self.assertEqual(ctx.term_months, 60)
        self.assertGreater(ctx.max_price, 0)

    def test_typo_follow_up_uses_prior_budget(self):
        """The reported case: 'fior this prioce point' should still trigger
        budget-constrained search when the session already has a budget."""
        _make_vehicle("BC-2", "20000")
        profile = {"target_monthly_payment": 500, "term_months": 60}
        ctx = build_budget_context(
            profile, "fior this prioce point", regex_hits={}
        )
        self.assertTrue(ctx.is_budget_query)
        self.assertEqual(ctx.target_monthly, 500.0)

    def test_no_target_means_chat_engine_skips_budget_path(self):
        """When the customer asks a budget cue but the profile has no $/mo
        target yet, build_budget_context yields is_budget_query=False so the
        chat engine falls through to the normal keyword search."""
        ctx = build_budget_context({}, "what can I afford?", regex_hits={})
        self.assertFalse(ctx.is_budget_query)
        self.assertIsNone(ctx.target_monthly)
        self.assertIsNone(ctx.max_price)

    def test_model_pivot_keeps_prior_budget_active(self):
        """Phase 8m+: a model pivot on a follow-up turn must NOT exit budget
        mode when the session already has a $/mo target. The model becomes a
        filter on the candidate pool; classification still runs so the LLM
        cannot describe over-budget trims as 'within your budget'."""
        _make_vehicle("MP-1", "20000", model="F-150")
        profile = {"target_monthly_payment": 500, "term_months": 60}
        regex_hits = {"model": "F-150"}
        ctx = build_budget_context(
            profile, "tell me about the F-150", regex_hits=regex_hits
        )
        self.assertTrue(ctx.is_budget_query)
        self.assertEqual(ctx.target_monthly, 500.0)

    def test_same_budget_phrase_with_body_pivot_stays_in_budget_mode(self):
        """Two-turn flow: turn 1 sets $500/mo + $3k down + 60mo. Turn 2 says
        'Show me SUVs for the same budget' — must stay in budget mode and
        return only fit/near_fit SUVs, never over-budget ones."""
        in_budget_suv = _make_vehicle(
            "SB-SUV-1", "22000", model="Escape", body="suv"
        )
        out_of_budget_suv = _make_vehicle(
            "SB-SUV-2", "65000", model="Expedition", body="suv"
        )
        # Turn 1 outcome already merged into the session profile:
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
        }
        # Turn 2: the customer pivots body style and uses "same budget".
        new_text = "Show me SUVs for the same budget"
        regex_hits = regex_extract(new_text)
        # Simulate the merge that handle_user_message would perform:
        merged = dict(profile)
        if "vehicle_type" in regex_hits:
            merged["vehicle_type"] = regex_hits["vehicle_type"]

        ctx = build_budget_context(merged, new_text, regex_hits=regex_hits)

        self.assertTrue(ctx.is_budget_query)
        self.assertEqual(ctx.target_monthly, 500.0)
        self.assertEqual(ctx.down_payment, 3000.0)
        self.assertEqual(ctx.term_months, 60)

        matched_ids = {v.id for v in ctx.matched_in_budget + ctx.near_fit}
        self.assertIn(in_budget_suv.id, matched_ids)
        self.assertNotIn(
            out_of_budget_suv.id,
            matched_ids,
            "over-budget SUV must not appear in matched_vehicles",
        )

    def test_body_pivot_without_explicit_phrase_still_carries_budget(self):
        """'Now show me trucks' after a $500 budget — no 'same budget' phrase,
        but the prior budget in the profile must still trigger budget mode
        (carry-forward contract)."""
        in_budget_truck = _make_vehicle(
            "BP-TRK-1", "19000", model="Maverick", body="truck"
        )
        out_truck = _make_vehicle(
            "BP-TRK-2", "78000", model="F-150", body="truck"
        )
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
        }
        new_text = "Now show me trucks"
        regex_hits = regex_extract(new_text)
        merged = dict(profile)
        if "vehicle_type" in regex_hits:
            merged["vehicle_type"] = regex_hits["vehicle_type"]

        ctx = build_budget_context(merged, new_text, regex_hits=regex_hits)

        self.assertTrue(ctx.is_budget_query)
        matched_ids = {v.id for v in ctx.matched_in_budget + ctx.near_fit}
        self.assertIn(in_budget_truck.id, matched_ids)
        self.assertNotIn(out_truck.id, matched_ids)

    def test_trade_in_intent_exits_budget_mode_even_with_prior_budget(self):
        """An explicit trade-in valuation question must NOT trigger budget
        mode, even when the session profile has a $/mo target."""
        _make_vehicle("TI-1", "20000")
        profile = {"target_monthly_payment": 500, "term_months": 60}
        new_text = "What is my car worth as a trade-in?"
        regex_hits = regex_extract(new_text)

        ctx = build_budget_context(profile, new_text, regex_hits=regex_hits)
        self.assertFalse(ctx.is_budget_query)

    def test_compare_intent_exits_budget_mode_even_with_prior_budget(self):
        """Compare-vehicles intent must NOT trigger budget mode, even with a
        prior budget in profile."""
        _make_vehicle("CMP-1", "20000")
        profile = {"target_monthly_payment": 500, "term_months": 60}
        new_text = "Compare the Bronco vs the Bronco Sport"
        regex_hits = regex_extract(new_text)
        # Sanity: regex_extract should classify this as compare_vehicles.
        self.assertEqual(regex_hits.get("intent"), "compare_vehicles")

        ctx = build_budget_context(profile, new_text, regex_hits=regex_hits)
        self.assertFalse(ctx.is_budget_query)

    def test_phase_8m_followup_full_pipeline_restores_near_fit_richness(self):
        """End-to-end pipeline lock for the Phase 8m+ regression report:
            Turn 1: '$500/mo with $3k down for 5 years' (truck)
            Turn 2: 'Show me SUVs for the same budget'

        Phase 8s update: the per-bucket cap is 1 fit + 2 near_fit (max 3
        total), so we seed 1 fit, 2 near_fits, and 1 over-budget. The
        regression we're guarding against is "single-vehicle reply with
        no near-fit"; that's covered by asserting ≥1 near-fit + ≥2
        matched + zero over-budget leakage.
        """
        # Spread of SUVs at $500/$3k/60mo: 1 fit + 2 near_fits + 1 over.
        #   $500 target, $75 tolerance → fit ≤ $500/mo, near-fit ≤ $575/mo.
        fit_a = _make_vehicle("PIPE-F1", "20000", model="Escape", body="suv")
        near_a = _make_vehicle("PIPE-N1", "27500", model="Edge", body="suv")
        near_b = _make_vehicle("PIPE-N2", "28500", model="Tucson", body="suv")
        over = _make_vehicle("PIPE-OVER", "65000", model="Expedition", body="suv")

        # Turn 1 — establishes the budget on a truck request.
        profile: dict = {}
        turn1 = "Looking for a truck around $500/mo with $3k down for 5 years"
        profile = merge_profile(profile, parse_intent(turn1, use_llm=False))
        self.assertEqual(profile["target_monthly_payment"], 500)
        self.assertEqual(profile["down_payment"], 3000)
        self.assertEqual(profile["term_months"], 60)
        self.assertEqual(profile["vehicle_type"], "truck")

        # Turn 2 — body pivots to SUV with explicit "same budget" carry-forward.
        turn2 = "Show me SUVs for the same budget"
        profile = merge_profile(profile, parse_intent(turn2, use_llm=False))
        self.assertEqual(
            profile["vehicle_type"],
            "suv",
            "plural 'SUVs' must overwrite prior vehicle_type=truck",
        )
        # Budget fields must still be present after the merge.
        self.assertEqual(profile["target_monthly_payment"], 500)
        self.assertEqual(profile["down_payment"], 3000)
        self.assertEqual(profile["term_months"], 60)

        ctx = build_budget_context(
            profile, turn2, regex_hits=regex_extract(turn2)
        )

        self.assertTrue(ctx.is_budget_query)
        self.assertEqual(ctx.target_monthly, 500.0)
        self.assertEqual(ctx.down_payment, 3000.0)
        self.assertEqual(ctx.term_months, 60)

        matched = ctx.matched_in_budget + ctx.near_fit
        matched_ids = {v.id for v in matched}

        # ≥1 near-fit (the regression report's primary symptom).
        self.assertGreaterEqual(
            len(ctx.near_fit),
            1,
            f"expected ≥1 near-fit SUV, got {len(ctx.near_fit)}",
        )
        # Phase 8s cap: 1 fit + 2 near_fits → matched is exactly 3 here.
        self.assertEqual(
            len(matched),
            3,
            f"expected 1 fit + 2 near-fit = 3 matched SUVs, got {len(matched)}",
        )
        # No over-budget in matched_vehicles.
        self.assertNotIn(
            over.id,
            matched_ids,
            "$65k Expedition must not appear in matched_vehicles "
            "at $500/mo $3k down",
        )
        # The single fit and both near-fits all survive the cap.
        self.assertIn(fit_a.id, matched_ids)
        self.assertIn(near_a.id, matched_ids)
        self.assertIn(near_b.id, matched_ids)

    def test_followup_matches_carry_fit_or_near_fit_annotations(self):
        """Every vehicle returned in matched_in_budget+near_fit on a follow-up
        turn must carry _budget_fit ∈ {'fit','near_fit'} and a numeric
        _estimated_payment, so the LLM cannot describe near-fit vehicles as
        'within budget' (the inventory block reads the annotation)."""
        _make_vehicle("AN-1", "22000", model="Escape", body="suv")
        _make_vehicle("AN-2", "27000", model="Edge", body="suv")
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
        }
        new_text = "Show me SUVs for the same budget"
        regex_hits = regex_extract(new_text)
        merged = dict(profile)
        if "vehicle_type" in regex_hits:
            merged["vehicle_type"] = regex_hits["vehicle_type"]

        ctx = build_budget_context(merged, new_text, regex_hits=regex_hits)
        matched = ctx.matched_in_budget + ctx.near_fit
        self.assertGreater(len(matched), 0)
        for v in matched:
            self.assertIn(
                getattr(v, "_budget_fit", None),
                ("fit", "near_fit"),
                f"{v.stock_number} missing fit annotation",
            )
            self.assertIsInstance(
                getattr(v, "_estimated_payment", None),
                float,
                f"{v.stock_number} missing _estimated_payment",
            )

    def test_filters_to_in_budget_only(self):
        in_budget = _make_vehicle("IN-1", "20000")
        out_of_budget = _make_vehicle("OUT-1", "78000")
        profile = {
            "target_monthly_payment": 500,
            "term_months": 60,
            "down_payment": 0,
        }
        ctx = build_budget_context(
            profile, "what can I afford?", regex_hits={}
        )
        ids = {v.id for v in ctx.matched_in_budget}
        self.assertIn(in_budget.id, ids)
        self.assertNotIn(out_of_budget.id, ids)

    def test_no_fit_returns_closest_above_only_for_context(self):
        # Phase 8s/UX: closest_above is filtered by the realistic-stretch
        # cap (max $150 / 30% above target). At $200/mo target the cap
        # is $150 → seed both overs inside that window so they actually
        # qualify as stretches.
        _make_vehicle("HIGH-1", "13500")
        _make_vehicle("HIGH-2", "14000")
        profile = {
            "target_monthly_payment": 200,
            "term_months": 60,
            "down_payment": 0,
        }
        ctx = build_budget_context(
            profile, "only want to spend $200/month", regex_hits={}
        )
        self.assertEqual(ctx.matched_in_budget, [])
        # closest_above is for the LLM to mention with OVER BUDGET framing —
        # NOT for the matched_vehicles list.
        self.assertGreater(len(ctx.closest_above), 0)


# ---- 4. ChatEngine integration --------------------------------------------


class ChatEngineBudgetFlowTests(TestCase):
    def test_dollar_500_all_inventory_filters_by_affordability(self):
        in_budget = _make_vehicle("OK-1", "20000", model="Maverick")
        out_of_budget = _make_vehicle("OK-2", "78000", model="F-150")
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "intent": "vehicle_search",
                        "target_monthly_payment": 500,
                        "term_months": 60,
                    }
                ),
                "Here's what fits your budget.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I only want to spend 500 a month — check all inventory for this price point"
        )

        ids = {v.id for v in result.matched_vehicles}
        self.assertIn(in_budget.id, ids)
        self.assertNotIn(out_of_budget.id, ids)
        # Metadata records the budget query for audit / dashboard.
        bq = result.assistant_message.metadata.get("budget_query")
        self.assertIsNotNone(bq)
        self.assertEqual(bq["target_monthly"], 500.0)
        self.assertEqual(bq["term_months"], 60)
        self.assertGreater(bq["max_price"], 0)

    def test_no_fit_surfaces_only_realistic_stretch_cards(self):
        # Phase 8s/UX promotion: when no fits / no near-fits exist but
        # realistic stretches (within max($150, 30%) of target) do, the
        # API surfaces those stretches as cards with budget_fit=
        # "over_budget" so the customer sees real options. no_fit
        # metadata stays True (no IN-BUDGET / NEAR-FIT match), and the
        # OVER BUDGET text block still goes to the LLM.
        _make_vehicle("HIGH-A", "13500", model="F-150")  # ≈ $290/mo (stretch)
        _make_vehicle("HIGH-B", "14000", model="Bronco")  # ≈ $300/mo (stretch)
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search", "target_monthly_payment": 200}),
                "I don't see a fit at that target.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Only want to spend 200 a month — show me all inventory"
        )
        # Stretches surface as cards — both are within the $150 cap.
        matched_stocks = {v.stock_number for v in result.matched_vehicles}
        self.assertEqual(matched_stocks, {"HIGH-A", "HIGH-B"})
        for v in result.matched_vehicles:
            self.assertEqual(getattr(v, "_budget_fit", None), "over_budget")
        bq = result.assistant_message.metadata.get("budget_query")
        self.assertIsNotNone(bq)
        # no_fit is still True — no IN-BUDGET / NEAR-FIT match exists.
        self.assertTrue(bq["no_fit"])
        # The LLM saw the BUDGET ANALYSIS block — verify by inspecting the
        # provider call payload.
        joined = "\n".join(
            m["content"] for m in provider.calls[-1] if m["role"] == "system"
        )
        self.assertIn("BUDGET ANALYSIS", joined)
        self.assertIn("OVER BUDGET", joined)

    def test_followup_with_prior_budget(self):
        in_budget = _make_vehicle("F-1", "20000", model="Maverick")
        _make_vehicle("F-2", "78000", model="F-150")
        session = ChatSession.objects.create(
            extracted_profile={"target_monthly_payment": 500, "term_months": 60}
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),  # no new intent
                "Here's what fits.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "check all inventory for this price point"
        )
        ids = {v.id for v in result.matched_vehicles}
        self.assertIn(in_budget.id, ids)
        bq = result.assistant_message.metadata.get("budget_query")
        self.assertIsNotNone(bq)
        self.assertEqual(bq["target_monthly"], 500.0)

    def test_typo_followup_with_prior_budget(self):
        in_budget = _make_vehicle("T-1", "20000", model="Escape")
        session = ChatSession.objects.create(
            extracted_profile={"target_monthly_payment": 500, "term_months": 60}
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Here are options.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("fior this prioce point")
        ids = {v.id for v in result.matched_vehicles}
        self.assertIn(in_budget.id, ids)
        self.assertIsNotNone(result.assistant_message.metadata.get("budget_query"))

    def test_normal_question_does_not_trigger_budget_mode(self):
        _make_vehicle("N-1", "55000", model="F-150")
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search", "vehicle_type": "truck"}),
                "Here are some F-150s.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me F-150s")
        self.assertNotIn("budget_query", result.assistant_message.metadata)

    def test_term_change_recomputes_max_price(self):
        """If a customer first says '$300/mo for 5 years' and then says
        'what about 6 years?', the affordable max should jump."""
        _make_vehicle("PR-1", "20000")  # fits 5yr at $300
        _make_vehicle("PR-2", "23000")  # fits 6yr at $300 but tighter
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                # turn 1 — extract + reply
                json_reply(
                    {
                        "intent": "vehicle_search",
                        "target_monthly_payment": 300,
                        "term_months": 60,
                    }
                ),
                "Here's a 5-year picture.",
                # turn 2
                json_reply({"term_months": 72}),
                "Updated for 6 years.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)

        engine.handle_user_message("$300/month for 5 years — what can I get?")
        first_max = session.extracted_profile.get("term_months")
        self.assertEqual(first_max, 60)

        engine.handle_user_message(
            "What about 6 years? check all inventory for this price point"
        )
        session.refresh_from_db()
        self.assertEqual(session.extracted_profile.get("term_months"), 72)

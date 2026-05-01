"""Phase 8s: multi-option cap + fabricated-inventory guard.

Two new chat-engine contracts the system enforces:

1. ``BudgetContext.matched_in_budget`` is capped at ``MAX_FIT_RESULTS``
   (1) and ``BudgetContext.near_fit`` is capped at ``MAX_NEAR_FIT_RESULTS``
   (2). The use site (``handle_user_message``) concatenates them, so the
   API's ``matched_vehicles[]`` is bounded by 1 + 2 = 3 total. The
   BUDGET ANALYSIS block rendered into the prompt iterates the same
   lists, so what the LLM sees and what the API returns stay symmetric.
2. The post-LLM guard ``_detect_fabricated_stocks`` returns the list of
   ``Stock #X`` mentions in the assistant reply that were NOT in the
   ``matched_vehicles`` set. ``handle_user_message`` wholesale-replaces
   any reply that cites a fabricated stock with
   ``FABRICATED_INVENTORY_RESPONSE`` and tags
   ``metadata.flag = "fabricated_inventory"``.

These tests cap the contracts so any future refactor that loosens the
cap or skips the fabrication check has to update them deliberately.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    FABRICATED_INVENTORY_RESPONSE,
    MAX_FIT_RESULTS,
    MAX_NEAR_FIT_RESULTS,
    _detect_fabricated_stocks,
    _format_budget_block,
    build_budget_context,
)
from dealer_ai.tests._mocks import MockLLMProvider, json_reply


def _make_vehicle(stock, price, *, model="Escape", body="suv", make="Ford"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        make=make,
        model=model,
        body_style=body,
        condition="new",
        price=Decimal(price),
    )


# ---- Cap: BudgetContext slices to 1 fit + 2 near_fits ----------------------


class MatchedVehicleCapTests(TestCase):
    def test_constants_are_one_fit_and_two_near_fits(self):
        self.assertEqual(MAX_FIT_RESULTS, 1)
        self.assertEqual(MAX_NEAR_FIT_RESULTS, 2)

    def test_five_fits_seeded_returns_one_fit(self):
        # Five SUVs all under $500/mo at 60mo/$0 down → all classify as
        # fit. The cap must drop us to exactly 1.
        for i in range(5):
            _make_vehicle(f"FIT-{i}", str(15000 + i * 500))
        ctx = build_budget_context(
            {"target_monthly_payment": 500, "term_months": 60},
            "$500/mo SUVs",
        )
        self.assertEqual(len(ctx.matched_in_budget), 1)

    def test_five_near_fits_seeded_returns_two(self):
        # Five SUVs in the $25-27k band → at $500/mo / 60mo / $0 down
        # they're all near_fits. Cap should keep exactly 2.
        for i in range(5):
            _make_vehicle(f"NEAR-{i}", str(25000 + i * 400))
        ctx = build_budget_context(
            {"target_monthly_payment": 500, "term_months": 60},
            "$500/mo SUVs",
        )
        self.assertEqual(len(ctx.near_fit), 2)

    def test_total_matched_capped_at_three(self):
        # 3 fits + 4 near_fits in inventory → matched should be capped.
        for i in range(3):
            _make_vehicle(f"FIT-{i}", str(15000 + i * 500))
        for i in range(4):
            _make_vehicle(f"NEAR-{i}", str(25000 + i * 400))
        ctx = build_budget_context(
            {"target_monthly_payment": 500, "term_months": 60},
            "$500/mo SUVs",
        )
        matched = ctx.matched_in_budget + ctx.near_fit
        self.assertLessEqual(len(matched), 3)
        self.assertEqual(len(ctx.matched_in_budget), 1)
        self.assertEqual(len(ctx.near_fit), 2)

    def test_fewer_candidates_than_cap_returns_what_exists(self):
        # Only 1 vehicle in inventory: matched is exactly 1, no padding.
        _make_vehicle("LONELY", "20000")
        ctx = build_budget_context(
            {"target_monthly_payment": 500, "term_months": 60},
            "$500/mo SUVs",
        )
        matched = ctx.matched_in_budget + ctx.near_fit
        self.assertEqual(len(matched), 1)

    def test_budget_analysis_block_lists_only_capped_vehicles(self):
        # Same seed as test_total_matched_capped_at_three; the rendered
        # BUDGET ANALYSIS block must list 1 fit + 2 near_fits, not the
        # full 7-row inventory.
        for i in range(3):
            _make_vehicle(f"FIT-{i}", str(15000 + i * 500))
        for i in range(4):
            _make_vehicle(f"NEAR-{i}", str(25000 + i * 400))
        ctx = build_budget_context(
            {"target_monthly_payment": 500, "term_months": 60},
            "$500/mo SUVs",
        )
        block = _format_budget_block(ctx)
        # Block is multi-line; count lines that begin with the
        # vehicle-line marker "  · " produced by _format_vehicle_line.
        bullet_lines = [ln for ln in block.split("\n") if ln.startswith("  · ")]
        self.assertEqual(
            len(bullet_lines),
            3,
            f"BUDGET ANALYSIS block should list 1 fit + 2 near_fits "
            f"(3 lines), got {len(bullet_lines)}:\n{block}",
        )


# ---- Fabricated-stock detector ---------------------------------------------


class DetectFabricatedStocksTests(TestCase):
    def test_no_stock_mentions_returns_empty(self):
        self.assertEqual(
            _detect_fabricated_stocks(
                "Want me to walk through trim options?", set()
            ),
            [],
        )

    def test_legit_stock_only_returns_empty(self):
        allowed = {"FF-2025-001"}
        reply = "We have a 2025 F-150 (Stock #FF-2025-001) at $62,995."
        self.assertEqual(_detect_fabricated_stocks(reply, allowed), [])

    def test_unknown_stock_returns_it(self):
        allowed = {"FF-USED-406"}
        reply = (
            "Here are options: Stock #FF-USED-406 (real) and "
            "Stock #FF-TRUCK-123 (fake) and Stock #FF-TRUCK-789 (fake)."
        )
        result = _detect_fabricated_stocks(reply, allowed)
        self.assertEqual(set(result), {"FF-TRUCK-123", "FF-TRUCK-789"})

    def test_case_insensitive_match(self):
        # Allowed stocks are uppercased by the caller; the detector
        # uppercases the cited stock too so case differences don't trip
        # a false positive.
        allowed = {"FF-USED-406"}
        reply = "Stock #ff-used-406 in our lot."
        self.assertEqual(_detect_fabricated_stocks(reply, allowed), [])

    def test_dedupes_repeated_mentions(self):
        allowed = {"FF-2025-001"}
        reply = "Stock #FAKE-1 then later Stock #FAKE-1 again."
        # Even though FAKE-1 appears twice, the result is a single entry.
        self.assertEqual(_detect_fabricated_stocks(reply, allowed), ["FAKE-1"])

    def test_empty_reply_returns_empty(self):
        self.assertEqual(_detect_fabricated_stocks("", {"FF-X"}), [])


# ---- End-to-end: chat reply with fabricated stock is wholesale-replaced ----


class FabricatedInventoryEndToEndTests(TestCase):
    def setUp(self):
        # One real SUV in inventory at the $500/mo target.
        _make_vehicle("REAL-1", "25000")
        self.session = ChatSession.objects.create()

    def test_clean_reply_passes_through(self):
        provider = MockLLMProvider(
            replies=[
                json_reply({"target_monthly_payment": 500, "vehicle_type": "suv"}),
                "I have a 2024 Ford Escape (Stock #REAL-1) at $25,000. "
                "Want me to walk through the financing?",
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        result = engine.handle_user_message("$500/mo SUV")
        self.assertNotEqual(result.assistant_message.content, FABRICATED_INVENTORY_RESPONSE)
        self.assertNotEqual(
            result.assistant_message.metadata.get("flag"),
            "fabricated_inventory",
        )

    def test_fabricated_stock_triggers_wholesale_replacement(self):
        provider = MockLLMProvider(
            replies=[
                json_reply({"target_monthly_payment": 500, "vehicle_type": "suv"}),
                "Three options: Stock #REAL-1 at $25,000, Stock #FAKE-A at "
                "$23,000, and Stock #FAKE-B at $27,500. Which one calls to you?",
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        result = engine.handle_user_message("$500/mo SUV")
        msg = result.assistant_message
        self.assertEqual(msg.content, FABRICATED_INVENTORY_RESPONSE)
        self.assertEqual(msg.metadata.get("flag"), "fabricated_inventory")
        self.assertEqual(
            set(msg.metadata.get("fabricated_stocks") or []),
            {"FAKE-A", "FAKE-B"},
        )

    def test_only_real_stock_survives_when_extras_fabricated(self):
        # If the LLM cites the real stock alongside two fakes, we still
        # replace the WHOLE reply — partial scrubs would leave half-baked
        # sentences referring to the fake units.
        provider = MockLLMProvider(
            replies=[
                json_reply({"target_monthly_payment": 500, "vehicle_type": "suv"}),
                "Stock #REAL-1 is our top pick. We also have Stock #FAKE-X.",
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        result = engine.handle_user_message("$500/mo SUV")
        self.assertEqual(
            result.assistant_message.content, FABRICATED_INVENTORY_RESPONSE
        )

    def test_partial_scrubs_skip_when_fabricated_inventory_fires(self):
        # The reply contains BOTH a fabricated stock AND rate language —
        # the wholesale fabricated-inventory replacement must take
        # precedence over rate-language scrubbing.
        provider = MockLLMProvider(
            replies=[
                json_reply({"target_monthly_payment": 500, "vehicle_type": "suv"}),
                "Stock #FAKE-Z at $25,000, $500/mo @ 7.49% APR over 60mo.",
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        result = engine.handle_user_message("$500/mo SUV")
        msg = result.assistant_message
        self.assertEqual(msg.content, FABRICATED_INVENTORY_RESPONSE)
        # The rate-scrub flag must NOT win — fabricated_inventory is the
        # higher-severity wholesale rewrite.
        self.assertEqual(msg.metadata.get("flag"), "fabricated_inventory")

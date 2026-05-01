"""Item 13–15 — tighten leaks observed in live UI testing.

13. Debug stocks (RANGER-DBG etc.) excluded from customer-facing
    matched_vehicles via `customer_visible_vehicles()`.
14. Model-followup anchor filter — drops brochure sentences that
    don't reference a constraint, comparison, or card data.
15. Cash-mode comparison reply rule — system message injected
    when cash_mode + ≥ 2 cards.

Plus the extended cash-mode financing scrub patterns (item 9
augmentation).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    LIST_SHAPE_FALLBACK,
    _format_cash_mode_block,
    customer_visible_vehicles,
    scrub_financing_language,
    scrub_followup_anchors,
)
from dealer_ai.services.inventory_search import search_vehicles

from ._mocks import MockLLMProvider, json_reply


# ---- Item 13: customer_visible_vehicles excludes debug stocks -----------


class CustomerVisibleVehiclesTests(TestCase):
    def _seed_real_and_debug(self):
        real = Vehicle.objects.create(
            stock_number="FF-USED-REAL", year=2019, make="Ford",
            model="Ranger", body_style="truck", condition="used",
            price=Decimal("26995"), drivetrain="4x4",
        )
        # Various debug-shaped stocks that should be excluded.
        Vehicle.objects.create(
            stock_number="RANGER-DBG", year=2019, make="Ford",
            model="Ranger", body_style="truck", condition="used",
            price=Decimal("26995"), drivetrain="4x4",
        )
        Vehicle.objects.create(
            stock_number="DEBUG-001", year=2020, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"), drivetrain="4x4",
        )
        Vehicle.objects.create(
            stock_number="TEST-A", year=2018, make="Toyota",
            model="Camry", body_style="car", condition="used",
            price=Decimal("12000"), drivetrain="FWD",
        )
        Vehicle.objects.create(
            stock_number="__SCRATCH", year=2017, make="Honda",
            model="Accord", body_style="car", condition="used",
            price=Decimal("11000"), drivetrain="FWD",
        )
        return real

    def test_helper_excludes_dbg_suffix(self):
        self._seed_real_and_debug()
        stocks = set(
            customer_visible_vehicles().values_list(
                "stock_number", flat=True
            )
        )
        self.assertIn("FF-USED-REAL", stocks)
        self.assertNotIn("RANGER-DBG", stocks)
        self.assertNotIn("DEBUG-001", stocks)
        self.assertNotIn("TEST-A", stocks)
        self.assertNotIn("__SCRATCH", stocks)

    def test_search_vehicles_excludes_debug(self):
        # search_vehicles is the keyword-search path the chat
        # engine uses for non-budget turns. It must filter too.
        self._seed_real_and_debug()
        results = search_vehicles("ranger truck", limit=10)
        stocks = {v.stock_number for v in results}
        self.assertIn("FF-USED-REAL", stocks)
        self.assertNotIn("RANGER-DBG", stocks)

    def test_chat_engine_does_not_surface_dbg_stock(self):
        # End-to-end: the dev-DB pollution case the user reported.
        # Both a real Ranger and a RANGER-DBG twin exist; the
        # customer must only see the real one.
        self._seed_real_and_debug()
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "The Ranger is close at $517/mo. Want a look?",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I want a 4WD truck for $500/mo with $3k down"
        )
        stocks = {v.stock_number for v in result.matched_vehicles}
        self.assertNotIn("RANGER-DBG", stocks)
        self.assertNotIn("DEBUG-001", stocks)


# ---- Item 9 extension: cash-mode financing scrub catches more -----------


class ExtendedFinancingScrubTests(SimpleTestCase):
    def test_approved_credit_phrase_stripped(self):
        text = (
            "The Fusion is at $11,995. With approved credit your "
            "payment lands around $227. Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("approved credit", cleaned.lower())
        self.assertIn("$11,995", cleaned)
        self.assertIn("Want a look?", cleaned)

    def test_low_monthly_payment_phrase_stripped(self):
        text = (
            "The Camry is great. Low monthly payment commuter "
            "for sure. Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("monthly payment", cleaned.lower())
        self.assertNotIn("payment commuter", cleaned.lower())
        self.assertIn("Want a look?", cleaned)

    def test_payment_commuter_phrase_stripped(self):
        text = (
            "The Sonata is a payment commuter pick. Sound good?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("payment commuter", cleaned.lower())

    def test_wac_spaced_variant_stripped(self):
        text = (
            "The Accord at $12,995. (W A C — with approved "
            "credit). Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("W A C", cleaned)
        self.assertNotIn("approved credit", cleaned.lower())

    def test_all_extended_phrases_no_op_off_cash_mode(self):
        # Sanity: extended phrases still pass through when
        # cash_mode is False (normal finance flow).
        text = (
            "With approved credit, the Camry lands at $227/mo. "
            "Low monthly payment commuter."
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=False
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)


# ---- Item 14: model-followup anchor filter ------------------------------


class ScrubFollowupAnchorsUnitTests(SimpleTestCase):
    """Pure-function coverage. Drops brochure statements with no
    constraint / comparison / card-data anchor.
    """

    class _FakeCard:
        def __init__(self, **kw):
            self.make = kw.get("make", "")
            self.model = kw.get("model", "")
            self.features = kw.get("features", [])

    MODE = "model_followup"

    def _ranger(self):
        return self._FakeCard(
            make="Ford", model="Ranger",
            features=["Tow Package", "FX4 Off-Road", "Sync 3"],
        )

    def test_mode_not_followup_no_op(self):
        text = "Generic brochure copy with no anchors."
        cleaned, changed = scrub_followup_anchors(
            text, mode=None, matched=[self._ranger()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_no_matched_no_op(self):
        text = "Generic brochure copy with no anchors."
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_brochure_statement_dropped(self):
        # "great option for those" / "feature-packed vehicle" /
        # "standout features" — all anchorless.
        text = (
            "It's a great option for those who love adventure. "
            "The Ranger has a 2.3L EcoBoost engine that gets "
            "good gas mileage. Want a look?"
        )
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[self._ranger()]
        )
        self.assertTrue(changed)
        # Brochure sentence stripped.
        self.assertNotIn("great option for those", cleaned)
        # Anchored sentence preserved (Ranger + gas mileage).
        self.assertIn("Ranger", cleaned)
        self.assertIn("gas mileage", cleaned)

    def test_constraint_fit_sentence_preserved(self):
        text = (
            "The Ranger fits your $500 target with the 4WD you "
            "wanted. Want a look?"
        )
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[self._ranger()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_comparison_sentence_preserved(self):
        text = (
            "The Ranger is smaller than the F-150 you saw earlier. "
            "Sound good?"
        )
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[self._ranger()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_card_data_anchor_preserved(self):
        # Mentions "Ranger" (model) → has card-data anchor.
        text = "The Ranger is a solid pickup. Want a look?"
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[self._ranger()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_feature_anchor_preserved(self):
        text = (
            "The truck has the FX4 Off-Road package. Want a look?"
        )
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[self._ranger()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_pure_brochure_falls_back(self):
        text = (
            "Standout features and feature-packed design define "
            "this truck. It's a true adventure companion."
        )
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[self._ranger()]
        )
        # Every statement is anchorless → fallback fires.
        self.assertTrue(changed)
        self.assertEqual(cleaned, LIST_SHAPE_FALLBACK)

    def test_trailing_question_kept_when_anchored_prose_remains(self):
        # The trailing question is preserved as the soft close
        # WHEN there's enough anchored prose to keep the reply
        # coherent. Brochure statements drop out around it.
        text = (
            "Standout features and a feature-packed design. "
            "The Ranger fits your $500 target with the 4WD you "
            "wanted. Want a closer look?"
        )
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[self._ranger()]
        )
        self.assertTrue(changed)
        self.assertIn("Want a closer look?", cleaned)
        self.assertIn("Ranger", cleaned)
        self.assertNotIn("Standout features", cleaned)

    def test_only_question_survives_falls_back(self):
        # When stripping leaves ONLY the trailing question, the
        # 5-word coherence threshold fails and the fallback fires
        # — a 3-word reply isn't a substantive response.
        text = (
            "Generic brochure here. Standout features galore. "
            "Want a closer look?"
        )
        cleaned, changed = scrub_followup_anchors(
            text, mode=self.MODE, matched=[self._ranger()]
        )
        self.assertTrue(changed)
        self.assertEqual(cleaned, LIST_SHAPE_FALLBACK)


# ---- Item 15: cash-mode comparison reply rule ---------------------------


class FormatCashModeBlockTests(TestCase):
    def _seed_three_cars(self):
        v1 = Vehicle.objects.create(
            stock_number="C-1", year=2014, make="Honda",
            model="Accord", body_style="car", condition="used",
            price=Decimal("12995"), mileage=85000, drivetrain="FWD",
        )
        v2 = Vehicle.objects.create(
            stock_number="C-2", year=2015, make="Toyota",
            model="Camry", body_style="car", condition="used",
            price=Decimal("13495"), mileage=72000, drivetrain="FWD",
        )
        v3 = Vehicle.objects.create(
            stock_number="C-3", year=2017, make="Hyundai",
            model="Sonata", body_style="car", condition="used",
            price=Decimal("10995"), mileage=92000, drivetrain="FWD",
        )
        return [v1, v2, v3]

    def test_zero_or_one_card_no_block(self):
        self.assertEqual(_format_cash_mode_block([]), "")
        cards = self._seed_three_cars()
        self.assertEqual(_format_cash_mode_block(cards[:1]), "")

    def test_two_or_more_cards_emit_block(self):
        cards = self._seed_three_cars()
        block = _format_cash_mode_block(cards)
        self.assertIn("CASH-MODE PRESENTATION", block)
        self.assertIn("paying CASH", block)
        # Forbids financing language explicitly.
        self.assertIn("DO NOT mention monthly payments", block)
        self.assertIn("financing", block)
        self.assertIn("approved credit", block)
        # Compares dimensions a cash buyer cares about.
        self.assertIn("price", block.lower())
        self.assertIn("mileage", block.lower())
        self.assertIn("reliability", block.lower())
        # Names the actual vehicles.
        self.assertIn("Honda Accord", block)
        self.assertIn("Toyota Camry", block)
        self.assertIn("Hyundai Sonata", block)
        # Includes a tradeoff-question template.
        self.assertIn(
            "lowest price, or long-term reliability", block
        )

    def test_block_uses_customer_drivetrain_label(self):
        # FWD → "FWD" (passthrough). Verify drivetrain renders
        # via customer_drivetrain_label so card and block agree.
        cards = self._seed_three_cars()
        block = _format_cash_mode_block(cards)
        self.assertIn("drivetrain FWD", block)


class CashModeBlockIntegrationTests(TestCase):
    """End-to-end: cash query with multiple cards injects the
    comparison block as a system message before the LLM call.
    """

    def _seed_cars(self):
        Vehicle.objects.create(
            stock_number="CC-1", year=2014, make="Ford",
            model="Fusion", body_style="car", condition="used",
            price=Decimal("11995"), mileage=85000, drivetrain="FWD",
        )
        Vehicle.objects.create(
            stock_number="CC-2", year=2015, make="Toyota",
            model="Camry", body_style="car", condition="used",
            price=Decimal("13495"), mileage=72000, drivetrain="FWD",
        )

    def test_cash_block_appears_in_provider_messages(self):
        self._seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "The Fusion at $11,995. The Camry at $13,495. "
                "Sound good?",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message(
            "cheap car cash, gas mileage"
        )
        # The 2nd LLM call (the reply call) should have the
        # cash-mode block among its system messages.
        reply_call = provider.calls[-1]
        cash_block_seen = any(
            "CASH-MODE PRESENTATION" in m.get("content", "")
            for m in reply_call
            if m.get("role") == "system"
        )
        self.assertTrue(
            cash_block_seen,
            "Cash-mode block should be injected when cash_mode "
            "AND len(matched) >= 2",
        )

    def test_no_cash_block_when_one_card(self):
        Vehicle.objects.create(
            stock_number="C-LONE", year=2014, make="Ford",
            model="Fusion", body_style="car", condition="used",
            price=Decimal("11995"), mileage=85000, drivetrain="FWD",
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "The Fusion at $11,995. Sound good?",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message(
            "cheap car cash, gas mileage"
        )
        reply_call = provider.calls[-1]
        cash_block_seen = any(
            "CASH-MODE PRESENTATION" in m.get("content", "")
            for m in reply_call
            if m.get("role") == "system"
        )
        # Only 1 card → no comparison to make → block skipped.
        self.assertFalse(cash_block_seen)

    def test_no_cash_block_in_finance_flow(self):
        # Truck $500/mo flow — cash_mode=False, so no block.
        Vehicle.objects.create(
            stock_number="T-1", year=2019, make="Ford",
            model="Ranger", body_style="truck", condition="used",
            price=Decimal("26995"), drivetrain="4x4",
        )
        Vehicle.objects.create(
            stock_number="T-2", year=2018, make="Toyota",
            model="Tundra", body_style="truck", condition="used",
            price=Decimal("35995"), drivetrain="4x4",
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), "Some trucks. Want a look?"]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message(
            "4WD truck around $500/mo with $3k down"
        )
        reply_call = provider.calls[-1]
        cash_block_seen = any(
            "CASH-MODE PRESENTATION" in m.get("content", "")
            for m in reply_call
            if m.get("role") == "system"
        )
        self.assertFalse(cash_block_seen)

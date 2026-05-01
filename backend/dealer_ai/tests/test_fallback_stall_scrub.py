"""Item 11 — fallback-routing / clarifier-stall scrub.

When `matched_vehicles` is non-empty, the reply must show
vehicles. The LLM has been observed:
  - Asking clarifying questions instead of presenting cards
    ("Could you share a bit more about what matters most?")
  - Inserting stalling prose ("Let me pull our inventory before
    I show you specific units")

Both shapes leave the customer without inventory they could
already see. This scrub catches both.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    LIST_SHAPE_FALLBACK,
    scrub_fallback_stall,
)

from ._mocks import MockLLMProvider, json_reply


# ---- scrub_fallback_stall unit tests ------------------------------------


class ScrubFallbackStallUnitTests(SimpleTestCase):
    def test_no_cards_returns_unchanged(self):
        # Without inventory, clarifying questions are legitimate.
        text = "Could you share your monthly target?"
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=False
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_no_cards_keeps_stall_phrase(self):
        # Discovery / clarifier turns may legitimately say
        # "let me see what we have" — gate is has_cards.
        text = "Let me pull our inventory once you share a target."
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=False
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_empty_text_unchanged(self):
        cleaned, changed = scrub_fallback_stall("", has_cards=True)
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)

    def test_clean_prose_with_cards_unchanged(self):
        text = (
            "The Ranger is really close at about $517/mo. Want a "
            "closer look?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_clarifier_only_replaced_with_fallback(self):
        # User-spec test #2 — every sentence is a question with
        # cards present.
        text = (
            "Could you share what matters most to you? Are you "
            "looking for size, towing, or fuel economy?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertEqual(cleaned, LIST_SHAPE_FALLBACK)

    def test_let_me_pull_inventory_stripped(self):
        text = (
            "Let me pull our real inventory before I show you. The "
            "Ranger is at $517/mo. Want a closer look?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertNotIn("pull our real inventory", cleaned.lower())
        self.assertIn("$517/mo", cleaned)
        self.assertIn("Want a closer look?", cleaned)

    def test_ill_check_whats_available_stripped(self):
        text = (
            "I'll check what's available for you. The Camry lands "
            "at $13,495. Sound good?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertNotIn("what's available", cleaned.lower())
        self.assertIn("$13,495", cleaned)

    def test_come_back_with_options_stripped(self):
        text = (
            "I'll come back with concrete options shortly. The "
            "Ranger is at $517/mo. Want a look?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertNotIn("come back with", cleaned.lower())

    def test_let_me_see_what_we_have_stripped(self):
        text = (
            "Let me see what we have on the lot. The Fusion is at "
            "$11,995. Sound good?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertNotIn("what we have", cleaned.lower())
        self.assertIn("$11,995", cleaned)

    def test_give_me_a_moment_to_check_stripped(self):
        text = (
            "Give me a moment to check the lot. The Sonata is at "
            "$10,995. Want to take a look?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertNotIn("moment to check", cleaned.lower())
        self.assertIn("$10,995", cleaned)

    def test_let_me_get_back_to_you_stripped(self):
        text = (
            "Let me get back to you with specifics. The Civic at "
            "$11,995. Want a look?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertNotIn("get back to you", cleaned.lower())

    def test_only_stall_sentences_falls_back(self):
        # Reply is purely stalling — fallback fires.
        text = (
            "Let me pull our inventory. I'll come back with "
            "options shortly."
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertEqual(cleaned, LIST_SHAPE_FALLBACK)

    def test_stall_plus_clarifier_only_falls_back(self):
        # Stall sentence + clarifying question — both stripped /
        # detected → fallback.
        text = (
            "Let me check what's available. Could you share a "
            "bit more about what matters?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertTrue(changed)
        # Either the clarifier-only path OR the post-strip
        # clarifier-only check fires; either way we get the
        # fallback.
        self.assertEqual(cleaned, LIST_SHAPE_FALLBACK)

    def test_no_stall_no_clarifier_only_unchanged(self):
        text = (
            "The Accord is great at $12,995. The Camry is bigger "
            "at $13,495. Want a closer look?"
        )
        cleaned, changed = scrub_fallback_stall(
            text, has_cards=True
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)


# ---- ChatEngine integration tests --------------------------------------


def _seed_cars():
    Vehicle.objects.create(
        stock_number="CAR-A",
        year=2014,
        make="Honda",
        model="Accord",
        body_style="car",
        condition="used",
        price=Decimal("12995"),
        drivetrain="FWD",
    )
    Vehicle.objects.create(
        stock_number="CAR-B",
        year=2015,
        make="Toyota",
        model="Camry",
        body_style="car",
        condition="used",
        price=Decimal("13495"),
        drivetrain="FWD",
    )


class FallbackStallIntegrationTests(TestCase):
    def test_clarifier_only_reply_replaced(self):
        # User-spec test #2 — no clarifier-only response when
        # inventory exists.
        _seed_cars()
        session = ChatSession.objects.create()
        bad_clarifier = (
            "Could you share what matters most? Are you looking "
            "for size, fuel economy, or something else?"
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                bad_clarifier,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap car cash, gas mileage"
        )
        # Inventory was matched.
        self.assertGreater(len(list(result.matched_vehicles)), 0)
        # Reply is the canned redirect, not the clarifier.
        self.assertEqual(
            result.assistant_message.content, LIST_SHAPE_FALLBACK
        )
        meta = result.assistant_message.metadata
        self.assertIn("fallback_stall", meta.get("scrubs", []))

    def test_stall_phrase_stripped_with_cards(self):
        _seed_cars()
        session = ChatSession.objects.create()
        bad = (
            "Let me pull our real inventory before I show you. "
            "The Honda Accord is a great option at $12,995. Want "
            "a closer look?"
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                bad,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap car cash, fuel economy"
        )
        content = result.assistant_message.content
        self.assertNotIn("pull our real inventory", content.lower())
        self.assertIn("$12,995", content)
        meta = result.assistant_message.metadata
        self.assertIn("fallback_stall", meta.get("scrubs", []))

    def test_clean_reply_unchanged(self):
        _seed_cars()
        session = ChatSession.objects.create()
        clean = (
            "The Honda Accord is a solid choice at $12,995. Want "
            "to take a closer look?"
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                clean,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap car cash"
        )
        self.assertEqual(result.assistant_message.content, clean)
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "fallback_stall", meta.get("scrubs", [])
        )

    def test_no_card_session_keeps_clarifier(self):
        # User-spec safety: when matched_vehicles is empty, the
        # scrub gate blocks. Clarifying questions are the correct
        # response in that case.
        session = ChatSession.objects.create()
        clarifier = (
            "Could you share your monthly target? Are you looking "
            "at trucks or cars?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), clarifier]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("just browsing")
        self.assertEqual(len(list(result.matched_vehicles)), 0)
        self.assertEqual(
            result.assistant_message.content, clarifier
        )
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "fallback_stall", meta.get("scrubs", [])
        )

    def test_fabricated_inventory_guard_still_works(self):
        # Sanity: the existing FABRICATED_INVENTORY_RESPONSE
        # (which CONTAINS stalling-style phrasing about pulling
        # real inventory) is a wholesale replacement that fires
        # BEFORE this scrub. The fallback-stall scrub gate
        # explicitly skips when fabricated_inventory_fired so the
        # canned safe response is preserved.
        _seed_cars()
        session = ChatSession.objects.create()
        bad = (
            "Try Stock #FAKE-999 instead — the Mustang at "
            "$705/mo."
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                bad,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("cheap car cash")
        meta = result.assistant_message.metadata
        # Wholesale guard claimed the slot.
        self.assertEqual(
            meta.get("flag"), "fabricated_inventory"
        )
        # Fallback-stall did NOT fire.
        self.assertNotIn(
            "fallback_stall", meta.get("scrubs", [])
        )

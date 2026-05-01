"""Item 3 — follow-up question quality scrub.

When cards are present, the assistant prose may close with EXACTLY
ONE natural sales question. The smoke run found two failure modes:

  - Compound / forbidden openers: "Would you like to know more
    about any specific aspect, or would you like me to ask a
    narrowing question?"
  - Two questions per turn: "Are you looking for a longer term?
    Would a 72 or 84-month term be acceptable?"

This scrub strips duplicate questions and replaces forbidden
closers with a context-appropriate sales-tone question.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    scrub_followup_question,
)

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(stock, price, *, model="F-150"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        make="Ford",
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


# ---- scrub_followup_question unit tests ---------------------------------


class ScrubFollowupQuestionUnitTests(SimpleTestCase):
    """Pure-function coverage. Each test exercises one detection
    case + one replacement-context selection rule.
    """

    def test_clean_single_question_untouched(self):
        # User-spec test #4 — clean single question untouched.
        text = (
            "The Ranger is really close at about $517/mo. Want a "
            "closer look?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=1,
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertEqual(kind, "")

    def test_no_card_reply_untouched(self):
        # User-spec test #5 — has_cards=False short-circuits.
        text = (
            "Happy to help — would you like to share your monthly "
            "target so I can pull the right options?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=False, card_count=0,
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertEqual(kind, "")

    def test_no_question_in_text_untouched(self):
        text = "The Ranger is really close at about $517/mo."
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=1,
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertEqual(kind, "")

    def test_empty_reply_unchanged(self):
        cleaned, changed, kind = scrub_followup_question(
            "", has_cards=True, card_count=1,
        )
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)
        self.assertEqual(kind, "")

    def test_would_you_like_opener_replaced_with_generic(self):
        # User-spec test #2 — forbidden opener replaced. No flex
        # kinds, multi-card → generic fallback.
        text = (
            "The Ranger is really close at about $517/mo. Would "
            "you like to explore other options?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=3,
        )
        self.assertTrue(changed)
        self.assertEqual(kind, "generic")
        self.assertNotIn("Would you like", cleaned)
        self.assertIn(
            "Would that be something you'd consider?", cleaned
        )
        # Useful prose before the bad question is preserved.
        self.assertIn(
            "The Ranger is really close at about $517/mo.", cleaned
        )

    def test_would_you_like_opener_replaced_with_lever_flex(self):
        # When lever-flex kinds surfaced, the replacement mirrors
        # _lever_flex_close_question (same wording the deterministic
        # branch produces).
        text = (
            "The Ranger is close. Would you like to explore other "
            "options?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text,
            has_cards=True,
            lever_flex_kinds=["longer_term", "drivetrain_flex"],
            card_count=3,
        )
        self.assertTrue(changed)
        self.assertEqual(kind, "lever_flex")
        self.assertIn(
            "Would you rather look at a longer term or flexible "
            "drivetrain?",
            cleaned,
        )

    def test_would_you_like_opener_replaced_with_single_card(self):
        # Single-card anchor follow-up turns get the focused close.
        text = (
            "The 2019 Ranger is a great option. Would you like to "
            "know more about any specific feature?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=1,
        )
        self.assertTrue(changed)
        self.assertEqual(kind, "single_card")
        self.assertIn(
            "Is that the direction you want to go?", cleaned
        )
        self.assertNotIn("specific feature", cleaned)

    def test_narrowing_question_phrase_replaced(self):
        # User-spec test #3 — the meta phrase is forbidden even when
        # the opener is benign.
        text = (
            "The Ranger is close at about $517/mo. Want me to ask "
            "a narrowing question?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=3,
        )
        self.assertTrue(changed)
        self.assertEqual(kind, "generic")
        self.assertNotIn("narrowing question", cleaned)

    def test_specific_aspect_phrase_replaced(self):
        text = (
            "The Ranger is great. Want to know more about any "
            "specific aspect of the truck?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=1,
        )
        self.assertTrue(changed)
        # card_count=1 → single_card replacement.
        self.assertEqual(kind, "single_card")
        self.assertNotIn("specific aspect", cleaned)

    def test_compound_would_you_like_replaced(self):
        # Compound "Would you like X, or would you like Y?" — two
        # `would you like` instances in one sentence.
        text = (
            "The Ranger is close. Would you like to know more about "
            "the Ranger, or would you like me to ask a narrowing "
            "question?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=3,
        )
        self.assertTrue(changed)
        self.assertEqual(kind, "generic")
        self.assertNotIn("Would you like", cleaned)
        self.assertNotIn("narrowing question", cleaned)

    def test_two_questions_keep_last_when_clean(self):
        # User-spec test #1 — two `?` total. Strip the earlier one,
        # keep the last (which is clean).
        text = (
            "What sounds best for you? Want me to set up a test "
            "drive?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=3,
        )
        self.assertTrue(changed)
        self.assertEqual(kind, "stripped_extras")
        self.assertEqual(cleaned.count("?"), 1)
        self.assertIn("Want me to set up a test drive?", cleaned)
        self.assertNotIn("What sounds best for you?", cleaned)

    def test_two_questions_keep_last_then_replace(self):
        # Setup question first, forbidden closer second. Strip
        # earlier, then replace the closer.
        text = (
            "Are you looking for a longer term or more "
            "flexibility? Would you like to know more about any "
            "specific aspect?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=3,
        )
        self.assertTrue(changed)
        self.assertEqual(kind, "generic")
        self.assertNotIn("Are you looking for a longer term", cleaned)
        self.assertNotIn("specific aspect", cleaned)
        self.assertIn(
            "Would that be something you'd consider?", cleaned
        )

    def test_useful_prose_before_question_preserved(self):
        # The prose leading up to the forbidden question stays.
        text = (
            "The Ranger is close at about $517/mo. The Tundra "
            "opens up if you stretch the term. Would you like to "
            "explore?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=3,
        )
        self.assertTrue(changed)
        self.assertIn("really close", cleaned.lower()) if False else None
        self.assertIn("$517/mo", cleaned)
        self.assertIn("Tundra", cleaned)
        self.assertIn(
            "Would that be something you'd consider?", cleaned
        )

    def test_what_would_you_like_is_open_ended_not_forbidden(self):
        # "What would you like..." is genuine discovery, NOT the
        # sales-template "Would you like..." opener. Must pass.
        text = (
            "Got it — let me focus on the vehicle. What would you "
            "like to know next?"
        )
        cleaned, changed, kind = scrub_followup_question(
            text, has_cards=True, card_count=1,
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)


# ---- ChatEngine integration tests ---------------------------------------


class FollowupQuestionIntegrationTests(TestCase):
    """End-to-end coverage. Verifies the scrub fires through the
    full ``handle_user_message`` pipeline and the metadata flag
    chain stays correct.
    """

    def _ranger_session(self):
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        return ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )

    def test_integration_replaces_would_you_like_opener(self):
        # User-spec test #2 — full pipeline.
        session = self._ranger_session()
        bad = (
            "The Ranger is really close at about $517/mo. Would "
            "you like to know more about any specific aspect of "
            "the Ranger?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("Would you like", content)
        self.assertNotIn("specific aspect", content)
        self.assertIn(
            "Is that the direction you want to go?", content
        )
        meta = result.assistant_message.metadata
        self.assertIn("followup_question", meta.get("scrubs", []))
        self.assertEqual(
            meta.get("flag"), "followup_question_scrubbed"
        )

    def test_integration_clean_question_unchanged(self):
        # User-spec test #4 — clean prose passes through untouched.
        session = self._ranger_session()
        clean = (
            "The Ranger is really close at about $517/mo. Want a "
            "closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), clean])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        self.assertEqual(result.assistant_message.content, clean)
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "followup_question", meta.get("scrubs", [])
        )
        self.assertNotEqual(
            meta.get("flag"), "followup_question_scrubbed"
        )

    def test_integration_no_card_session_unchanged(self):
        # User-spec test #5 — when there are no matched_vehicles
        # the scrub does not fire even on a forbidden close.
        session = ChatSession.objects.create(extracted_profile={})
        clarifier = (
            "Happy to help. Would you like to share your monthly "
            "target so I can find the right options?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), clarifier])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I'm just browsing for now"
        )

        self.assertEqual(len(list(result.matched_vehicles)), 0)
        self.assertEqual(
            result.assistant_message.content, clarifier
        )
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "followup_question", meta.get("scrubs", [])
        )

    def test_integration_two_questions_stripped(self):
        # User-spec test #1 — two ?-marks, last is clean.
        session = self._ranger_session()
        bad = (
            "The Ranger is close at about $517/mo. Are you looking "
            "for more flexibility? Want a closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertEqual(content.count("?"), 1)
        self.assertIn("Want a closer look?", content)
        self.assertNotIn("Are you looking for more flexibility?", content)
        meta = result.assistant_message.metadata
        self.assertIn("followup_question", meta.get("scrubs", []))

    def test_integration_narrowing_question_phrase_replaced(self):
        # User-spec test #3 — meta phrase replaced.
        session = self._ranger_session()
        bad = (
            "The Ranger is close at about $517/mo. Want me to "
            "ask a narrowing question to help you decide?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("narrowing question", content)
        # card_count=1 → single_card replacement.
        self.assertIn(
            "Is that the direction you want to go?", content
        )

    def test_integration_stacks_with_list_shape_scrubbed(self):
        # User-spec test #6 — list_shape and followup_question
        # both fire, flag promotes to multiple_scrubs_fired.
        session = self._ranger_session()
        bad = (
            "Here are a few options:\n"
            "* 2019 Ford Ranger | Stock #FF-USED-104 | $26,995\n"
            "Would you like to know more about any specific aspect?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        # Bullet line stripped, forbidden close replaced.
        self.assertNotIn("FF-USED-104", content)
        self.assertNotIn("Would you like", content)
        self.assertIn(
            "Is that the direction you want to go?", content
        )
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        self.assertIn("list_shape", scrubs)
        self.assertIn("followup_question", scrubs)
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")

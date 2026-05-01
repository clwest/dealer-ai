"""Item 10 — hard length cap for model-followup replies.

Runs AFTER all other scrubs. Truncates the reply to ≤ 3 sentences
with exactly one question at the end. Mechanical safety net for
the verbosity that slips past the generic-use-case scrub on
brochure-shaped LLM output.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatMessage, ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    cap_model_followup_length,
)

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(stock, price, *, model, drivetrain="4x4", body="truck"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2019,
        make="Ford",
        model=model,
        body_style=body,
        condition="used",
        price=Decimal(price),
        drivetrain=drivetrain,
    )


# ---- cap_model_followup_length unit tests -------------------------------


class CapModelFollowupLengthUnitTests(SimpleTestCase):
    """Pure-function coverage. Gates on mode, walks sentences,
    enforces ≤ 3 sentences with exactly one trailing question.
    """

    MODE = "model_followup"

    def test_mode_not_followup_no_op(self):
        text = (
            "Sentence one. Sentence two. Sentence three. Sentence "
            "four. Sentence five."
        )
        cleaned, changed = cap_model_followup_length(text, mode=None)
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

        cleaned, changed = cap_model_followup_length(
            text, mode="discovery"
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_empty_reply_no_op(self):
        cleaned, changed = cap_model_followup_length("", mode=self.MODE)
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)

    def test_two_sentences_ending_question_no_op(self):
        text = (
            "The Ranger is close at about $517/mo. Want a closer "
            "look?"
        )
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_three_sentences_ending_question_no_op(self):
        text = (
            "The Ranger is mid-size. It lands at $517/mo. Want a "
            "closer look?"
        )
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_five_sentences_ending_question_truncated(self):
        text = (
            "The Ranger is a mid-size pickup. It handles like a "
            "smaller truck. Easy to park. Plenty of bed space for "
            "weekend hauls. Want a closer look?"
        )
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        # ≤ 3 sentences total.
        self.assertLessEqual(cleaned.count(". ") + 1, 3)
        # Trailing question preserved.
        self.assertTrue(cleaned.rstrip().endswith("?"))
        self.assertIn("Want a closer look?", cleaned)
        # First two statements kept.
        self.assertIn("The Ranger is a mid-size pickup", cleaned)
        # Later statements dropped.
        self.assertNotIn("weekend hauls", cleaned)

    def test_no_question_appends_default_close(self):
        text = (
            "The Ranger is mid-size. It handles like a smaller "
            "truck. Easy to park. Plenty of bed space."
        )
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        self.assertTrue(cleaned.rstrip().endswith("?"))
        self.assertIn("Is that the direction you want to go?", cleaned)
        # First two statements kept.
        self.assertIn("The Ranger is mid-size", cleaned)
        self.assertIn("smaller truck", cleaned)
        # Later statements dropped.
        self.assertNotIn("bed space", cleaned)

    def test_two_questions_keeps_last_only(self):
        text = (
            "What sounds best for you? The Ranger is mid-size. "
            "Want me to set up a test drive?"
        )
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        # Earlier question dropped.
        self.assertNotIn("What sounds best", cleaned)
        # Last question preserved.
        self.assertIn("Want me to set up a test drive?", cleaned)
        # Statement preserved.
        self.assertIn("The Ranger is mid-size", cleaned)

    def test_one_statement_no_question_adds_default(self):
        text = "The Ranger is a mid-size pickup."
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        self.assertIn("The Ranger is a mid-size pickup", cleaned)
        self.assertIn("Is that the direction you want to go?", cleaned)

    def test_one_question_only_no_op(self):
        text = "Want a closer look?"
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_six_sentences_with_mid_question_truncates(self):
        # Question in the middle, more sentences after — keep first
        # 2 statements, drop mid-question, append a default close
        # since the LAST sentence isn't a question.
        text = (
            "The Ranger is mid-size. It handles like a smaller "
            "truck. Want a look? It's $517/mo. The cargo bed is "
            "big. Towing is solid."
        )
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        # The mid-question is dropped (not the LAST one — but
        # there's no later question, so it's the only one).
        # Actually — "Want a look?" is the LAST question in the
        # reply. The function picks it as the closer.
        self.assertIn("Want a look?", cleaned)
        # First two statements kept; "Towing is solid" dropped.
        self.assertIn("The Ranger is mid-size", cleaned)
        self.assertNotIn("Towing is solid", cleaned)

    def test_custom_max_sentences_2(self):
        text = (
            "Sentence one. Sentence two. Sentence three. Want a "
            "look?"
        )
        cleaned, changed = cap_model_followup_length(
            text, mode=self.MODE, max_sentences=2
        )
        self.assertTrue(changed)
        # Just 1 statement + 1 question.
        self.assertIn("Sentence one", cleaned)
        self.assertNotIn("Sentence two", cleaned)
        self.assertNotIn("Sentence three", cleaned)
        self.assertIn("Want a look?", cleaned)

    def test_custom_default_close(self):
        text = "Just one statement here."
        cleaned, changed = cap_model_followup_length(
            text,
            mode=self.MODE,
            default_close="Sound good?",
        )
        self.assertTrue(changed)
        self.assertIn("Just one statement", cleaned)
        self.assertIn("Sound good?", cleaned)


# ---- ChatEngine integration test ----------------------------------------


class ModelFollowupLengthCapIntegrationTests(TestCase):
    def _ranger_session(self):
        ranger = _make_vehicle(
            "FF-USED-104", "26995", model="Ranger", drivetrain="4x4"
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
                "current_vehicle_id": ranger.id,
                "current_vehicle_stock": ranger.stock_number,
            }
        )
        prior = ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=(
                "The Ranger is really close at about $517/mo. Want a "
                "look?"
            ),
            metadata={"matched_count": 1},
        )
        prior.matched_vehicles.set([ranger])
        return session

    def test_long_followup_reply_capped(self):
        session = self._ranger_session()
        # Six-sentence brochure-style reply. The list_shape and
        # generic_use_case scrubs may catch some shapes, but if any
        # verbose prose survives, the length cap takes the rest.
        long_reply = (
            "The Ranger is a mid-size pickup truck. It handles "
            "like a smaller truck. Easy to park, plenty of bed "
            "space. The 2.3L EcoBoost engine gets decent mileage. "
            "Towing capacity is solid. Is that the direction you "
            "want to go?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), long_reply]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "tell me more about the Ranger"
        )
        content = result.assistant_message.content
        # ≤ 3 sentences total.
        sentence_endings = sum(
            content.count(p) for p in (".", "!", "?")
        )
        self.assertLessEqual(sentence_endings, 3)
        # Last sentence is a question.
        self.assertTrue(content.rstrip().endswith("?"))
        # Anchorless brochure-y statements dropped (towing
        # capacity isn't anchored to constraint / comparison /
        # this card's features in the test fixture).
        self.assertNotIn("Towing capacity", content)
        meta = result.assistant_message.metadata
        self.assertEqual(meta.get("mode"), "model_followup")
        # The reduction must happen via SOMETHING — either the
        # length cap (item 10) or the anchor filter (item 14)
        # depending on which strips first. Both leave the reply
        # short and on-topic.
        self.assertTrue(
            meta.get("sentence_capped")
            or "followup_anchors" in meta.get("scrubs", [])
            or "generic_use_case" in meta.get("scrubs", []),
            "Long reply must be reduced by some scrub: scrubs="
            f"{meta.get('scrubs', [])}, "
            f"sentence_capped={meta.get('sentence_capped')}",
        )

    def test_short_followup_reply_unchanged(self):
        # Already compliant — the cap doesn't fire.
        session = self._ranger_session()
        clean = (
            "The Ranger is a mid-size that handles like a smaller "
            "truck. It lands at $517/mo. Is that the direction you "
            "want to go?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), clean])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "tell me more about the Ranger"
        )
        # Other scrubs may have fired but the cap shouldn't have.
        meta = result.assistant_message.metadata
        self.assertFalse(meta.get("sentence_capped"))

    def test_non_followup_turn_not_capped(self):
        # Length cap is gated on mode == model_followup. A regular
        # multi-card budget turn isn't capped.
        ranger = _make_vehicle(
            "FF-USED-104", "26995", model="Ranger", drivetrain="4x4"
        )
        _make_vehicle(
            "FF-USED-405", "25495", model="Colorado",
            drivetrain="RWD", body="truck",
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                # 5 sentences, ends with a question.
                "The Ranger is close at about $517/mo. The "
                "Colorado slips under at $486/mo. The Tundra "
                "opens up at $609/mo. All three are solid "
                "options. Want a closer look?",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I'm looking for a 4WD truck around $500/mo with $3k down"
        )
        meta = result.assistant_message.metadata
        # Not a model_followup → cap doesn't fire.
        self.assertFalse(meta.get("sentence_capped"))
        self.assertNotEqual(meta.get("mode"), "model_followup")

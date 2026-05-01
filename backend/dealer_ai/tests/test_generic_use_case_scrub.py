"""Item 6 — generic-use-case scrub for model-followup turns.

When the customer asks about a specific vehicle (*"tell me more
about the Ranger"*), the small Ollama model defaults to brochure
copy: *"perfect for hunting and camping"*, *"ideal for off-road
adventures"*. These sentences carry no constraint-fit / comparison
anchor and waste the customer's attention. The scrub strips them.

Narrow scope: only fires on `mode == "model_followup"` turns. Other
branches (lever-flex multi-card replies, single-near soft-close,
etc.) are unaffected.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatMessage, ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    scrub_generic_use_cases,
)

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(
    stock,
    price,
    *,
    model="F-150",
    trim="",
    drivetrain="4x4",
    body="truck",
    condition="used",
    year=2025,
):
    return Vehicle.objects.create(
        stock_number=stock,
        year=year,
        make="Ford",
        model=model,
        trim=trim,
        body_style=body,
        condition=condition,
        price=Decimal(price),
        drivetrain=drivetrain,
    )


# ---- scrub_generic_use_cases unit tests ---------------------------------


class ScrubGenericUseCasesUnitTests(SimpleTestCase):
    """Pure-function coverage. The scrub is sentence-level and
    distinguishes brochure clichés (`"perfect for hunting"`) from
    constraint-fit prose (`"fits your $500 target with the 4WD you
    wanted"`) by checking for fit / comparison signals.
    """

    MODE = "model_followup"

    def test_clean_prose_untouched(self):
        text = (
            "The 2019 Ranger is a mid-size pickup that handles like "
            "a smaller truck. It lands at $517/mo, just above your "
            "$500 target. Want a closer look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_empty_text_unchanged(self):
        cleaned, changed = scrub_generic_use_cases("", mode=self.MODE)
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)

    def test_perfect_for_hunting_and_camping_stripped(self):
        text = (
            "The 2019 Ranger is a mid-size truck that's perfect for "
            "hunting and camping. It lands at $517/mo. Want a "
            "closer look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        self.assertNotIn("perfect for hunting", cleaned)
        self.assertNotIn("camping", cleaned)
        self.assertIn("$517/mo", cleaned)
        self.assertIn("Want a closer look?", cleaned)

    def test_ideal_for_off_road_adventures_stripped(self):
        text = (
            "The Ranger is ideal for off-road adventures. The 4WD "
            "drivetrain handles tough terrain. Want a look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        self.assertNotIn("ideal for off-road", cleaned)
        self.assertIn("Want a look?", cleaned)

    def test_great_for_outdoor_enthusiasts_stripped(self):
        text = (
            "The Bronco Sport is great for outdoor enthusiasts who "
            "love adventure. It lands at about $545/mo. Should we "
            "talk numbers?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        self.assertNotIn("outdoor enthusiasts", cleaned)
        self.assertIn("$545/mo", cleaned)
        self.assertIn("Should we talk numbers?", cleaned)

    def test_great_option_for_those_who_brochure_stripped(self):
        # Pure brochure phrasing — "those who want adventure" with
        # no comparison or constraint-fit anchor.
        text = (
            "The Maverick is a great option for those who love "
            "weekend adventures. It runs at $385/mo. Sound good?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        self.assertNotIn("great option for those", cleaned)
        self.assertIn("$385/mo", cleaned)
        self.assertIn("Sound good?", cleaned)

    def test_great_option_for_those_with_comparison_preserved(self):
        # Documents the borderline case: "those who want a smaller
        # hybrid truck" — the comparison adjective ("smaller")
        # makes this real positioning, not brochure fluff. Preserve.
        text = (
            "The Maverick is a great option for those who want a "
            "smaller hybrid truck. It runs at $385/mo. Sound good?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_constraint_fit_with_use_case_word_preserved(self):
        # User-spec test #3 — "fits your $500 target with the 4WD
        # you wanted" preserved. Constraint-fit signals
        # ("your target", "you wanted") win over the cliché phrase.
        text = (
            "The Ranger is perfect for your $500 target with the "
            "4WD you wanted. Want a closer look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_constraint_fit_with_target_signal_preserved(self):
        text = (
            "The Ranger lands right at your $500 target. Want a "
            "closer look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_comparison_to_smaller_preserved(self):
        # User-spec test #4 — comparison to larger / smaller truck
        # preserved.
        text = (
            "The Maverick is smaller than the F-150 you saw, with "
            "similar towing for most loads. It's $385/mo. Want a "
            "closer look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_comparison_step_up_from_preserved(self):
        text = (
            "The Lariat is a step up from the XLT you saw — same "
            "size class, more interior trim. $604/mo. Should I "
            "line one up?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_real_world_positioning_preserved(self):
        # "Mid-size that handles like a smaller truck" is the
        # canonical good positioning sentence. No cliché phrase —
        # passes regardless of mode.
        text = (
            "The Ranger is a mid-size that handles like a smaller "
            "truck — easy to park, plenty of bed for camping gear "
            "or weekend hauls. Want a closer look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_mode_not_followup_no_scrub(self):
        # Narrow-scope safety: when the turn is NOT a
        # model-followup, the scrub never fires even on cliché
        # phrasing. This protects the lever-flex / multi-near
        # branches (which can legitimately mention "weekend" or
        # "family" descriptively).
        text = (
            "The Ranger is perfect for hunting and camping. The "
            "Tundra is bigger if you need more cargo. Want a look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=None
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

        cleaned, changed = scrub_generic_use_cases(
            text, mode="discovery"
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_multiple_cliche_sentences_all_stripped(self):
        text = (
            "The Ranger is great for outdoor adventures. It's "
            "perfect for hunting and camping. The truck lands at "
            "$517/mo. Want a closer look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertTrue(changed)
        self.assertNotIn("outdoor adventures", cleaned)
        self.assertNotIn("hunting and camping", cleaned)
        self.assertIn("$517/mo", cleaned)
        self.assertIn("Want a closer look?", cleaned)

    def test_ideal_for_with_constraint_signal_preserved(self):
        text = (
            "The Bronco Sport is ideal for your $500 target with "
            "the AWD you asked for. Want a look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_cliche_phrase_without_activity_noun_preserved(self):
        # "perfect for the mountains" — no activity noun in the
        # forbidden list. The scrub allows it (we'd rather miss
        # one cliché than false-positive on real positioning).
        text = (
            "The Bronco is perfect for the mountains around here. "
            "Want a look?"
        )
        cleaned, changed = scrub_generic_use_cases(
            text, mode=self.MODE
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)


# ---- ChatEngine integration tests ---------------------------------------


class ModelFollowupDeepDiveIntegrationTests(TestCase):
    """End-to-end coverage. Verifies the scrub fires on
    model-followup turns and stays off everywhere else.
    """

    def _ranger_session(self):
        ranger = _make_vehicle(
            "FF-USED-104",
            "26995",
            model="Ranger",
            trim="XLT SuperCrew 4x4",
            drivetrain="4x4",
            year=2019,
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
        # Seed a prior assistant turn so the model-followup detector
        # has an anchor + the previous-shown set has names to
        # reference. The bare matched-vehicles M2M is what
        # `_previous_assistant_matched_vehicles` reads.
        prior = ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=(
                "The Ranger is really close at about $517/mo. Want a "
                "closer look?"
            ),
            metadata={"matched_count": 1},
        )
        prior.matched_vehicles.set([ranger])
        return session, ranger

    def test_integration_brochure_reply_stripped(self):
        # User-spec test #1 — "perfect for hunting and camping"
        # stripped end-to-end.
        session, _ranger = self._ranger_session()
        bad = (
            "The 2019 Ford Ranger XLT SuperCrew 4x4 is a mid-size "
            "pickup that's perfect for hunting and camping. It "
            "lands at $517/mo. Is that the direction you want to "
            "go?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "tell me more about the Ranger"
        )
        content = result.assistant_message.content
        self.assertNotIn("perfect for hunting", content)
        self.assertNotIn("camping", content)
        self.assertIn("$517/mo", content)
        meta = result.assistant_message.metadata
        self.assertEqual(meta.get("mode"), "model_followup")
        self.assertIn("generic_use_case", meta.get("scrubs", []))

    def test_integration_clean_deep_dive_unchanged(self):
        # User-spec test #5 — a clean deep-dive reply is left alone.
        session, _ = self._ranger_session()
        clean = (
            "The Ranger is a mid-size that handles like a smaller "
            "truck. It lands at $517/mo, just above your $500 "
            "target. Is that the direction you want to go?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), clean])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "tell me more about the Ranger"
        )
        self.assertEqual(result.assistant_message.content, clean)
        meta = result.assistant_message.metadata
        self.assertEqual(meta.get("mode"), "model_followup")
        self.assertNotIn(
            "generic_use_case", meta.get("scrubs", [])
        )

    def test_integration_constraint_fit_preserved(self):
        # User-spec test #3 — "fits your $500 target with the 4WD
        # you wanted" preserved end-to-end.
        session, _ = self._ranger_session()
        good = (
            "The Ranger fits your $500 target with the 4WD you "
            "wanted. It lands at $517/mo. Is that the direction "
            "you want to go?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), good])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "tell me more about the Ranger"
        )
        self.assertEqual(result.assistant_message.content, good)
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "generic_use_case", meta.get("scrubs", [])
        )

    def test_integration_non_followup_turn_no_scrub(self):
        # Narrow-scope safety: a regular budget turn (not a
        # model-followup) should not have the scrub fire even if
        # the LLM emits brochure copy. This protects the rest of
        # the chat surface from unintended over-stripping while we
        # iterate.
        _make_vehicle(
            "FF-USED-104",
            "26995",
            model="Ranger",
            trim="XLT 4x4",
            drivetrain="4x4",
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )
        bad = (
            "The Ranger is really close at about $517/mo. It's "
            "perfect for hunting and camping. Want a closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I'm looking for a truck around $500/mo with $3k down"
        )
        meta = result.assistant_message.metadata
        # NOT a model-followup turn — scrub stays off.
        self.assertNotEqual(meta.get("mode"), "model_followup")
        self.assertNotIn(
            "generic_use_case", meta.get("scrubs", [])
        )

    def test_integration_stacks_with_followup_question(self):
        # Bad reply has both a cliché AND a forbidden close.
        # generic_use_case + followup_question both fire.
        session, _ = self._ranger_session()
        bad = (
            "The Ranger is great for outdoor enthusiasts. It lands "
            "at $517/mo. Would you like to know more about any "
            "specific aspect?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "tell me more about the Ranger"
        )
        content = result.assistant_message.content
        self.assertNotIn("outdoor enthusiasts", content)
        self.assertNotIn("Would you like", content)
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        self.assertIn("generic_use_case", scrubs)
        self.assertIn("followup_question", scrubs)
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")

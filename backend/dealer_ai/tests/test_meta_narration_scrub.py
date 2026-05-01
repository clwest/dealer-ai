"""Item 5 — meta-narration scrub.

Strips lines / parentheticals where the LLM talks about its own
response or process: "Here's a revised response that...",
"(Note: I've removed the payment quote...)", "Let's try again",
"As requested:", "Based on your request:", "This response...".

The smoke run produced these wrappers in scenario 5 — the
internal_confusion_fallback caught some wholesale, but a partial
scrub preserves the genuine reply underneath.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    META_NARRATION_FALLBACK,
    scrub_meta_narration,
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


# ---- scrub_meta_narration unit tests -------------------------------------


class ScrubMetaNarrationUnitTests(SimpleTestCase):
    """Pure-function coverage for each detection class.

    The scrub does NOT take a `has_cards` gate — meta narration is
    bad in clarifier turns too. False positives on legitimate prose
    are the bigger risk, so the patterns are anchored to whole
    lines (or parenthesized segments) and require strong meta
    signals (trailing colon, first-person past-action verb).
    """

    def test_clean_prose_untouched(self):
        # User-spec test #4 — clean replies untouched.
        text = (
            "The Ranger is really close at about $517/mo. The Tundra "
            "opens up if you stretch the term a bit. Want a closer "
            "look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_empty_reply_unchanged(self):
        cleaned, changed, fallback = scrub_meta_narration("")
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_meta_prefix_removed_content_preserved(self):
        # User-spec test #1 — meta prefix removed, content preserved.
        text = (
            "Here's a revised response that takes into account the "
            "customer's open-mindedness on drivetrain:\n"
            "The Ranger is really close at about $517/mo. Want a "
            "closer look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("Here's a revised response", cleaned)
        self.assertIn("The Ranger is really close", cleaned)
        self.assertIn("Want a closer look?", cleaned)

    def test_heres_a_reply_that_matches_the_format_removed(self):
        text = (
            "Here's a reply that matches the format:\n"
            "The Ranger is close at about $517/mo. Want a look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("matches the format", cleaned)
        self.assertIn("$517/mo", cleaned)

    def test_heres_a_response_that_follows_the_guidelines_removed(self):
        text = (
            "Here's a response that follows the guidelines:\n"
            "The Ranger is great. Want a look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("follows the guidelines", cleaned)

    def test_lets_try_again_removed(self):
        text = (
            "Let's try again.\n"
            "The Ranger is close at about $517/mo. Want a look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("Let's try again", cleaned)
        self.assertIn("$517/mo", cleaned)

    def test_meta_suffix_parenthetical_removed(self):
        # User-spec test #2 — meta suffix removed.
        text = (
            "The Ranger is really close at about $517/mo. Want a "
            "closer look? (Note: I've removed the specific payment "
            "quote for the Tundra, as it's not necessary in this "
            "case.)"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("Note: I've removed", cleaned)
        # Genuine reply preserved.
        self.assertIn(
            "The Ranger is really close at about $517/mo.", cleaned
        )
        self.assertIn("Want a closer look?", cleaned)

    def test_standalone_note_line_removed(self):
        text = (
            "The Ranger is close at about $517/mo. Want a look?\n"
            "Note: I've adjusted the payment to reflect 60-month "
            "term."
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("I've adjusted", cleaned)

    def test_generic_note_line_kept(self):
        # "Note: prices may vary" is a legitimate caveat — only
        # first-person past-action verbs trigger the meta scrub.
        text = (
            "The Ranger is close at about $517/mo.\n"
            "Note: prices may vary by trim."
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_as_requested_prefix_removed(self):
        text = (
            "As requested: here are some options.\n"
            "The Ranger is close at about $517/mo. Want a look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("As requested", cleaned)

    def test_based_on_your_request_prefix_removed(self):
        text = (
            "Based on your request, I've prepared the following:\n"
            "The Ranger is close at about $517/mo. Want a look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("Based on your request", cleaned)
        self.assertIn("$517/mo", cleaned)

    def test_this_response_prefix_removed(self):
        text = (
            "This response covers your options:\n"
            "The Ranger is close at about $517/mo. Want a look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("This response", cleaned)

    def test_mixed_content_preserved(self):
        # User-spec test #3 — mixed content preserved.
        text = (
            "Here's a revised response that addresses your "
            "concerns:\n"
            "\n"
            "The Ranger is really close at about $517/mo. If you're "
            "flexible on drivetrain, the Colorado slips under your "
            "target.\n"
            "\n"
            "Would you rather look at a longer term or flexible "
            "drivetrain? (Note: I've focused on qualitative "
            "references rather than restating prices.)"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        # Meta wrapper gone.
        self.assertNotIn("revised response", cleaned)
        self.assertNotIn("Note: I've focused", cleaned)
        # Genuine reply preserved.
        self.assertIn(
            "The Ranger is really close at about $517/mo.", cleaned
        )
        self.assertIn("Colorado slips under your target", cleaned)
        self.assertIn(
            "Would you rather look at a longer term", cleaned
        )

    def test_inline_based_on_your_needs_kept(self):
        # "Based on your needs" mid-sentence (no comma/colon) is
        # legitimate prose, not meta. Anchor to start-of-line +
        # comma/colon ensures we don't false-positive.
        text = (
            "Based on your needs we should look at the Ranger. "
            "Want a closer look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_fallback_when_only_meta_remains(self):
        text = (
            "Here's a revised response:\n"
            "(Note: I've removed everything.)"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertTrue(fallback)
        self.assertEqual(cleaned, META_NARRATION_FALLBACK)

    def test_parenthetical_in_middle_removed(self):
        text = (
            "The Ranger is great (Note: I've trimmed the price "
            "details). Want a look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("I've trimmed", cleaned)
        self.assertIn("The Ranger is great", cleaned)
        self.assertIn("Want a look?", cleaned)

    def test_two_parentheticals_both_removed(self):
        text = (
            "The Ranger is great (Note: I've removed prices) and "
            "the Tundra is bigger (Note: I've trimmed details). "
            "Want a look?"
        )
        cleaned, changed, fallback = scrub_meta_narration(text)
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("I've removed", cleaned)
        self.assertNotIn("I've trimmed", cleaned)
        self.assertIn("The Ranger is great", cleaned)
        self.assertIn("the Tundra is bigger", cleaned)


# ---- ChatEngine integration tests ----------------------------------------


class MetaNarrationIntegrationTests(TestCase):
    """End-to-end coverage. Verifies the scrub fires through the
    full ``handle_user_message`` pipeline and stacks correctly with
    list_shape and followup_question.
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

    def test_integration_meta_prefix_removed(self):
        # Full pipeline: meta opener stripped, genuine reply
        # preserved.
        session = self._ranger_session()
        bad = (
            "Here's a revised response that takes into account your "
            "preferences:\n"
            "The Ranger is really close at about $517/mo. Want a "
            "closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("Here's a revised response", content)
        self.assertIn("$517/mo", content)
        self.assertIn("Want a closer look?", content)
        meta = result.assistant_message.metadata
        self.assertIn("meta_narration", meta.get("scrubs", []))
        self.assertEqual(
            meta.get("flag"), "meta_narration_scrubbed"
        )

    def test_integration_meta_suffix_parenthetical_removed(self):
        session = self._ranger_session()
        bad = (
            "The Ranger is really close at about $517/mo. Want a "
            "closer look? (Note: I've removed the specific payment "
            "quote for the Tundra.)"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("Note: I've removed", content)
        self.assertIn(
            "The Ranger is really close at about $517/mo", content
        )
        meta = result.assistant_message.metadata
        self.assertIn("meta_narration", meta.get("scrubs", []))

    def test_integration_clean_reply_untouched(self):
        # User-spec test #4 — clean prose passes through unchanged.
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
        self.assertNotIn("meta_narration", meta.get("scrubs", []))
        self.assertNotEqual(
            meta.get("flag"), "meta_narration_scrubbed"
        )

    def test_integration_stacks_with_list_shape(self):
        # User-spec test #5 — meta_narration + list_shape both fire.
        session = self._ranger_session()
        bad = (
            "Here's a revised response that follows the format:\n"
            "* 2019 Ford Ranger | Stock #FF-USED-104 | $26,995\n"
            "Want a look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("revised response", content)
        self.assertNotIn("FF-USED-104", content)
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        self.assertIn("meta_narration", scrubs)
        self.assertIn("list_shape", scrubs)
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")

    def test_integration_stacks_with_followup_question(self):
        # User-spec test #5 — meta_narration + followup_question both
        # fire.
        session = self._ranger_session()
        bad = (
            "Here's a revised response:\n"
            "The Ranger is close at about $517/mo. Would you like to "
            "know more about any specific aspect?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("revised response", content)
        self.assertNotIn("Would you like", content)
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        self.assertIn("meta_narration", scrubs)
        self.assertIn("followup_question", scrubs)
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")

    def test_integration_stacks_with_list_and_followup(self):
        # Three-way stack: meta + list + followup.
        session = self._ranger_session()
        bad = (
            "Here's a revised response:\n"
            "* 2019 Ford Ranger | Stock #FF-USED-104 | $26,995\n"
            "Would you like to know more about any specific aspect?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("revised response", content)
        self.assertNotIn("FF-USED-104", content)
        self.assertNotIn("Would you like", content)
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        self.assertIn("meta_narration", scrubs)
        self.assertIn("list_shape", scrubs)
        self.assertIn("followup_question", scrubs)
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")

    def test_integration_existing_scrubs_still_work(self):
        # Sanity check: with meta_narration in the chain, the
        # legacy partial scrubs (rate_language) still fire on
        # whatever survives the meta strip. The meta wrapper here
        # carries a rate-language phrase; stripping the wrapper
        # also removes the rate phrase. Checks no regression in
        # the partial-scrub gates.
        session = self._ranger_session()
        bad = (
            "Here's a revised response:\n"
            "The Ranger is close at about $517/mo at 7.49% APR. "
            "Want a look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        # Meta wrapper gone.
        self.assertNotIn("revised response", content)
        # Rate language scrubbed (replaced with W.A.C.).
        self.assertNotIn("7.49%", content)
        self.assertNotIn("APR", content)
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        # Both meta_narration and rate_language fired.
        self.assertIn("meta_narration", scrubs)
        self.assertIn("rate_language", scrubs)
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")

    def test_integration_fallback_when_only_meta_remains(self):
        # Reply is purely meta wrapper — fallback fires.
        session = self._ranger_session()
        only_meta = (
            "Here's a revised response that addresses your needs:\n"
            "(Note: I've removed all the details.)"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), only_meta]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertEqual(content, META_NARRATION_FALLBACK)
        meta = result.assistant_message.metadata
        self.assertIn("meta_narration", meta.get("scrubs", []))
        self.assertTrue(meta.get("meta_narration_fallback"))

"""SESSION_009: dealer onboarding fields shape live chat behavior.

Two layers of tests:

1. **Helper unit tests** (``OnboardingOverrides`` loader, tone mapping,
   phrase parsing, banned-phrase scrub, disclaimer gating). Pure-ish,
   no LLM, no chat engine — just the building blocks.

2. **Chat-engine integration tests** wired through ``MockLLMProvider``
   so we verify the helper output actually flows into the assistant
   reply (or its system messages). No real LLM call, no fragile prose
   assertions.
"""

from __future__ import annotations

from django.test import TestCase

from dealer_ai.models import ChatSession, DealerOnboardingProfile
from dealer_ai.services.chat_engine import ChatEngine
from dealer_ai.services.onboarding_overrides import (
    OnboardingOverrides,
    append_disclaimer,
    disclaimer_already_present,
    format_store_voice_block,
    load_overrides,
    parse_phrase_list,
    reply_mentions_payment,
    scrub_banned_phrases,
    should_append_disclaimer,
    tone_directive,
)
from dealer_ai.tests._mocks import MockLLMProvider, json_reply


# ---- Loader / dataclass -----------------------------------------------------


class LoadOverridesTests(TestCase):
    def test_no_profile_returns_empty_overrides(self):
        self.assertEqual(DealerOnboardingProfile.objects.count(), 0)
        overrides = load_overrides()
        self.assertTrue(overrides.is_empty)
        self.assertEqual(overrides.greeting, "")
        self.assertEqual(overrides.banned_phrases, [])
        self.assertEqual(overrides.approved_phrases, [])
        self.assertEqual(overrides.payment_disclaimer, "")

    def test_loaded_profile_populates_fields(self):
        DealerOnboardingProfile.objects.create(
            dealership_greeting="Welcome to Freedom Ford.",
            sales_tone="Warm + consultative",
            approved_phrases="Want a closer look?\nHappy to help",
            banned_phrases="guaranteed approval\nbest price ever",
            payment_disclaimer="Payments are estimates (W.A.C.).",
            escalation_rule="Hand off when finance terms come up.",
        )
        overrides = load_overrides()
        self.assertFalse(overrides.is_empty)
        self.assertEqual(overrides.greeting, "Welcome to Freedom Ford.")
        self.assertEqual(overrides.sales_tone, "Warm + consultative")
        self.assertEqual(
            overrides.approved_phrases, ["Want a closer look?", "Happy to help"]
        )
        self.assertEqual(
            overrides.banned_phrases, ["guaranteed approval", "best price ever"]
        )
        self.assertEqual(
            overrides.payment_disclaimer, "Payments are estimates (W.A.C.)."
        )
        self.assertEqual(
            overrides.escalation_rule, "Hand off when finance terms come up."
        )

    def test_load_strips_field_whitespace(self):
        DealerOnboardingProfile.objects.create(
            dealership_greeting="   Welcome.   ",
            sales_tone="  direct  ",
        )
        overrides = load_overrides()
        self.assertEqual(overrides.greeting, "Welcome.")
        self.assertEqual(overrides.sales_tone, "direct")


# ---- Phrase list parsing ---------------------------------------------------


class ParsePhraseListTests(TestCase):
    def test_empty_text_returns_empty_list(self):
        self.assertEqual(parse_phrase_list(""), [])
        self.assertEqual(parse_phrase_list("   \n\n   "), [])

    def test_strips_whitespace_per_line(self):
        self.assertEqual(
            parse_phrase_list("  one  \n  two  \nthree"),
            ["one", "two", "three"],
        )

    def test_dedupes_case_insensitively_preserves_first_casing(self):
        self.assertEqual(
            parse_phrase_list("Want a Closer Look?\nwant a closer look?\nDifferent"),
            ["Want a Closer Look?", "Different"],
        )

    def test_strips_wrapping_quotes(self):
        self.assertEqual(
            parse_phrase_list('"guaranteed approval"\n\'best price\''),
            ["guaranteed approval", "best price"],
        )

    def test_does_not_split_on_commas(self):
        # A phrase containing a comma stays a single phrase.
        self.assertEqual(
            parse_phrase_list("trucks, first-time buyers"),
            ["trucks, first-time buyers"],
        )


# ---- Tone directive --------------------------------------------------------


class ToneDirectiveTests(TestCase):
    def test_empty_input_returns_empty_string(self):
        self.assertEqual(tone_directive(""), "")

    def test_consultative_label_maps_to_directive(self):
        result = tone_directive("Warm + consultative")
        self.assertIn("consultative", result.lower())
        self.assertIn("voice", result.lower())

    def test_direct_fast_paced_maps_to_directive(self):
        result = tone_directive("Direct + fast-paced")
        self.assertTrue(result)
        self.assertIn("voice", result.lower())

    def test_unknown_label_returns_empty_string(self):
        # Caller decides what to do with a free-form unknown label
        # (chat engine passes the raw label through verbatim instead).
        self.assertEqual(tone_directive("custom-purple-mode"), "")


# ---- Store-voice system block ---------------------------------------------


class FormatStoreVoiceBlockTests(TestCase):
    def test_empty_overrides_returns_empty_string(self):
        self.assertEqual(format_store_voice_block(OnboardingOverrides()), "")

    def test_block_contains_header_and_greeting(self):
        block = format_store_voice_block(
            OnboardingOverrides(greeting="Welcome to Freedom Ford.")
        )
        self.assertIn("DEALER VOICE OVERRIDES", block)
        self.assertIn("Welcome to Freedom Ford.", block)
        # Greeting line tells the LLM not to repeat it verbatim.
        self.assertIn("do NOT repeat verbatim", block)

    def test_known_tone_label_emits_directive(self):
        block = format_store_voice_block(
            OnboardingOverrides(sales_tone="Warm + consultative")
        )
        self.assertIn("consultative", block.lower())

    def test_unknown_tone_label_passed_through_verbatim(self):
        block = format_store_voice_block(
            OnboardingOverrides(sales_tone="custom-purple-mode")
        )
        self.assertIn("custom-purple-mode", block)
        # Unknown tones get a "free-form from manager" wrapper so the LLM
        # still sees the manager's intent.
        self.assertIn("free-form", block.lower())

    def test_approved_phrases_are_listed(self):
        block = format_store_voice_block(
            OnboardingOverrides(approved_phrases=["Want a closer look?", "Happy to help"])
        )
        self.assertIn("Want a closer look?", block)
        self.assertIn("Happy to help", block)
        self.assertIn("encouraged phrasing", block.lower())
        self.assertIn("phrase-stuff", block.lower())

    def test_banned_phrases_are_listed_with_disallowed_label(self):
        block = format_store_voice_block(
            OnboardingOverrides(banned_phrases=["guaranteed approval"])
        )
        self.assertIn("guaranteed approval", block)
        self.assertIn("disallowed", block.lower())

    def test_escalation_rule_is_passed_through(self):
        rule = "Hand off when financing terms come up."
        block = format_store_voice_block(
            OnboardingOverrides(escalation_rule=rule)
        )
        self.assertIn(rule, block)
        self.assertIn("soft-handoff", block.lower())

    def test_long_phrase_lists_capped_at_ten(self):
        many = [f"phrase {i}" for i in range(20)]
        block = format_store_voice_block(
            OnboardingOverrides(approved_phrases=many)
        )
        # First ten survive; phrase 11+ are clipped.
        self.assertIn("phrase 0", block)
        self.assertIn("phrase 9", block)
        self.assertNotIn("phrase 10", block)


# ---- Banned-phrase scrub --------------------------------------------------


class ScrubBannedPhrasesTests(TestCase):
    def test_no_banned_list_is_noop(self):
        cleaned, fired, hits = scrub_banned_phrases("Hello there.", [])
        self.assertEqual(cleaned, "Hello there.")
        self.assertFalse(fired)
        self.assertEqual(hits, [])

    def test_no_match_is_noop(self):
        cleaned, fired, hits = scrub_banned_phrases(
            "We can offer a great test drive.", ["guaranteed approval"]
        )
        self.assertFalse(fired)
        self.assertEqual(cleaned, "We can offer a great test drive.")
        self.assertEqual(hits, [])

    def test_strips_sentence_containing_banned_phrase(self):
        reply = (
            "The Ranger is a great fit for your budget. "
            "We have guaranteed approval for everyone. "
            "Want me to set up a closer look?"
        )
        cleaned, fired, hits = scrub_banned_phrases(
            reply, ["guaranteed approval"]
        )
        self.assertTrue(fired)
        self.assertNotIn("guaranteed approval", cleaned.lower())
        self.assertIn("Ranger", cleaned)
        self.assertIn("closer look", cleaned)
        self.assertEqual(hits, ["guaranteed approval"])

    def test_match_is_case_insensitive(self):
        reply = "We offer GUARANTEED APPROVAL on most loans."
        cleaned, fired, _ = scrub_banned_phrases(
            reply, ["guaranteed approval"]
        )
        self.assertTrue(fired)
        self.assertNotIn("approval", cleaned.lower())

    def test_multiple_banned_phrases_logged_in_hits(self):
        reply = (
            "We have guaranteed approval here. "
            "Plus the best price ever in town. "
            "Schedule a test drive?"
        )
        cleaned, fired, hits = scrub_banned_phrases(
            reply, ["guaranteed approval", "best price ever"]
        )
        self.assertTrue(fired)
        self.assertEqual(set(hits), {"guaranteed approval", "best price ever"})
        self.assertIn("test drive", cleaned)

    def test_all_sentences_banned_returns_safe_fallback(self):
        reply = "We have guaranteed approval here. Best price ever, every day."
        cleaned, fired, _ = scrub_banned_phrases(
            reply, ["guaranteed approval", "best price ever"]
        )
        self.assertTrue(fired)
        # Defensive fallback rather than empty string.
        self.assertTrue(cleaned)
        self.assertNotIn("guaranteed", cleaned.lower())
        self.assertNotIn("best price ever", cleaned.lower())


# ---- Disclaimer gating ----------------------------------------------------


class ReplyMentionsPaymentTests(TestCase):
    def test_dollar_per_mo_pattern(self):
        self.assertTrue(reply_mentions_payment("That lands at $475/mo."))

    def test_finance_word(self):
        self.assertTrue(reply_mentions_payment("We can finance over 60 months."))

    def test_monthly_payment_phrase(self):
        self.assertTrue(reply_mentions_payment("Estimated monthly payment is reasonable."))

    def test_passing_word_payment_alone_is_false(self):
        # "payment" alone (no $X/mo, no finance) does not trigger.
        self.assertFalse(reply_mentions_payment("Down payment options vary."))

    def test_empty_reply_is_false(self):
        self.assertFalse(reply_mentions_payment(""))


class DisclaimerAlreadyPresentTests(TestCase):
    def test_full_match(self):
        d = "Payments are estimates (W.A.C.)."
        self.assertTrue(disclaimer_already_present(f"Sure thing. {d}", d))

    def test_wac_fingerprint_match(self):
        # The standard W.A.C. wording is the load-bearing fingerprint.
        d = "Payments are estimates (W.A.C.)."
        self.assertTrue(
            disclaimer_already_present(
                "That's about $475/mo (W.A.C.).", d
            )
        )

    def test_approved_credit_fingerprint_match(self):
        d = "Payments are estimates with approved credit."
        self.assertTrue(
            disclaimer_already_present(
                "Estimated payment is $475/mo with approved credit.", d
            )
        )

    def test_no_overlap(self):
        d = "Payments are estimates (W.A.C.)."
        self.assertFalse(
            disclaimer_already_present("That's a great fit.", d)
        )


class ShouldAppendDisclaimerTests(TestCase):
    DISCLAIMER = "Payments are estimates (W.A.C.)."

    def test_disclaimer_unset_never_appends(self):
        self.assertFalse(
            should_append_disclaimer(
                "$475/mo", cash_mode=False, disclaimer=""
            )
        )

    def test_cash_mode_blocks_append_even_with_payment_language(self):
        self.assertFalse(
            should_append_disclaimer(
                "Cash purchase totals $25,000.",
                cash_mode=True,
                disclaimer=self.DISCLAIMER,
            )
        )

    def test_no_payment_language_skips_append(self):
        self.assertFalse(
            should_append_disclaimer(
                "Tell me more about your priorities.",
                cash_mode=False,
                disclaimer=self.DISCLAIMER,
            )
        )

    def test_already_present_skips_append(self):
        self.assertFalse(
            should_append_disclaimer(
                "$475/mo (W.A.C.).",
                cash_mode=False,
                disclaimer=self.DISCLAIMER,
            )
        )

    def test_appends_when_payment_present_and_unique(self):
        self.assertTrue(
            should_append_disclaimer(
                "Estimated $475/mo over 60 months.",
                cash_mode=False,
                disclaimer="Custom dealership disclaimer text.",
            )
        )


class AppendDisclaimerTests(TestCase):
    def test_appends_with_separator(self):
        out = append_disclaimer(
            "That's about $475/mo.", "Custom disclaimer."
        )
        self.assertEqual(out, "That's about $475/mo. Custom disclaimer.")

    def test_strips_trailing_whitespace_from_disclaimer(self):
        out = append_disclaimer("Hello.", "  Disclaimer.   ")
        self.assertEqual(out, "Hello. Disclaimer.")

    def test_empty_reply_returns_disclaimer_only(self):
        self.assertEqual(append_disclaimer("", "Disclaimer."), "Disclaimer.")


# ---- Chat-engine integration tests (MockLLMProvider) ----------------------


def _engine_with_mock(reply_text: str) -> ChatEngine:
    """Build a ChatEngine with a MockLLMProvider scripted for two calls:
    intent-parse (returns ``{}``) and chat-reply (returns the given text).

    Provider call index 0 = intent-parse, index 1 = chat-reply. Tests that
    inspect provider system messages should look at index 1."""
    session = ChatSession.objects.create()
    return ChatEngine(
        session=session,
        provider=MockLLMProvider([json_reply({}), reply_text]),
    )


class StoreVoiceBlockIntegrationTests(TestCase):
    """The store-voice block (greeting / tone / approved / banned /
    escalation) must end up in the system messages the LLM provider
    receives. MockLLMProvider records every call so we can introspect."""

    def test_no_profile_means_no_store_voice_block(self):
        engine = _engine_with_mock("OK.")
        engine.handle_user_message("hello")
        provider = engine.provider
        assert isinstance(provider, MockLLMProvider)
        # Two calls: index 0 = intent parser, index 1 = chat reply.
        self.assertEqual(len(provider.calls), 2)
        system_messages = [
            m["content"]
            for m in provider.calls[1]
            if m.get("role") == "system"
        ]
        self.assertFalse(
            any("DEALER VOICE OVERRIDES" in m for m in system_messages),
            "store-voice block must NOT be injected when no profile exists",
        )

    def test_profile_injects_store_voice_block_with_tone_and_approved_phrases(self):
        DealerOnboardingProfile.objects.create(
            sales_tone="Warm + consultative",
            approved_phrases="Want a closer look?\nHappy to help",
            escalation_rule="Hand off when finance terms come up.",
        )
        engine = _engine_with_mock("OK.")
        engine.handle_user_message("hello")
        provider = engine.provider
        assert isinstance(provider, MockLLMProvider)
        # Inspect the chat-reply call (index 1), not the intent parser
        # (index 0). The store-voice block is only injected for the
        # chat reply, which is the user-facing layer it's meant to shape.
        system_messages = "\n\n".join(
            m["content"]
            for m in provider.calls[1]
            if m.get("role") == "system"
        )
        self.assertIn("DEALER VOICE OVERRIDES", system_messages)
        self.assertIn("consultative", system_messages.lower())
        self.assertIn("Want a closer look?", system_messages)
        self.assertIn("Hand off when finance terms come up.", system_messages)


class BannedPhraseIntegrationTests(TestCase):
    def test_banned_phrase_in_llm_reply_is_scrubbed(self):
        DealerOnboardingProfile.objects.create(
            banned_phrases="guaranteed approval"
        )
        # Reply mixes a benign sentence with the banned phrase. The scrub
        # should drop the offending sentence and keep the benign one.
        reply = (
            "The Ranger fits your budget. "
            "We have guaranteed approval for everyone. "
            "Want a closer look?"
        )
        engine = _engine_with_mock(reply)
        result = engine.handle_user_message("show me trucks")
        final_text = result.assistant_message.content
        self.assertNotIn("guaranteed approval", final_text.lower())
        # Audit metadata records the firing.
        meta = result.assistant_message.metadata
        self.assertIn("banned_phrase", meta.get("scrubs", []))
        self.assertEqual(
            meta.get("banned_phrase_hits"), ["guaranteed approval"]
        )


class DisclaimerIntegrationTests(TestCase):
    def test_disclaimer_appended_when_payment_in_reply(self):
        DealerOnboardingProfile.objects.create(
            payment_disclaimer="Custom dealership disclaimer text."
        )
        reply = "The F-150 lands at about $620/mo over 60 months."
        engine = _engine_with_mock(reply)
        result = engine.handle_user_message("show me trucks")
        final_text = result.assistant_message.content
        self.assertIn("Custom dealership disclaimer text.", final_text)
        self.assertTrue(
            result.assistant_message.metadata.get("disclaimer_appended")
        )

    def test_disclaimer_not_appended_when_already_present_via_wac(self):
        # The default disclaimer ships with W.A.C. wording; the rate
        # scrub may already have inserted "(W.A.C.)" — we must not
        # double-append.
        DealerOnboardingProfile.objects.create(
            payment_disclaimer=(
                "Payments shown are estimates. Final terms with approved credit (W.A.C.)."
            )
        )
        # Reply already contains the W.A.C. fingerprint.
        reply = "The F-150 lands at about $620/mo (W.A.C.) over 60 months."
        engine = _engine_with_mock(reply)
        result = engine.handle_user_message("show me trucks")
        final_text = result.assistant_message.content
        # We don't want the word "Final terms" to appear (would indicate
        # the configured disclaimer was appended despite the fingerprint).
        self.assertNotIn("Final terms", final_text)
        self.assertFalse(
            result.assistant_message.metadata.get("disclaimer_appended", False)
        )

    def test_disclaimer_not_appended_when_no_payment_language(self):
        DealerOnboardingProfile.objects.create(
            payment_disclaimer="Custom disclaimer."
        )
        reply = "Tell me a bit about what you're shopping for."
        engine = _engine_with_mock(reply)
        result = engine.handle_user_message("just browsing")
        final_text = result.assistant_message.content
        self.assertNotIn("Custom disclaimer.", final_text)
        self.assertFalse(
            result.assistant_message.metadata.get("disclaimer_appended", False)
        )


class FallbackBehaviorIntegrationTests(TestCase):
    """When no profile exists, behavior must be identical to the
    pre-SESSION_009 chat engine — empty fallback, no extra metadata."""

    def test_no_profile_no_disclaimer_no_banned_metadata(self):
        engine = _engine_with_mock("That's about $475/mo over 60 months.")
        result = engine.handle_user_message("show me trucks")
        meta = result.assistant_message.metadata
        self.assertNotIn("disclaimer_appended", meta)
        self.assertNotIn("banned_phrase_hits", meta)
        self.assertNotIn("banned_phrase", meta.get("scrubs", []))

    def test_no_profile_short_reply_unchanged(self):
        # Confirms the helper does not mutate replies when no profile
        # exists. The only possible mutation path is via existing scrubs;
        # a benign payment reply with no $X/mo drift should pass clean.
        engine = _engine_with_mock("Tell me a bit about what you need.")
        result = engine.handle_user_message("hi")
        self.assertEqual(
            result.assistant_message.content,
            "Tell me a bit about what you need.",
        )

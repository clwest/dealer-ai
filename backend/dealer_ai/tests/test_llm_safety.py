"""Manager Phase 4: shared post-LLM safety stack.

Closes PROJECT_PIPELINE.md §6.1 by giving every LLM-touching surface
the same scrub stack via :func:`services.llm_safety.apply_post_llm_scrubs`.

Coverage:

- Wholesale-rewrite classes (dealer-cost / negotiation) return
  ``dropped_reason`` and leave the text untouched (caller decides
  whether to drop or substitute).
- Partial scrubs strip rate / directive / default-assumption phrases
  from any kind.
- ``kind="ad"`` adds ``invented_promotion`` (save $X, limited time,
  $0 down, guaranteed approval, etc).
- ``kind="follow_up"`` adds ``invented_promotion`` AND
  ``invented_appointment`` (I'll see you Saturday at 2 PM, your
  appointment is confirmed for Tuesday at noon, etc).
- The chat-path's existing scrub functions are still locked by the
  580+ chat tests — this test file pins the *shared helper*'s
  behaviour, not the underlying scrubs themselves.
"""

from __future__ import annotations

from django.test import TestCase

from dealer_ai.services.llm_safety import apply_post_llm_scrubs


class WholesaleRewriteTests(TestCase):
    def test_dealer_cost_leak_returns_dropped_reason(self):
        text = "Our dealer cost on this F-150 is around $52,000."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="ad")
        self.assertEqual(dropped, "dealer_cost_safety")
        # Caller decides what to do — we don't mutate text on a hard drop.
        self.assertEqual(cleaned, text)
        self.assertEqual(scrubs, [])

    def test_negotiation_phrase_returns_dropped_reason(self):
        text = "I can match that price for you. We can do $48,000."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="ad")
        self.assertEqual(dropped, "post_llm_override:negotiation")
        self.assertEqual(cleaned, text)
        self.assertEqual(scrubs, [])

    def test_clean_text_returns_no_dropped_reason(self):
        text = "We have a 2025 Ford Bronco Sport in stock. (W.A.C.)"
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="ad")
        self.assertIsNone(dropped)
        self.assertEqual(cleaned, text)
        self.assertEqual(scrubs, [])

    def test_empty_input_returns_empty_output(self):
        cleaned, scrubs, dropped = apply_post_llm_scrubs("", kind="chat")
        self.assertEqual(cleaned, "")
        self.assertEqual(scrubs, [])
        self.assertIsNone(dropped)


class PartialScrubTests(TestCase):
    def test_rate_language_scrubbed_for_chat_kind(self):
        text = "Estimated $517/mo at 7.49% APR over 60 months."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertIsNone(dropped)
        self.assertNotIn("APR", cleaned)
        self.assertNotIn("7.49%", cleaned)
        self.assertIn("rate_language", scrubs)

    def test_internal_directive_scrubbed(self):
        text = "Per BUDGET ANALYSIS, the payment is around $500/mo."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertIsNone(dropped)
        self.assertNotIn("BUDGET ANALYSIS", cleaned)
        self.assertIn("internal_directive", scrubs)

    def test_default_assumption_scrubbed(self):
        text = "At the default 72-month term, payments are $400/mo."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertIsNone(dropped)
        self.assertNotIn("default 72-month", cleaned)
        self.assertIn("default_assumption", scrubs)


class AdKindTests(TestCase):
    def test_save_phrase_scrubbed(self):
        text = "Save $1,000 today on a new F-150!"
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="ad")
        self.assertIsNone(dropped)
        self.assertNotIn("Save $1,000", cleaned)
        self.assertNotIn("save $1,000", cleaned.lower())
        self.assertIn("invented_promotion", scrubs)

    def test_limited_time_scrubbed(self):
        text = "Limited time offer — visit Dealer OS today only!"
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="ad")
        self.assertNotIn("Limited time", cleaned)
        self.assertNotIn("today only", cleaned.lower())
        self.assertIn("invented_promotion", scrubs)

    def test_zero_down_scrubbed(self):
        text = "$0 down, drive home today!"
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="ad")
        self.assertNotIn("$0 down", cleaned)
        self.assertIn("invented_promotion", scrubs)

    def test_guaranteed_approval_scrubbed(self):
        text = "Guaranteed approval on any new Bronco!"
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="ad")
        self.assertNotIn("Guaranteed approval", cleaned)
        self.assertNotIn("guaranteed approval", cleaned.lower())
        self.assertIn("invented_promotion", scrubs)

    def test_chat_kind_does_not_scrub_save_phrase(self):
        # The "save $X" pattern is marketing-only. Chat replies that
        # mention a customer's saved vehicle list etc shouldn't be touched
        # — only kind=ad / kind=follow_up runs the invented_promotion scrub.
        text = "Save $1,000 today on a new F-150."
        _, scrubs, _ = apply_post_llm_scrubs(text, kind="chat")
        self.assertNotIn("invented_promotion", scrubs)


class FollowUpKindTests(TestCase):
    def test_appointment_promise_scrubbed(self):
        text = "Hi Jamie — I'll see you Saturday at 2 PM. Maria"
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text, kind="follow_up"
        )
        self.assertIsNone(dropped)
        self.assertNotIn("see you Saturday at 2 PM", cleaned)
        self.assertIn("invented_appointment", scrubs)

    def test_appointment_confirmed_scrubbed(self):
        text = "Your appointment is confirmed for Tuesday at noon."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text, kind="follow_up"
        )
        self.assertNotIn("appointment is confirmed", cleaned)
        self.assertIn("invented_appointment", scrubs)

    def test_have_you_down_scrubbed(self):
        text = "I have you down for Monday at 10 AM."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text, kind="follow_up"
        )
        self.assertNotIn("have you down", cleaned)
        self.assertIn("invented_appointment", scrubs)

    def test_promo_and_appointment_both_scrubbed(self):
        text = (
            "Limited time offer! Save $500 today. I have you down "
            "for Saturday at 1 PM."
        )
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text, kind="follow_up"
        )
        self.assertIsNone(dropped)
        self.assertNotIn("Limited time", cleaned)
        self.assertNotIn("Save $500", cleaned)
        self.assertNotIn("have you down", cleaned)
        self.assertIn("invented_promotion", scrubs)
        self.assertIn("invented_appointment", scrubs)

    def test_ad_kind_does_not_run_appointment_scrub(self):
        # Appointment-promise phrases are follow-up-only. Ad copy that
        # happens to use "see you Saturday" is unusual but the ad scrub
        # set deliberately doesn't touch it (less false-positive risk).
        text = "See you Saturday at 2 PM at Dealer OS."
        _, scrubs, _ = apply_post_llm_scrubs(text, kind="ad")
        self.assertNotIn("invented_appointment", scrubs)


class VehicleAskKindTests(TestCase):
    def test_vehicle_ask_inherits_chat_partial_scrubs(self):
        # The §6.1 fix: vehicle_assistant uses kind="vehicle_ask" which
        # gets the same partial scrubs as the chat path.
        text = "Estimated $517/mo at 7.49% APR over 60 months."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text, kind="vehicle_ask"
        )
        self.assertIsNone(dropped)
        self.assertNotIn("APR", cleaned)
        self.assertNotIn("7.49%", cleaned)
        self.assertIn("rate_language", scrubs)

    def test_vehicle_ask_drops_dealer_cost_leak(self):
        text = "Our dealer cost is around $52,000."
        _, _, dropped = apply_post_llm_scrubs(text, kind="vehicle_ask")
        self.assertEqual(dropped, "dealer_cost_safety")


class IndieProhibitedCopyTests(TestCase):
    """SESSION_030 pivot: independent-dealer prohibited copy scrub.

    Fires whenever ``get_dealer_profile().dealer_type == "independent"``
    (the shipped default post-pivot). Franchise deployments must not be
    affected — the OEM / brand-new / captive-finance language is legal
    for them.
    """

    def test_brand_new_is_softened(self):
        # No override_settings — indie is the shipped default.
        cleaned, scrubs, _ = apply_post_llm_scrubs(
            "This Camry is brand new.", kind="chat"
        )
        self.assertNotIn("brand new", cleaned.lower())
        self.assertIn("indie_prohibited_copy", scrubs)

    def test_certified_pre_owned_is_stripped(self):
        cleaned, scrubs, _ = apply_post_llm_scrubs(
            "Consider this Certified Pre-Owned Tundra.", kind="chat"
        )
        self.assertNotIn("certified pre-owned", cleaned.lower())
        self.assertIn("indie_prohibited_copy", scrubs)

    def test_manufacturer_warranty_becomes_limited_powertrain(self):
        cleaned, scrubs, _ = apply_post_llm_scrubs(
            "It still has the manufacturer warranty.", kind="chat"
        )
        self.assertIn("limited powertrain warranty", cleaned)
        self.assertIn("indie_prohibited_copy", scrubs)

    def test_factory_warranty_becomes_limited_powertrain(self):
        cleaned, _, _ = apply_post_llm_scrubs(
            "Factory warranty is still active.", kind="chat"
        )
        self.assertIn("limited powertrain warranty", cleaned)

    def test_oem_captive_lenders_become_lending_partners(self):
        for phrase in (
            "Ford Credit",
            "Toyota Financial Services",
            "Honda Financial",
            "GM Financial",
            "Nissan Motor Acceptance",
            "Chrysler Capital",
        ):
            with self.subTest(phrase=phrase):
                cleaned, scrubs, _ = apply_post_llm_scrubs(
                    f"You can finance through {phrase}.", kind="chat"
                )
                self.assertNotIn(phrase, cleaned)
                self.assertIn("our lending partners", cleaned)
                self.assertIn("indie_prohibited_copy", scrubs)

    def test_zero_percent_apr_variants_are_stripped(self):
        for phrase in ("0% APR", "0 % APR", "zero percent financing"):
            with self.subTest(phrase=phrase):
                cleaned, _, _ = apply_post_llm_scrubs(
                    f"We can offer {phrase} today.", kind="chat"
                )
                self.assertNotIn(phrase.lower(), cleaned.lower())

    def test_scrub_runs_on_ad_and_follow_up_kinds_too(self):
        for kind in ("ad", "follow_up", "vehicle_ask"):
            with self.subTest(kind=kind):
                _, scrubs, _ = apply_post_llm_scrubs(
                    "This unit is brand new.", kind=kind
                )
                self.assertIn("indie_prohibited_copy", scrubs)

    def test_no_indie_scrub_when_dealer_type_is_franchise(self):
        with self.settings(DEALER_AI_DEALER_TYPE="franchise"):
            cleaned, scrubs, _ = apply_post_llm_scrubs(
                "This F-150 is brand new with Ford Credit financing.",
                kind="chat",
            )
            # Franchise deployment — original OEM/new phrasing is legal.
            self.assertIn("brand new", cleaned.lower())
            self.assertIn("Ford Credit", cleaned)
            self.assertNotIn("indie_prohibited_copy", scrubs)

    def test_no_scrub_fires_when_text_has_no_prohibited_phrases(self):
        text = "That truck has a tow package and clean history."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind="chat")
        self.assertEqual(cleaned, text)
        self.assertNotIn("indie_prohibited_copy", scrubs)

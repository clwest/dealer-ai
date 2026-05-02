"""SESSION_010: stateless manager-side chat tester endpoint.

Endpoint: ``POST /api/dealer-ai/manager-chat/``.

Behavior:
  - Each request creates an ephemeral ``ChatSession`` tagged with
    ``metadata={"channel": "manager_test"}`` so audits / dashboards can
    filter the test traffic out of customer metrics.
  - The existing ``ChatEngine`` handles everything — including the
    SESSION_009 onboarding overrides — so manager-side voice changes
    behave identically to what a real customer would see.
  - Response is ``{"reply": <assistant text>}``. No vehicle cards.
  - Empty / missing message → 400.
"""

from __future__ import annotations

import json

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import ChatSession, DealerOnboardingProfile
from dealer_ai.tests._mocks import MockLLMProvider, json_reply


URL = reverse("dealer_ai:manager-chat")


class _ProviderInjector:
    """Patch ``ChatEngine.__init__`` so every engine instance built during
    a request uses the supplied mock provider. Plain ``patch.object`` on
    ``get_llm_provider`` doesn't fit because the manager-chat view always
    instantiates ``ChatEngine`` itself.
    """

    def __init__(self, provider: MockLLMProvider):
        self.provider = provider

    def __enter__(self):
        from dealer_ai.services import chat_engine

        original = chat_engine.ChatEngine.__init__

        def patched(inner_self, session, *, provider=None):
            return original(
                inner_self, session, provider=provider or self.provider
            )

        self._original = original
        self._patched = patched
        chat_engine.ChatEngine.__init__ = patched  # type: ignore[assignment]
        return self

    def __exit__(self, *exc):
        from dealer_ai.services import chat_engine

        chat_engine.ChatEngine.__init__ = self._original  # type: ignore[assignment]


class ManagerChatHappyPathTests(TestCase):
    def test_post_returns_assistant_reply(self):
        # SESSION_011: mock reply must be coaching-shaped (Shape A) so
        # the structural enforcer leaves it unchanged. Shapeless replies
        # are now rewritten to a deterministic coaching fallback.
        coaching = (
            "If a customer says hello, I'd open by acknowledging them "
            "and asking what they're shopping for to start qualifying."
        )
        provider = MockLLMProvider(replies=[json_reply({}), coaching])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "hello"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data, {"reply": coaching})

    def test_endpoint_creates_ephemeral_session_tagged_manager_test(self):
        provider = MockLLMProvider(replies=[json_reply({}), "ok"])
        self.assertEqual(ChatSession.objects.count(), 0)
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "hello"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)
        # One session was created for the test.
        self.assertEqual(ChatSession.objects.count(), 1)
        session = ChatSession.objects.get()
        self.assertEqual(session.metadata.get("channel"), "manager_test")

    def test_response_does_not_include_vehicle_cards(self):
        # Manager-test endpoint intentionally returns reply text only.
        provider = MockLLMProvider(replies=[json_reply({}), "hi"])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "show me trucks"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(set(data.keys()), {"reply"})

    def test_each_call_creates_a_new_session(self):
        # Stateless: a second request must NOT pick up history from the
        # first. Two sessions, no cross-contamination.
        provider = MockLLMProvider(
            replies=[json_reply({}), "first", json_reply({}), "second"]
        )
        with _ProviderInjector(provider):
            self.client.post(
                URL,
                data=json.dumps({"message": "one"}),
                content_type="application/json",
            )
            self.client.post(
                URL,
                data=json.dumps({"message": "two"}),
                content_type="application/json",
            )
        self.assertEqual(ChatSession.objects.count(), 2)


class ManagerChatValidationTests(TestCase):
    def test_missing_message_returns_400(self):
        res = self.client.post(
            URL,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400, res.content)

    def test_empty_message_returns_400(self):
        res = self.client.post(
            URL,
            data=json.dumps({"message": "   "}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400, res.content)


class ManagerChatRespectsOnboardingOverridesTests(TestCase):
    """The whole point of the manager-chat endpoint: changes the manager
    saved on /dealer-ai-onboarding must influence the assistant reply
    here, exactly like they would for a real customer."""

    def test_banned_phrase_scrubbed_from_manager_reply(self):
        # SESSION_011: surviving sentences (after banned-phrase scrub
        # strips the middle one) must be in coaching shape so the
        # structural enforcer passes them through.
        DealerOnboardingProfile.objects.create(
            banned_phrases="guaranteed approval"
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                (
                    "If a customer asks about trucks, I'd recommend "
                    "pointing them at the Ranger as a coaching example. "
                    "Avoid promising guaranteed approval since that's "
                    "marketing language we don't use. "
                    "Coach the rep to pivot to a closer look at "
                    "trade-in numbers instead."
                ),
            ]
        )
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "show me trucks"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        reply = res.json()["reply"]
        # The banned-phrase scrub from SESSION_009 fired through the
        # shared chat engine, even on this manager-test path.
        self.assertNotIn("guaranteed approval", reply.lower())
        # Surrounding coaching prose survives — the SESSION_011 enforcer
        # leaves shape-correct replies unchanged.
        self.assertIn("Ranger", reply)
        self.assertIn("closer look", reply)

    def test_no_profile_passes_reply_through_unmodified(self):
        # SESSION_011: mock reply must be coaching-shaped so the
        # structural enforcer leaves it alone.
        coaching = (
            "If a customer says hi, I'd ask what they need to start "
            "qualifying the conversation before quoting anything."
        )
        provider = MockLLMProvider(replies=[json_reply({}), coaching])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "hi"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], coaching)


# ---- SESSION_010 hotfix: card-implying phrase scrub -----------------------


class ManagerChatNoCardImplicationTests(TestCase):
    """Hotfix regression: the manager-chat endpoint never renders cards,
    so the reply must never imply visible options. Two layers of
    defense: (1) MANAGER_TEST_HINT system message tells the LLM not
    to produce card-implying language; (2) scrub_card_implying_phrases
    in the view strips any sentences that slip through."""

    def test_user_reported_bad_reply_is_repaired(self):
        """The exact pattern reported in the SESSION_010 hotfix issue:
        an LLM reply that splits across three card-implying sentences
        ending in "Which one of these trucks catches your eye?"."""
        bad_reply = (
            "Wanting a truck under $30k means you're looking at some great "
            "options. Let me show you some trucks that fit your budget. "
            "Here are a few options: Which one of these trucks catches "
            "your eye?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad_reply])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "I want a truck under 30k"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        reply = res.json()["reply"]
        # None of the reported card-implying phrasings may survive.
        forbidden = [
            "here are a few options",
            "let me show you",
            "let's take a look",
            "take a look at some",
            "these vehicles",
            "these trucks",
            "which one of these",
            "take a look at these",
            "pick one of these",
            "looking at some great options",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase,
                reply.lower(),
                f"manager-chat reply must not imply visible cards (saw {phrase!r})",
            )

    def test_first_person_inventory_claim_is_stripped(self):
        """Coaching follow-up: replies that pretend the dealership has
        specific inventory rendered ("We have a 2020 Chevrolet Colorado",
        "Our F-150 starts at $24,000") get scrubbed because no card is
        actually being shown.

        SESSION_011: outer coaching frame and trailing coaching prose
        ensure the surviving text stays on-shape after the inventory-
        claim sentences are stripped."""
        bad_reply = (
            "If a customer says they want a truck under $30k, "
            "I'd say there are good options across used inventory. "
            "We have a 2020 Chevrolet Colorado LT in stock. "
            "Our F-150 starts at $28,000. "
            "Coaching the rep on a closer comparison comes next."
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad_reply])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "trucks under 30k"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)
        reply = res.json()["reply"]
        forbidden = [
            "we have a 2020",
            "our f-150",
            "starts at $",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase,
                reply.lower(),
                f"first-person inventory claim survived ({phrase!r})",
            )
        # The coaching opener and the closing question survive — the
        # scrub is sentence-level.
        self.assertIn("good options", reply.lower())

    def test_one_option_is_the_X_pattern_is_stripped(self):
        bad_reply = (
            "I'd narrow what matters first. "
            "One option is the Chevrolet Colorado LT. "
            "Another option is the Ford Ranger XL. "
            "What matters most for this customer?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad_reply])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "trucks"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        # The "One option is the X" / "Another option is the Y"
        # sentences are inventory-claim shapes for coaching mode.
        self.assertNotIn("one option is the", reply.lower())
        self.assertNotIn("another option is the", reply.lower())
        # The coaching prose and qualifying question still survive.
        self.assertIn("narrow what matters first", reply)
        self.assertIn("matters most", reply.lower())

    def test_coaching_frame_reply_passes_through(self):
        """Pure coaching replies (the ideal shape per the product
        decision) must NOT be modified — the scrub is additive, not
        subtractive on good prose. Mentions of model names in coaching
        context are fine; only first-person inventory claims get
        stripped."""
        coaching_reply = (
            "If a customer asks about trucks under $30k, I'd narrow the "
            "deal first: 4WD, cab size, towing, or mileage. The "
            "assistant should ask one clean qualifying question like "
            "\"What matters most: 4WD, crew cab, towing, or lowest "
            "miles?\" before quoting any specific Ranger or Maverick."
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), coaching_reply]
        )
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "trucks under 30k"}),
                content_type="application/json",
            )
        self.assertEqual(res.json()["reply"], coaching_reply)

    def test_safe_fallback_when_every_sentence_strips(self):
        # Pathological case: every sentence is card-implying. The view
        # must still return SOMETHING usable — the safe fallback.
        all_bad = (
            "Let me show you some trucks. "
            "Here are a few options. "
            "Take a look at these models."
        )
        provider = MockLLMProvider(replies=[json_reply({}), all_bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "I want a truck"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)
        reply = res.json()["reply"]
        self.assertTrue(reply.strip())
        # The safe fallback is a manager-coaching prompt; it ends with a
        # focused next-step question (not a card promise).
        self.assertIn("?", reply)
        for phrase in [
            "here are a few options",
            "let me show you",
            "these trucks",
            "take a look at these",
        ]:
            self.assertNotIn(phrase, reply.lower())

    def test_clean_reply_passes_through_unmodified(self):
        # The hint is meant to nudge the LLM, but a reply that already
        # avoids the patterns must NOT be modified — the scrub is
        # additive, not subtractive on good prose.
        clean_reply = (
            "Under $30k, I'd narrow what matters most for this customer "
            "first — 4WD, crew cab, or lowest miles? That gives the "
            "salesperson a way to focus before quoting inventory."
        )
        provider = MockLLMProvider(replies=[json_reply({}), clean_reply])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "I want a truck under 30k"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], clean_reply)

    def test_hint_reaches_llm_call(self):
        # Inspect MockLLMProvider.calls[1] (chat-reply call): system
        # messages must include the MANAGER_COACHING_HINT marker and
        # the role-reframe to "internal sales coaching advisor".
        provider = MockLLMProvider(replies=[json_reply({}), "ok"])
        with _ProviderInjector(provider):
            self.client.post(
                URL,
                data=json.dumps({"message": "hi"}),
                content_type="application/json",
            )
        # provider.calls = [intent_parse_call, chat_reply_call]
        chat_systems = "\n\n".join(
            m["content"]
            for m in provider.calls[1]
            if m.get("role") == "system"
        )
        # Marker phrase asserted by tests; do not change without
        # updating the constant in manager_chat_response.py.
        self.assertIn("MANAGER COACHING MODE", chat_systems)
        # Role re-frame line — the LLM must understand it is coaching,
        # not impersonating the assistant.
        self.assertIn("INTERNAL SALES COACHING ADVISOR", chat_systems)
        # Sanity: the hint names at least one of the forbidden
        # phrasings so the LLM has the explicit list.
        self.assertIn("Which one catches your eye", chat_systems)
        # Anti-shape rule: explicit "you are NOT the customer-facing
        # assistant" guidance.
        self.assertIn("NOT the customer-facing assistant", chat_systems)


class CustomerChatNotAffectedByManagerHintTests(TestCase):
    """The hint and scrub must NOT leak into the customer-facing chat
    path. A regular ``send_message`` call (no manager_test channel)
    produces the original reply unchanged."""

    def test_send_message_does_not_inject_manager_hint(self):
        from dealer_ai.models import ChatSession
        from dealer_ai.services.chat_engine import ChatEngine

        session = ChatSession.objects.create()  # no channel metadata
        provider = MockLLMProvider(
            replies=[json_reply({}), "Here are a few options for you."]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("show me trucks")
        # Inspect the chat-reply call: NO manager-coaching marker.
        chat_systems = "\n\n".join(
            m["content"]
            for m in provider.calls[1]
            if m.get("role") == "system"
        )
        self.assertNotIn("MANAGER COACHING MODE", chat_systems)
        self.assertNotIn("INTERNAL SALES COACHING ADVISOR", chat_systems)

    def test_send_message_reply_is_not_card_scrubbed(self):
        # Customer chat keeps card-implying phrasing — those replies are
        # accompanied by real cards in the customer demo. The view-level
        # card scrub lives ONLY in manager_chat.
        from dealer_ai.models import ChatSession
        from dealer_ai.services.chat_engine import ChatEngine

        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[json_reply({}), "Here are a few options for you."]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("show me trucks")
        self.assertIn(
            "here are a few options",
            result.assistant_message.content.lower(),
        )


# ---- SESSION_011: structural shape enforcement ----------------------------


class ManagerChatStructureEnforcementTests(TestCase):
    """SESSION_011: the manager-chat view must enforce response *structure*,
    not just strip known-bad sentences. Replies that lack a coaching
    frame OR contain customer-facing patterns (the-card references,
    first-person delivery, customer-directed closes) are replaced with
    a deterministic coaching fallback built from the customer message.

    These tests cover Jessica's reported failure plus the families of
    customer-facing wording the static scrub doesn't catch."""

    def test_jessica_reported_failure_is_repaired(self):
        """The exact reply Jessica saw on the coaching page when she
        sent 'i have $400/mo and want a sedan'. Three independent
        customer-facing failures: 'in our inventory' / 'the card'
        reference, 'I can show you' delivery, and a customer-directed
        closing question. None of these match the SESSION_010 static
        scrub patterns; the SESSION_011 structural enforcer must catch
        them all by detecting the customer-facing *family*."""
        bad_reply = (
            "Most sedans in our inventory fall under the payment shown "
            "on the card, but I can show you some options that might "
            "fit your budget. Would that be something you'd consider?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad_reply])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps(
                    {"message": "i have $400/mo and want a sedan"}
                ),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        reply = res.json()["reply"]
        forbidden = [
            "in our inventory",
            "the card",
            "shown on the card",
            "i can show you",
            "fit your budget",
            "would that be something",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase,
                reply.lower(),
                f"Jessica's failure phrase survived: {phrase!r}",
            )
        # Fallback is context-aware — pulled "sedan" + "$400/mo" from
        # the customer message.
        self.assertIn("sedan", reply.lower())
        self.assertIn("$400/mo", reply)
        # And the fallback opens in coaching shape.
        self.assertIn("If a customer", reply)

    def test_shape_a_pure_coaching_passes_through(self):
        clean = (
            "If a customer asks about trucks under $30k, I'd narrow "
            "the deal first: 4WD, cab size, towing, or mileage. "
            "The assistant should ask one clean qualifying question."
        )
        provider = MockLLMProvider(replies=[json_reply({}), clean])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "trucks under 30k"}),
                content_type="application/json",
            )
        self.assertEqual(res.json()["reply"], clean)

    def test_shape_b_coaching_with_quoted_preview_passes_through(self):
        """Shape B: coaching frame + a quoted sample customer-facing
        reply. Customer-facing phrasing inside the quote is allowed —
        the enforcer strips quoted segments before checking."""
        clean = (
            "I'd open by acknowledging the budget and narrowing "
            "priorities. A strong response: \"Absolutely — under $30k, "
            "what matters most: 4WD, crew cab, towing, or lowest "
            "miles?\""
        )
        provider = MockLLMProvider(replies=[json_reply({}), clean])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "trucks under 30k"}),
                content_type="application/json",
            )
        self.assertEqual(res.json()["reply"], clean)

    def test_the_card_reference_triggers_fallback(self):
        bad = (
            "Take a look at the card for the Bronco — the price is "
            "right there. Anything you want to know about it?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "tell me about the bronco"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertNotIn("the card", reply.lower())
        self.assertIn("If a customer", reply)

    def test_i_can_show_you_triggers_fallback(self):
        """Jessica's specific 'I can show you' delivery — not caught
        by the SESSION_010 'let me show you' / 'I'll show you' static
        patterns."""
        bad = "I can show you the Ford lineup so you can pick one."
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "show me trucks"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertNotIn("i can show you", reply.lower())
        self.assertIn("If a customer", reply)
        self.assertIn("truck", reply.lower())

    def test_customer_directed_close_does_that_sound_good_triggers_fallback(self):
        bad = (
            "These trims are similar in price. Does that sound good "
            "for you?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "what trims are available"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertNotIn("does that sound good", reply.lower())
        self.assertIn("If a customer", reply)

    def test_customer_directed_would_that_be_something_triggers_fallback(self):
        bad = (
            "There's a Maverick that might work. Would that be "
            "something you'd consider?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "i want a small truck"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertNotIn("would that be something", reply.lower())
        self.assertIn("If a customer", reply)

    def test_shapeless_reply_with_no_coaching_frame_triggers_fallback(self):
        """Reply with no customer-facing patterns AND no coaching-frame
        marker is shapeless — enforcer rewrites."""
        bad = "Trucks are great. The Ranger is solid. Used too."
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "i want a truck"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertIn("If a customer", reply)
        self.assertIn("truck", reply.lower())

    def test_fallback_is_context_aware_truck_under_30k(self):
        bad = "I can show you stuff."
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "i want a truck under 30k"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertIn("truck", reply.lower())
        self.assertIn("under $30,000", reply)

    def test_fallback_is_context_aware_sedan_400_per_month(self):
        bad = "I can show you sedans."
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps(
                    {"message": "i have $400/mo and want a sedan"}
                ),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertIn("sedan", reply.lower())
        self.assertIn("$400/mo", reply)

    def test_fallback_is_context_aware_suv(self):
        bad = "I can show you SUVs."
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "looking for an suv"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertIn("SUV", reply)

    def test_fallback_falls_back_to_generic_vehicle_when_unknown(self):
        bad = "I can show you something."
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "hi"}),
                content_type="application/json",
            )
        reply = res.json()["reply"]
        self.assertIn("vehicle", reply.lower())
        self.assertIn("If a customer", reply)

    def test_hint_includes_required_structure_markers(self):
        """The SESSION_011 tightened MANAGER_COACHING_HINT must
        explicitly declare required structure (Shape A / Shape B) AND
        list 'I can show you' / 'Would that be something' as forbidden
        — these were the new families Jessica's failure exposed."""
        provider = MockLLMProvider(replies=[json_reply({}), "ok"])
        with _ProviderInjector(provider):
            self.client.post(
                URL,
                data=json.dumps({"message": "hi"}),
                content_type="application/json",
            )
        chat_systems = "\n\n".join(
            m["content"]
            for m in provider.calls[1]
            if m.get("role") == "system"
        )
        self.assertIn("REQUIRED RESPONSE STRUCTURE", chat_systems)
        self.assertIn("Shape A", chat_systems)
        self.assertIn("Shape B", chat_systems)
        self.assertIn("I can show you", chat_systems)
        self.assertIn("Would that be something", chat_systems)


class ManagerChatEnforceCoachingShapeUnitTests(TestCase):
    """Unit tests for ``enforce_coaching_shape`` directly — no view,
    no chat engine, no LLM provider. Lets the structure logic be
    debugged in isolation from the integration path."""

    def test_pure_coaching_returns_unchanged(self):
        from dealer_ai.services.manager_chat_response import (
            enforce_coaching_shape,
        )

        text = (
            "If a customer asks about trucks, I'd narrow priorities "
            "before quoting any specific inventory."
        )
        out, action = enforce_coaching_shape(text, "trucks")
        self.assertEqual(out, text)
        self.assertEqual(action, "unchanged")

    def test_jessica_failure_returns_rewritten(self):
        from dealer_ai.services.manager_chat_response import (
            enforce_coaching_shape,
        )

        text = (
            "Most sedans in our inventory fall under the payment shown "
            "on the card, but I can show you some options that might "
            "fit your budget. Would that be something you'd consider?"
        )
        out, action = enforce_coaching_shape(
            text, customer_message="i have $400/mo and want a sedan"
        )
        self.assertEqual(action, "rewritten")
        self.assertIn("If a customer", out)
        self.assertIn("sedan", out.lower())
        self.assertIn("$400/mo", out)

    def test_only_card_scrubs_fired_returns_scrubbed(self):
        """Reply has card-implying sentence(s) the static scrub
        catches AND surrounding coaching prose. Surviving text is on
        shape — action is 'scrubbed', not 'rewritten'."""
        from dealer_ai.services.manager_chat_response import (
            enforce_coaching_shape,
        )

        text = (
            "If a customer asks about trucks, I'd narrow priorities "
            "first. One option is the Ranger XL. The assistant should "
            "ask one focused qualifying question."
        )
        out, action = enforce_coaching_shape(text, "trucks")
        self.assertEqual(action, "scrubbed")
        self.assertNotIn("One option is the Ranger", out)
        self.assertIn("If a customer", out)
        self.assertIn("assistant should", out)

    def test_empty_reply_passes_through(self):
        from dealer_ai.services.manager_chat_response import (
            enforce_coaching_shape,
        )

        out, action = enforce_coaching_shape("", "anything")
        self.assertEqual(out, "")
        self.assertEqual(action, "empty_input")

    def test_quoted_preview_protects_inner_customer_phrases(self):
        """Customer-facing phrasing inside a double-quoted sample reply
        is part of Shape B — it must NOT trigger the customer-facing
        fallback."""
        from dealer_ai.services.manager_chat_response import (
            enforce_coaching_shape,
        )

        text = (
            "I'd open with the budget. A strong response: "
            "\"I can show you a few options that fit your budget — "
            "want to take a closer look?\""
        )
        out, action = enforce_coaching_shape(text, "trucks")
        # Outer prose is coaching ("I'd open"); inner quote is a sample
        # reply allowed to use customer-facing phrasing.
        self.assertEqual(out, text)
        self.assertEqual(action, "unchanged")

    def test_fallback_handles_truck_under_30k(self):
        from dealer_ai.services.manager_chat_response import (
            _coaching_fallback,
        )

        out = _coaching_fallback("I want a truck under 30k")
        self.assertIn("truck", out.lower())
        self.assertIn("under $30,000", out)

    def test_fallback_handles_sedan_400_per_month(self):
        from dealer_ai.services.manager_chat_response import (
            _coaching_fallback,
        )

        out = _coaching_fallback("i have $400/mo and want a sedan")
        self.assertIn("sedan", out.lower())
        self.assertIn("$400/mo", out)

    def test_fallback_handles_unknown_input(self):
        from dealer_ai.services.manager_chat_response import (
            _coaching_fallback,
        )

        out = _coaching_fallback("")
        self.assertIn("vehicle", out.lower())
        self.assertIn("If a customer", out)

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
        provider = MockLLMProvider(
            replies=[json_reply({}), "Sure thing — what are you shopping for?"]
        )
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "hello"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data, {"reply": "Sure thing — what are you shopping for?"})

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
        DealerOnboardingProfile.objects.create(
            banned_phrases="guaranteed approval"
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                (
                    "The Ranger fits your budget. "
                    "We have guaranteed approval for everyone. "
                    "Want a closer look?"
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
        self.assertIn("Ranger", reply)
        self.assertIn("closer look", reply)

    def test_no_profile_passes_reply_through_unmodified(self):
        provider = MockLLMProvider(
            replies=[json_reply({}), "Tell me a bit about what you need."]
        )
        with _ProviderInjector(provider):
            res = self.client.post(
                URL,
                data=json.dumps({"message": "hi"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["reply"], "Tell me a bit about what you need.")


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
        # messages must include the MANAGER_TEST_HINT marker.
        from dealer_ai.services.manager_chat_response import MANAGER_TEST_HINT

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
        # Use a marker phrase from the hint that's specific enough to
        # avoid false matches with SYSTEM_PROMPT.
        self.assertIn("MANAGER TEST MODE", chat_systems)
        # Sanity: the hint also names at least one of the forbidden
        # phrasings so the LLM has the explicit list.
        self.assertIn("Which one catches your eye", chat_systems)


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
        # Inspect the chat-reply call: NO manager-test marker.
        chat_systems = "\n\n".join(
            m["content"]
            for m in provider.calls[1]
            if m.get("role") == "system"
        )
        self.assertNotIn("MANAGER TEST MODE", chat_systems)

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

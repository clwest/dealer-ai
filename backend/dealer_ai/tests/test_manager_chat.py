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

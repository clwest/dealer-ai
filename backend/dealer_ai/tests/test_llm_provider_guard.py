"""Guard tests for the LLM provider boundary.

Two families here:

1. **SDK / model signature guard.** For every model family listed in
   ``openai_provider._REASONING_PREFIXES`` the provider must be able to
   compose a request the installed SDK will actually deliver. If a
   future SDK drops the compatibility retry, or a future model family
   needs another new parameter, this test surfaces the mismatch before
   a demo does — the 2026-09-03 demo walk caught the last such drift
   only after five failed customer prompts.

2. **Outage propagation.** ``LLMProvider.chat()`` raises
   ``ProviderUnavailable`` on unrecoverable failure. The customer chat
   surface returns the apology text; the manager coaching surface
   returns the manager degraded reply and NEVER runs
   ``_coaching_fallback()`` on an outage — the "purple submarine"
   regression is here.
"""

from __future__ import annotations

import inspect
import json
from typing import Iterable, List

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.services.llm.base import (
    CUSTOMER_OUTAGE_REPLY,
    MANAGER_OUTAGE_REPLY,
    ChatMessage,
    LLMProvider,
    ProviderUnavailable,
)
from dealer_ai.services.llm.openai_provider import (
    _REASONING_PREFIXES,
    OpenAIProvider,
)
from dealer_ai.tests._auth_helpers import sales_manager_client_at_default
from dealer_ai.tests._mocks import json_reply


MANAGER_URL = reverse("dealer_ai:manager-chat")


# ---------------------------------------------------------------------------
# 1. SDK / model signature guard
# ---------------------------------------------------------------------------


class OpenAIProviderShapeCompatTests(TestCase):
    """The provider must produce a request the SDK can transmit for each
    reasoning family it claims to support. Where the SDK signature is
    too old, the provider's ``TypeError`` retry path handles the drift
    and the request reaches the API on legacy shape.
    """

    def _make_provider(self, model: str) -> OpenAIProvider:
        return OpenAIProvider(api_key="test", model=model)

    def _sample_model_for(self, prefix: str) -> str:
        # A representative model name per family. Only the prefix
        # matters for _is_reasoning_model detection.
        return {
            "gpt-5": "gpt-5-mini",
            "o1": "o1-mini",
            "o3": "o3-mini",
            "o4": "o4-mini",
        }[prefix]

    def test_every_reasoning_family_produces_a_deliverable_request(self):
        """For each reasoning family we support, at least one of the
        first-try shape (``max_completion_tokens``) or the retry shape
        (``max_tokens``) must be accepted by the installed SDK. If
        both were rejected the provider could not talk to the model
        at all, and the demo would never reach the API.

        NOTE: this test was written to fail on ``openai==1.30.5`` +
        ``gpt-5-mini`` BEFORE the ``TypeError`` retry existed in
        ``OpenAIProvider.chat()`` — its first-try shape used
        ``max_completion_tokens`` and the SDK rejected it with
        ``TypeError``. The retry (added in the same change as this
        test) is what makes it green today. See
        ``dealer_ai.checks.W001`` for the operator-facing warning
        that keeps the underlying pin-and-model mismatch visible.
        """
        for prefix in _REASONING_PREFIXES:
            model = self._sample_model_for(prefix)
            provider = self._make_provider(model)
            sig = inspect.signature(provider._client.chat.completions.create)
            first_try = provider._build_params(
                [{"role": "user", "content": "hello"}],
                temperature=0.4,
                max_tokens=800,
            )
            fallback = provider._legacy_fallback_params(first_try, max_tokens=800)
            first_ok = all(k in sig.parameters for k in first_try)
            fallback_ok = all(k in sig.parameters for k in fallback)
            self.assertTrue(
                first_ok or fallback_ok,
                msg=(
                    f"Neither the first-try nor the legacy-fallback param "
                    f"shape is deliverable for model {model!r}. "
                    f"SDK signature accepts: "
                    f"{sorted(k for k in sig.parameters)[:12]}"
                ),
            )

    def test_typeerror_on_unexpected_kwarg_triggers_legacy_retry(self):
        """The retry fires when the SDK rejects ``max_completion_tokens``
        with a matching TypeError, and re-raises anything else.
        """

        class _FakeCompletions:
            def __init__(self):
                self.calls: list = []

            def create(self, **params):
                self.calls.append(params)
                if "max_completion_tokens" in params:
                    raise TypeError(
                        "Completions.create() got an unexpected "
                        "keyword argument 'max_completion_tokens'"
                    )

                class _Choice:
                    def __init__(self, text):
                        self.message = type("m", (), {"content": text})()

                class _Resp:
                    def __init__(self, text):
                        self.choices = [_Choice(text)]

                return _Resp("ok")

        class _FakeChat:
            def __init__(self):
                self.completions = _FakeCompletions()

        class _FakeClient:
            def __init__(self):
                self.chat = _FakeChat()

        provider = OpenAIProvider(api_key="test", model="gpt-5-mini")
        provider._client = _FakeClient()  # type: ignore[assignment]

        reply = provider.chat([{"role": "user", "content": "hello"}])

        self.assertEqual(reply, "ok")
        # First call used max_completion_tokens (rejected); second used
        # legacy max_tokens shape.
        calls = provider._client.chat.completions.calls  # type: ignore[attr-defined]
        self.assertEqual(len(calls), 2)
        self.assertIn("max_completion_tokens", calls[0])
        self.assertNotIn("max_completion_tokens", calls[1])
        self.assertIn("max_tokens", calls[1])

    def test_unrelated_exception_raises_provider_unavailable(self):
        class _FakeCompletions:
            def create(self, **params):
                raise RuntimeError("boom")

        class _FakeChat:
            def __init__(self):
                self.completions = _FakeCompletions()

        class _FakeClient:
            def __init__(self):
                self.chat = _FakeChat()

        provider = OpenAIProvider(api_key="test", model="gpt-4o-mini")
        provider._client = _FakeClient()  # type: ignore[assignment]

        with self.assertRaises(ProviderUnavailable):
            provider.chat([{"role": "user", "content": "hello"}])


# ---------------------------------------------------------------------------
# 2. Outage propagation across surface boundaries
# ---------------------------------------------------------------------------


class _MixedProvider(LLMProvider):
    """Return scripted replies for the first ``n`` calls, raise
    ``ProviderUnavailable`` for the rest. Lets a test cover the
    intent-parser-then-outage sequence in one request without leaking
    the outage into the intent parser (which catches Exception).
    """

    name = "mixed_mock"

    def __init__(self, replies: List[str]):
        self.replies = replies
        self.calls: List[List[dict]] = []

    def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 800,
        **kwargs,
    ) -> str:
        idx = len(self.calls)
        self.calls.append(self.normalize(messages))
        if idx < len(self.replies):
            return self.replies[idx]
        raise ProviderUnavailable("simulated outage")


class _ProviderInjector:
    def __init__(self, provider):
        self.provider = provider

    def __enter__(self):
        from dealer_ai.services import chat_engine

        original = chat_engine.ChatEngine.__init__

        def patched(inner_self, session, *, provider=None):
            return original(
                inner_self, session, provider=provider or self.provider
            )

        self._original = original
        chat_engine.ChatEngine.__init__ = patched  # type: ignore[assignment]
        return self

    def __exit__(self, *exc):
        from dealer_ai.services import chat_engine

        chat_engine.ChatEngine.__init__ = self._original  # type: ignore[assignment]


class ManagerChatOutageTests(TestCase):
    """The regression the 2026-09-03 walk found: on a provider outage the
    manager coaching endpoint returned a byte-identical coaching template
    for unrelated prompts, so the demo looked like the LLM answered.
    """

    def setUp(self):
        self.client = sales_manager_client_at_default()

    def _post(self, message: str):
        return self.client.post(
            MANAGER_URL,
            data=json.dumps({"message": message}),
            content_type="application/json",
        )

    def test_provider_outage_returns_manager_outage_reply_not_coaching_fallback(self):
        # First call is intent_parser (json), second is the reply.
        # The reply call raises ProviderUnavailable.
        provider = _MixedProvider(replies=[json_reply({})])
        with _ProviderInjector(provider):
            res = self._post(
                "I want a purple submarine with heated seats for $2 million"
            )
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data.get("provider_unavailable"), True)
        self.assertEqual(data.get("reply"), MANAGER_OUTAGE_REPLY)
        # The coaching fallback opener must NOT appear on an outage.
        self.assertNotIn("If a customer says they want", data.get("reply", ""))
        self.assertNotIn(
            "narrow the conversation", data.get("reply", "")
        )

    def test_two_different_outage_prompts_produce_the_same_reply_and_thats_ok(self):
        """The manager outage reply is intentionally fixed — that is the
        signal. What must NOT be true is that a coaching-shaped reply
        comes back byte-identical for unrelated prompts, because that
        looks like the model answered. The manager outage reply is
        clearly labelled as an outage.
        """
        # One reply for the FIRST request's intent parser only; every
        # other call (2nd request's intent parser + both chat calls)
        # raises. Intent-parser exceptions are caught by that service;
        # the chat call's exception is what we exercise here.
        provider = _MixedProvider(replies=[json_reply({})])
        with _ProviderInjector(provider):
            r1 = self._post("purple submarine")
            r2 = self._post("$9,000 commuter car")
        # Both are the outage reply.
        self.assertEqual(r1.json().get("reply"), MANAGER_OUTAGE_REPLY)
        self.assertEqual(r2.json().get("reply"), MANAGER_OUTAGE_REPLY)
        # And the outage reply explicitly labels itself as an outage —
        # this is the property that keeps it honest.
        self.assertIn("AI service is unavailable", MANAGER_OUTAGE_REPLY)


class CustomerChatOutageTests(TestCase):
    def setUp(self):
        # /chat/start/ is unauthenticated — a customer opens the demo
        # page without logging in.
        self.client = APIClient()

    def test_provider_outage_returns_apology_text(self):
        from dealer_ai.models import ChatMessage

        # One reply for the intent parser; the actual chat call raises.
        provider = _MixedProvider(replies=[json_reply({})])
        with _ProviderInjector(provider):
            res = self.client.post(
                reverse("dealer_ai:chat-start"),
                data=json.dumps(
                    {"customer_name": "Outage Test", "initial_message": "hi"}
                ),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 201, res.content)
        data = res.json()
        reply = data["assistant_message"]["content"]
        self.assertEqual(reply, CUSTOMER_OUTAGE_REPLY)
        # The turn is flagged as an outage in metadata so audits can
        # find it without regex-matching the apology string. The
        # serializer does not expose metadata, so read it from the DB.
        msg = ChatMessage.objects.get(id=data["assistant_message"]["id"])
        self.assertEqual(
            (msg.metadata or {}).get("flag"), "provider_unavailable"
        )


class ProviderUnavailableIsARuntimeErrorTests(TestCase):
    """Existing callers (ad_copy, follow_up, intent_parser,
    handoff_service, lead_service, vehicle_assistant) catch broad
    ``Exception``. Confirm ``ProviderUnavailable`` is an ``Exception``
    subclass so those catches keep working — otherwise their
    deterministic fallbacks would not fire on a real outage.
    """

    def test_provider_unavailable_is_exception_subclass(self):
        self.assertTrue(issubclass(ProviderUnavailable, Exception))
        self.assertTrue(issubclass(ProviderUnavailable, RuntimeError))

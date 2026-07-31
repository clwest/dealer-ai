"""SESSION_030 pivot: INDIE_MODE_HINT prompt-injection contract.

The indie-mode system fragment is appended to the LLM message list
only when :func:`get_dealer_profile` returns
``dealer_type == "independent"``. Franchise deployments must not see
it — the base ``SYSTEM_PROMPT`` already handles franchise semantics.
"""

from __future__ import annotations

from django.test import TestCase, override_settings

from dealer_ai.models import ChatSession
from dealer_ai.services.chat_engine import (
    INDIE_MODE_HINT,
    ChatEngine,
)
from dealer_ai.tests._mocks import MockLLMProvider, json_reply


def _system_messages(mock_calls) -> list[str]:
    """Extract the concatenated system-role content from a mock call."""
    if not mock_calls:
        return []
    first_call = mock_calls[-1]
    return [m["content"] for m in first_call if m["role"] == "system"]


class IndieModeHintInjection(TestCase):
    def _run_engine(self) -> MockLLMProvider:
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}),  # intent extraction
                "Sure — I can help with that.",  # customer-facing reply
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("Just looking around today")
        return provider

    def test_indie_default_injects_the_hint(self):
        # Default DealerProfile is independent — hint should appear.
        provider = self._run_engine()
        systems = _system_messages(provider.calls)
        joined = "\n".join(systems)
        self.assertIn("INDEPENDENT DEALER MODE", joined)

    @override_settings(
        DEALER_AI_DEALER_TYPE="franchise",
        DEALER_AI_PRIMARY_MAKE="Ford",
    )
    def test_franchise_config_skips_the_hint(self):
        provider = self._run_engine()
        systems = _system_messages(provider.calls)
        joined = "\n".join(systems)
        self.assertNotIn("INDEPENDENT DEALER MODE", joined)

    def test_hint_content_reinforces_no_oem_captive(self):
        # Lock the key guidance the hint carries — future edits that
        # regress these bullets should fail here rather than in a
        # subtle behavior drift months from now.
        self.assertIn("captive financing", INDIE_MODE_HINT)
        self.assertIn("Ford Credit", INDIE_MODE_HINT)
        self.assertIn("limited powertrain warranty", INDIE_MODE_HINT)
        self.assertIn("AS-IS", INDIE_MODE_HINT)
        self.assertIn("credit tier", INDIE_MODE_HINT.lower())
        self.assertIn("in-house", INDIE_MODE_HINT.lower())

    def test_hint_uses_dealer_name_placeholder(self):
        # The rendered fragment substitutes {dealer_name} at call time,
        # matching the pattern the rest of the prompt stack uses.
        self.assertIn("{dealer_name}", INDIE_MODE_HINT)

    @override_settings(DEALER_AI_DEALER_NAME="Copper Canyon Auto")
    def test_hint_renders_configured_dealer_name(self):
        provider = self._run_engine()
        joined = "\n".join(_system_messages(provider.calls))
        self.assertIn("Copper Canyon Auto", joined)
        # And the placeholder itself must not survive rendering.
        self.assertNotIn("{dealer_name}", joined)

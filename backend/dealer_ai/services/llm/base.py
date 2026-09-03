"""Base LLM provider interface.

All providers must implement `chat(messages, **kwargs) -> str`.
Messages follow the OpenAI-style schema: [{"role": "system|user|assistant", "content": "..."}].
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Mapping


ChatMessage = Mapping[str, str]


# Canonical user-visible outage text for the customer-facing assistant.
# Kept here so both the surface boundary that catches ``ProviderUnavailable``
# and the tests that assert on it read from the same constant.
CUSTOMER_OUTAGE_REPLY = (
    "I'm having trouble reaching the AI service right now. "
    "Please try again in a moment."
)


# Canonical degraded-mode text for the manager coaching surface. This is
# deliberately distinct from ``manager_chat_response._coaching_fallback()``
# — the coaching template is for a model that answered *badly*, not for a
# model that never answered. A shaped fallback with a "purple submarine"
# reply would look like coaching worked when in fact no LLM ran.
MANAGER_OUTAGE_REPLY = (
    "The AI service is unavailable right now, so this turn didn't reach "
    "the assistant. This is a service outage, not coaching guidance — "
    "try again in a moment. If it persists, check the OpenAI / Ollama "
    "configuration and the server logs."
)


class ProviderUnavailable(RuntimeError):
    """Raised by ``LLMProvider.chat()`` when the request cannot complete.

    An outage must be distinguishable from an on-shape reply. Callers at
    surface boundaries catch this and produce a boundary-appropriate
    degraded response — the customer assistant returns its apology
    string; the manager coaching surface returns a distinct degraded
    reply (not ``_coaching_fallback()``, which is for a model that
    answered badly, not a model that never answered). Text-composing
    callers must never persist an outage message as content.
    """


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 800,
        **kwargs,
    ) -> str:
        """Return the assistant's text reply for the given message history."""

    @staticmethod
    def normalize(messages: Iterable[ChatMessage]) -> List[dict]:
        out: List[dict] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if not content:
                continue
            out.append({"role": role, "content": content})
        return out

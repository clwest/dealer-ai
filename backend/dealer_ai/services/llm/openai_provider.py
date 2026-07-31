"""OpenAI provider — gated behind config so Ollama works without an API key."""

from __future__ import annotations

import logging
from typing import Iterable

from .base import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)

# Model families that require the reasoning-model parameter shape:
#   - max_tokens is rejected; use max_completion_tokens.
#   - temperature only accepts the default (1); any other value is a 400.
# Detected by name prefix so future variants (gpt-5.1, o4, etc.) fall into
# the same bucket automatically.
_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _is_reasoning_model(model: str) -> bool:
    m = (model or "").lower()
    return any(m.startswith(p) for p in _REASONING_PREFIXES)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, *, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider.")
        # Lazy import so ollama-only setups don't need the openai package.
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model

    def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 800,
        **kwargs,
    ) -> str:
        params = {
            "model": self.model,
            "messages": self.normalize(messages),
        }
        if _is_reasoning_model(self.model):
            # Reasoning models burn tokens on internal reasoning before
            # producing content, so a caller-specified 800 for content
            # often leaves nothing for the actual answer. Double it as
            # a floor so the visible reply has room to land.
            params["max_completion_tokens"] = max(max_tokens * 2, 1200)
        else:
            params["max_tokens"] = max_tokens
            params["temperature"] = temperature

        try:
            resp = self._client.chat.completions.create(**params)
        except Exception as exc:  # noqa: BLE001
            # Expected fallback path — keep one warning line, not a full traceback.
            logger.warning("OpenAI request failed: %s", exc)
            return (
                "I'm having trouble reaching the AI service right now. "
                "Please try again in a moment."
            )

        choice = resp.choices[0]
        return (choice.message.content or "").strip()

"""OpenAI provider — gated behind config so Ollama works without an API key."""

from __future__ import annotations

import logging
from typing import Iterable

from .base import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)


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
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=self.normalize(messages),
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            # Expected fallback path — keep one warning line, not a full traceback.
            logger.warning("OpenAI request failed: %s", exc)
            return (
                "I'm having trouble reaching the AI service right now. "
                "Please try again in a moment."
            )

        choice = resp.choices[0]
        return (choice.message.content or "").strip()

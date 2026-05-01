"""Test doubles — used so tests never hit Ollama/OpenAI."""

from __future__ import annotations

import json
from typing import Iterable, List, Optional

from dealer_ai.services.llm.base import ChatMessage, LLMProvider


class MockLLMProvider(LLMProvider):
    """Returns scripted replies in order. The last reply is reused if exhausted."""

    name = "mock"

    def __init__(self, replies: Optional[List[str]] = None):
        self.replies = list(replies or [])
        self.calls: List[List[dict]] = []

    def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 800,
        **kwargs,
    ) -> str:
        normalized = self.normalize(messages)
        self.calls.append(normalized)
        if not self.replies:
            return ""
        if len(self.calls) <= len(self.replies):
            return self.replies[len(self.calls) - 1]
        return self.replies[-1]


def json_reply(payload: dict) -> str:
    return json.dumps(payload)

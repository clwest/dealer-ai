"""Base LLM provider interface.

All providers must implement `chat(messages, **kwargs) -> str`.
Messages follow the OpenAI-style schema: [{"role": "system|user|assistant", "content": "..."}].
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Mapping


ChatMessage = Mapping[str, str]


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

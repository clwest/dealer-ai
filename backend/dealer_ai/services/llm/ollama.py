"""Ollama provider — local inference, no paid API calls.

Uses Ollama's /api/chat endpoint:
https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
"""

from __future__ import annotations

import logging
from typing import Iterable

import requests

from .base import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 800,
        **kwargs,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": self.normalize(messages),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        url = f"{self.base_url}/api/chat"
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as exc:
            # Expected fallback path — Ollama not running, model not pulled, etc.
            # Keep the log a single warning line so demos aren't drowned in tracebacks.
            logger.warning("Ollama request to %s failed: %s", url, exc)
            return (
                "I'm having trouble reaching the local AI model right now. "
                "Please make sure Ollama is running and the model is pulled, "
                "then try again."
            )

        msg = data.get("message") or {}
        content = msg.get("content") or data.get("response") or ""
        return content.strip()

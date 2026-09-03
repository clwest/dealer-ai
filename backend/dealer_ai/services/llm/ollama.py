"""Ollama provider — local inference, no paid API calls.

Uses Ollama's /api/chat endpoint:
https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
"""

from __future__ import annotations

import logging
from typing import Iterable

import requests

from .base import ChatMessage, LLMProvider, ProviderUnavailable

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
            # Ollama not running, model not pulled, network error. Callers
            # at surface boundaries decide the user-visible response;
            # returning apology prose here would look like a normal
            # reply and get scrubbed / stored as one.
            logger.warning("Ollama request to %s failed: %s", url, exc)
            raise ProviderUnavailable(
                f"Ollama request to {url} failed: {exc}"
            ) from exc

        msg = data.get("message") or {}
        content = msg.get("content") or data.get("response") or ""
        return content.strip()

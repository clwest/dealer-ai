"""LLM provider factory — returns a provider instance based on Django settings."""

from __future__ import annotations

from django.conf import settings

from .base import LLMProvider
from .ollama import OllamaProvider


def get_llm_provider() -> LLMProvider:
    provider_name = (
        getattr(settings, "DEALER_AI_LLM_PROVIDER", "ollama") or "ollama"
    ).lower()

    if provider_name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=getattr(settings, "OPENAI_API_KEY", ""),
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
        )

    # Default: Ollama (local, free).
    return OllamaProvider(
        base_url=getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
        model=getattr(settings, "OLLAMA_MODEL", "llama3.1"),
    )

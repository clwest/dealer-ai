# dealer_ai/services/llm/factory.py

from django.conf import settings
from .ollama import OllamaProvider
from .openai_provider import OpenAIProvider


def get_llm_provider():
    provider = settings.DEALER_AI_LLM_PROVIDER.lower()

    if provider == "ollama":
        return OllamaProvider()

    if provider == "openai":
        return OpenAIProvider()

    raise ValueError(f"Unsupported LLM provider: {provider}")
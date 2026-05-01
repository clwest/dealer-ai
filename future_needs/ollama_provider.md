# dealer_ai/services/llm/ollama.py

import requests
from django.conf import settings
from .base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def chat(self, messages, temperature=0.2):
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
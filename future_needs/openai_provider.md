# dealer_ai/services/llm/openai_provider.py

from django.conf import settings
from openai import OpenAI
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def chat(self, messages, temperature=0.2):
        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content
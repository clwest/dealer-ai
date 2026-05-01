# dealer_ai/services/llm/base.py

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, messages, temperature=0.2):
        pass
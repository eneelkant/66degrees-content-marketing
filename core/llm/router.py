import os
from typing import Dict, Optional, Type

from core.llm.base import BaseLLMProvider
from core.llm.mock_adapter import MockLLMProvider
from core.llm.adapters.anthropic_adapter import AnthropicAdapter
from core.llm.adapters.openai_adapter import OpenAIAdapter
from core.llm.adapters.gemini_adapter import GeminiAdapter


class LLMRouter:
    def __init__(self):
        self._providers: Dict[str, Type[BaseLLMProvider]] = {
            "mock": MockLLMProvider,
            "anthropic": AnthropicAdapter,
            "openai": OpenAIAdapter,
            "gemini": GeminiAdapter,
        }

    def get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        selected = (provider_name or os.getenv("LLM_PROVIDER", "mock")).lower().strip()
        if selected not in self._providers:
            valid = ", ".join(self._providers)
            raise ValueError(f"Unsupported LLM_PROVIDER '{selected}'. Valid options: {valid}")
        return self._providers[selected]()


llm_router = LLMRouter()

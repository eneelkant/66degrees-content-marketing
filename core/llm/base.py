from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class LLMResponse(BaseModel):
    raw_text: str
    parsed_model: Optional[Any] = None
    provider: str
    model_name: str
    tokens_used: Dict[str, int] = Field(default_factory=dict)


class LLMProviderError(RuntimeError):
    """Provider/API failure. Never silently converted to mock output."""


class LLMStructuredOutputError(LLMProviderError):
    """Provider returned output that could not satisfy the requested schema."""


class BaseLLMProvider(ABC):
    provider_name: str
    model_name: str = "unknown"

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> T:
        raise NotImplementedError

    @staticmethod
    def _parse_json_model(raw_text: str, response_model: Type[T]) -> T:
        import json

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LLMStructuredOutputError(
                f"Provider returned invalid JSON: {exc}"
            ) from exc
        try:
            return response_model.model_validate(payload)
        except Exception as exc:
            raise LLMStructuredOutputError(
                f"Provider output failed {response_model.__name__} validation: {exc}"
            ) from exc

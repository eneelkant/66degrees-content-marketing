import os
from typing import Type, TypeVar

from pydantic import BaseModel

from core.llm.base import BaseLLMProvider, LLMResponse, LLMProviderError

T = TypeVar("T", bound=BaseModel)


class OpenAIAdapter(BaseLLMProvider):
    provider_name = "openai"

    def __init__(self, model_name: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMProviderError(
                "OpenAI provider requires the optional 'openai' package."
            ) from exc
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-5.1")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_text(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> LLMResponse:
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=system_prompt or None,
                input=prompt,
                temperature=temperature,
            )
            text = getattr(response, "output_text", "")
            usage_obj = getattr(response, "usage", None)
            tokens = {}
            if usage_obj:
                for source, target in (("input_tokens", "input"), ("output_tokens", "output")):
                    value = getattr(usage_obj, source, None)
                    if value is not None:
                        tokens[target] = value
            return LLMResponse(raw_text=text, provider=self.provider_name, model_name=self.model_name, tokens_used=tokens)
        except Exception as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc

    def generate_structured(self, prompt: str, response_model: Type[T], system_prompt: str = "", temperature: float = 0.2) -> T:
        try:
            response = self.client.responses.parse(
                model=self.model_name,
                instructions=system_prompt or None,
                input=prompt,
                text_format=response_model,
                temperature=temperature,
            )
            parsed = getattr(response, "output_parsed", None)
            if parsed is None:
                raise LLMProviderError("OpenAI returned no parsed structured output.")
            return parsed if isinstance(parsed, response_model) else response_model.model_validate(parsed)
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(f"OpenAI structured request failed: {exc}") from exc

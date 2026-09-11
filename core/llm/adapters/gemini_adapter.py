import os
from typing import Type, TypeVar

from pydantic import BaseModel

from core.llm.base import BaseLLMProvider, LLMResponse, LLMProviderError

T = TypeVar("T", bound=BaseModel)


class GeminiAdapter(BaseLLMProvider):
    provider_name = "gemini"

    def __init__(self, model_name: str | None = None):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMProviderError(
                "Gemini provider requires the optional 'google-genai' package."
            ) from exc
        self._types = types
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def generate_text(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> LLMResponse:
        try:
            config = self._types.GenerateContentConfig(
                system_instruction=system_prompt or None,
                temperature=temperature,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            usage = getattr(response, "usage_metadata", None)
            tokens = {}
            if usage:
                for source, target in (("prompt_token_count", "input"), ("candidates_token_count", "output")):
                    value = getattr(usage, source, None)
                    if value is not None:
                        tokens[target] = value
            return LLMResponse(raw_text=response.text or "", provider=self.provider_name, model_name=self.model_name, tokens_used=tokens)
        except Exception as exc:
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc

    def generate_structured(self, prompt: str, response_model: Type[T], system_prompt: str = "", temperature: float = 0.2) -> T:
        try:
            config = self._types.GenerateContentConfig(
                system_instruction=system_prompt or None,
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=response_model,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            parsed = getattr(response, "parsed", None)
            if parsed is not None:
                return parsed if isinstance(parsed, response_model) else response_model.model_validate(parsed)
            return response_model.model_validate_json(response.text)
        except Exception as exc:
            raise LLMProviderError(f"Gemini structured request failed: {exc}") from exc

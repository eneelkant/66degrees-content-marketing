import json
import os
from typing import Type, TypeVar

from pydantic import BaseModel

from core.llm.base import BaseLLMProvider, LLMResponse, LLMProviderError

T = TypeVar("T", bound=BaseModel)


class AnthropicAdapter(BaseLLMProvider):
    provider_name = "anthropic"

    def __init__(self, model_name: str | None = None):
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise LLMProviderError(
                "Anthropic provider requires the optional 'anthropic' package."
            ) from exc
        self.model_name = model_name or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def generate_text(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> LLMResponse:
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt or None,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(getattr(block, "text", "") for block in response.content)
            usage = getattr(response, "usage", None)
            tokens = {}
            if usage:
                if getattr(usage, "input_tokens", None) is not None:
                    tokens["input"] = usage.input_tokens
                if getattr(usage, "output_tokens", None) is not None:
                    tokens["output"] = usage.output_tokens
            return LLMResponse(raw_text=text, provider=self.provider_name, model_name=self.model_name, tokens_used=tokens)
        except Exception as exc:
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc

    def generate_structured(self, prompt: str, response_model: Type[T], system_prompt: str = "", temperature: float = 0.2) -> T:
        schema = response_model.model_json_schema()
        tool = {
            "name": "emit_structured_output",
            "description": f"Return data matching {response_model.__name__}.",
            "input_schema": schema,
        }
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt or None,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    return response_model.model_validate(block.input)
            raise LLMProviderError("Anthropic returned no structured tool result.")
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(f"Anthropic structured request failed: {exc}") from exc

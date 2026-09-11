import json
from typing import Type, TypeVar

from pydantic import BaseModel

from core.llm.base import BaseLLMProvider, LLMResponse, LLMStructuredOutputError

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(BaseLLMProvider):
    provider_name = "mock"
    model_name = "mock-v1"

    def generate_text(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> LLMResponse:
        text = "[Mock Output] 66degrees Google Cloud Premier Partner solution."
        return LLMResponse(raw_text=text, provider=self.provider_name, model_name=self.model_name)

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> T:
        factory = getattr(response_model, "mock_default", None)
        if callable(factory):
            value = factory()
            return value if isinstance(value, response_model) else response_model.model_validate(value)

        # Avoid model_construct(): it bypasses required-field validation and would
        # make the mock falsely appear schema-compliant.
        fields = response_model.model_fields
        payload = {}
        for name, field in fields.items():
            if field.default is not None and not field.is_required():
                payload[name] = field.default
            elif field.default_factory is not None:  # type: ignore[attr-defined]
                payload[name] = field.default_factory()  # type: ignore[misc]
            else:
                raise LLMStructuredOutputError(
                    f"Mock provider has no deterministic fixture for required field '{name}' "
                    f"in {response_model.__name__}. Add mock_default()."
                )
        try:
            return response_model.model_validate(payload)
        except Exception as exc:
            raise LLMStructuredOutputError(
                f"Mock fixture failed {response_model.__name__} validation: {exc}"
            ) from exc

import json

import pytest
from pydantic import BaseModel, Field

from core.llm.base import LLMStructuredOutputError
from core.llm.router import LLMRouter
from core.llm.mock_adapter import MockLLMProvider


class ExampleOutput(BaseModel):
    title: str = Field(min_length=1)
    items: list[str] = Field(min_length=2, max_length=2)

    @classmethod
    def mock_default(cls):
        return cls(title="Mock Event", items=["One", "Two"])


class RequiredWithoutFixture(BaseModel):
    title: str


def test_router_resolves_all_providers_without_instantiating_optional_sdks():
    router = LLMRouter()
    assert set(router._providers) == {"mock", "anthropic", "openai", "gemini"}
    assert isinstance(router.get_provider("mock"), MockLLMProvider)


def test_router_default_is_mock(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(LLMRouter().get_provider(), MockLLMProvider)


def test_router_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        LLMRouter().get_provider("not-a-provider")


def test_mock_structured_output_is_pydantic_validated():
    result = MockLLMProvider().generate_structured("ignored", ExampleOutput)
    assert isinstance(result, ExampleOutput)
    assert result.items == ["One", "Two"]


def test_mock_fails_instead_of_bypassing_required_schema():
    with pytest.raises(LLMStructuredOutputError, match="no deterministic fixture"):
        MockLLMProvider().generate_structured("ignored", RequiredWithoutFixture)


def test_base_json_parser_enforces_pydantic_constraints():
    raw = json.dumps({"title": "", "items": ["only-one"]})
    with pytest.raises(LLMStructuredOutputError, match="validation"):
        MockLLMProvider._parse_json_model(raw, ExampleOutput)

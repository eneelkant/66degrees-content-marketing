"""LLM configuration error messages must be actionable without leaking secrets."""
import pytest

from core.llm.base import LLMProviderError
from core.llm.router import llm_router


@pytest.mark.parametrize(
    ("provider", "needle"),
    [
        ("anthropic", "anthropic"),
        ("openai", "openai"),
        ("gemini", "gemini"),
    ],
)
def test_live_provider_errors_are_actionable_without_credentials(provider, needle, monkeypatch):
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(LLMProviderError) as excinfo:
        llm_router.get_provider(provider)
    message = str(excinfo.value).lower()
    assert needle in message
    # Must tell the operator what to install or which env var to set — never a bare traceback class name only.
    assert ("api" in message and "key" in message) or "optional" in message or "requires" in message


def test_mock_provider_always_available(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    provider = llm_router.get_provider("mock")
    assert provider.provider_name == "mock"

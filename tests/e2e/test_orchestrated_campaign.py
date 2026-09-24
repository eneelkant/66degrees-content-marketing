"""Autonomous mocked campaign orchestration E2E + failure recovery."""
from pathlib import Path

import pytest

from clients import public_api as api
from core.campaign.models import CampaignStatus
from core.campaign.orchestrator import CampaignOrchestrator
from core.campaign.store import CampaignStore
from core.llm.base import LLMProviderError


BRIEF = {
    "campaign_name": "66degrees Agentic AI Webinar",
    "campaign_type": "webinar",
    "audience": "Enterprise technology leaders",
    "objective": "Generate webinar promotion assets for Agentic AI",
    "offer": "Register for the webinar",
    "key_messages": [
        "Practical agentic architecture",
        "Governance for enterprise AI",
    ],
    "channels": ["email", "linkedin", "landing_page"],
    "deadline": "2026-11-15",
}


@pytest.fixture
def orch(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    store = CampaignStore(tmp_path / "campaigns")
    return CampaignOrchestrator(store=store, api=api)


def test_create_campaign_stops_at_approval_and_blocks_export(orch, tmp_path):
    result = orch.create_campaign(BRIEF)
    campaign_id = result["campaign_id"]
    assert campaign_id
    assert result["status"] == CampaignStatus.APPROVAL_PENDING.value
    assert result["approval_status"] == "pending"
    assert result["export_status"] == "blocked"
    assert result["kit_id"]
    assert result["qa_status"] in {"PASS", "WARNING", "REWRITE"}
    assert "landing_page" in result["generated_assets"]["assets"] or result["generated_assets"]["assets"]
    assert result["generated_assets"]["social_count"] >= 1

    # Persisted state is resumable
    status = orch.get_status(campaign_id)
    assert status["status"] == CampaignStatus.APPROVAL_PENDING.value
    assert Path(tmp_path / "campaigns" / f"{campaign_id}.json").exists()

    # Export blocked before approval (kit-level gate)
    with pytest.raises(PermissionError):
        api.export_campaign_kit(result["kit_id"], "json")

    resume = orch.resume_campaign(campaign_id)
    assert resume["status"] == CampaignStatus.APPROVAL_PENDING.value
    assert "approval" in resume["message"].lower()

    approved = orch.mark_approved(campaign_id)
    assert approved["status"] == CampaignStatus.APPROVED.value

    # Point the public API singleton at this test store for campaign-level export.
    import core.campaign.orchestrator as mod

    mod._orchestrator = orch
    exported = api.export_campaign(campaign_id, "json")
    assert exported["approved"] is True
    assert Path(exported["path"]).exists()
    Path(exported["path"]).unlink(missing_ok=True)

    final = orch.get_status(campaign_id)
    assert final["status"] == CampaignStatus.EXPORTED.value


def test_public_api_create_campaign_wrapper(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from config.settings import get_settings
    import core.campaign.orchestrator as mod

    get_settings.cache_clear()
    mod._orchestrator = None
    result = api.create_campaign(BRIEF)
    assert result["status"] == "APPROVAL_PENDING"
    assert result["campaign_id"].startswith("camp_")


def test_invalid_brief_is_actionable(orch):
    with pytest.raises(ValueError, match="campaign_name"):
        orch.create_campaign({"objective": "only objective"})


def test_qa_failed_cannot_approve(orch):
    result = orch.create_campaign(BRIEF)
    state = orch.store.load(result["campaign_id"])
    state.status = CampaignStatus.QA_FAILED
    orch.store.save(state)
    with pytest.raises(PermissionError, match="QA_FAILED"):
        orch.mark_approved(result["campaign_id"])


def test_missing_optional_llm_config_does_not_break_mock_campaign(orch, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    result = orch.create_campaign(BRIEF)
    assert result["status"] == "APPROVAL_PENDING"


def test_live_provider_unavailable_is_actionable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from core.llm.router import llm_router

    with pytest.raises(LLMProviderError):
        llm_router.get_provider("openai")


def test_invalid_tool_input_platforms(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    with pytest.raises(ValueError, match="platforms"):
        api.generate_social_posts({"title": "x"}, [])

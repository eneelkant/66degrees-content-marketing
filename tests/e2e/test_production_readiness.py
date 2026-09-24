"""Phase 3 production readiness: resume, QA revision, idempotency, MCP contracts."""
from __future__ import annotations

import asyncio
import uuid

import pytest

from clients import public_api as api
from clients.claude.server import mcp
from clients.surface import PUBLIC_TOOL_NAMES
from core.brand.rules import load_brand_rules
from core.campaign.brief import validate_marketing_brief
from core.campaign.models import STAGE_ORDER, CampaignStage, CampaignState, CampaignStatus, StageRecord
from core.campaign.orchestrator import CampaignOrchestrator
from core.campaign.store import CampaignStore
from core.llm.base import LLMStructuredOutputError, LLMTimeoutError, LLMUnavailableError


BRIEF = {
    "campaign_name": "66degrees Agentic AI Enterprise Webinar",
    "campaign_type": "webinar",
    "audience": "Enterprise technology leaders",
    "objective": "Generate webinar promotion assets for Agentic AI",
    "offer": "Register for the webinar",
    "key_messages": ["Practical agentic architecture", "Governance for enterprise AI"],
    "channels": ["email", "linkedin", "landing_page"],
    "deadline": "2026-11-20",
}


@pytest.fixture
def orch(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return CampaignOrchestrator(store=CampaignStore(tmp_path / "campaigns"), api=api)


def test_interrupt_and_resume_preserves_campaign_id(orch):
    brief = validate_marketing_brief(BRIEF)
    campaign_id = f"camp_{uuid.uuid4().hex[:12]}"
    state = CampaignState(
        campaign_id=campaign_id,
        status=CampaignStatus.DRAFT,
        brief=brief.model_dump(mode="json"),
        stages={s.value: StageRecord(stage=s) for s in STAGE_ORDER},
        provider="mock",
    )
    orch.store.save(state)

    stopped = orch.run_until_approval(campaign_id, stop_after=CampaignStage.CONTENT)
    assert stopped["campaign_id"] == campaign_id
    assert "content" in stopped["completed_stages"]
    assert "social" not in stopped["completed_stages"]
    assert stopped["status"] == CampaignStatus.GENERATED.value

    resumed = orch.resume_campaign(campaign_id)
    assert resumed["campaign_id"] == campaign_id
    assert resumed["status"] == CampaignStatus.APPROVAL_PENDING.value
    assert "social" in resumed["completed_stages"]
    assert resumed["export_status"] == "blocked"


def test_idempotent_create_and_approve_export(orch, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    key = "webinar-agentic-ai-enterprise-2026"
    first = orch.create_campaign({**BRIEF, "idempotency_key": key})
    second = orch.create_campaign({**BRIEF, "idempotency_key": key})
    assert first["campaign_id"] == second["campaign_id"]
    assert second.get("idempotent") is True

    approved = orch.mark_approved(first["campaign_id"])
    approved_again = orch.mark_approved(first["campaign_id"])
    assert approved["status"] == CampaignStatus.APPROVED.value
    assert approved_again.get("idempotent") is True

    import core.campaign.orchestrator as mod

    mod._orchestrator = orch
    exported = api.export_campaign(first["campaign_id"], "json")
    exported_again = api.export_campaign(first["campaign_id"], "json")
    assert exported.get("approved") is True or exported.get("status") == "EXPORTED"
    assert exported_again.get("idempotent") is True or exported_again.get("status") == "EXPORTED"


def test_qa_revision_loop_blocks_export_until_fixed(orch):
    result = orch.create_campaign(BRIEF)
    campaign_id = result["campaign_id"]
    state = orch.store.load(campaign_id)
    kit_id = state.kit_id

    landing = dict(state.assets.get("landing_page") or {})
    landing["body"] = "This is a game-changing synergy with guaranteed ROI and TBD metrics."
    state.assets["landing_page"] = landing
    state.status = CampaignStatus.GENERATED
    orch._reset_stages_from(state, CampaignStage.QA)
    orch.store.save(state)

    revised_run = orch.run_until_approval(campaign_id)
    assert revised_run["status"] in {
        CampaignStatus.REVISION_REQUIRED.value,
        CampaignStatus.QA_FAILED.value,
    }
    with pytest.raises(PermissionError):
        orch.mark_approved(campaign_id)
    with pytest.raises(PermissionError):
        api.export_campaign_kit(kit_id, "json")

    state = orch.store.load(campaign_id)
    state.assets["landing_page"] = {
        "hero": {"title": "Agentic AI for the enterprise", "hook": "Practical outcomes"},
        "body": "66degrees helps enterprises adopt Generative AI with governance.",
    }
    orch.store.save(state)
    resumed = orch.resume_campaign(campaign_id)
    assert resumed["status"] == CampaignStatus.APPROVAL_PENDING.value

    orch.mark_approved(campaign_id)
    import core.campaign.orchestrator as mod

    mod._orchestrator = orch
    exported = api.export_campaign(campaign_id, "json")
    assert exported.get("approved") is True or exported.get("status") == "EXPORTED"


def test_brand_detects_placeholders_and_unsupported_claims():
    rules = load_brand_rules()
    result = rules.validate_text("Insert TBD results with guaranteed ROI and lorem ipsum.")
    assert result["valid"] is False
    assert result["placeholders"]
    assert result["unsupported_claims"]


def test_mcp_contracts_all_sixteen_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == set(PUBLIC_TOOL_NAMES)
    assert len(names) == 16
    for tool in tools:
        schema = tool.inputSchema
        assert schema.get("type") == "object"
        assert "properties" in schema


def test_mcp_invalid_inputs_are_actionable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    with pytest.raises(ValueError, match="campaign_name|Invalid campaign brief"):
        api.create_campaign({"objective": "missing name"})
    with pytest.raises(ValueError, match="platforms"):
        api.generate_social_posts({"title": "x"}, [])
    with pytest.raises(FileNotFoundError, match="Unknown campaign_id"):
        api.get_campaign_status("camp_does_not_exist")


def test_llm_error_classes_are_actionable():
    assert "timed out" in str(LLMTimeoutError()).lower()
    assert "unavailable" in str(LLMUnavailableError()).lower()
    assert "Invalid structured response" in str(LLMStructuredOutputError("bad json"))


def test_lifecycle_labels_and_metadata(orch):
    result = orch.create_campaign(BRIEF)
    state = orch.store.load(result["campaign_id"])
    assert state.lifecycle_label() in {"APPROVAL_PENDING", "CONTENT_READY", "STRATEGY_READY"}
    landing = state.assets["landing_page"]
    assert landing["metadata"]["campaign_id"] == result["campaign_id"]
    assert landing["metadata"]["content_type"] == "landing_page"

import os
from pathlib import Path
import pytest

from core.approval.gate import HumanApprovalGate
from core.llm.base import LLMProviderError
from core.llm.router import llm_router
from core.optimization.optimizer import optimize_content_asset
from core.optimization.repurposer import repurpose_content_asset
from exporters.campaign import export_approved_campaign


def test_optimizer_mock_is_schema_valid_and_returns_asset():
    os.environ["LLM_PROVIDER"] = "mock"
    result = optimize_content_asset(
        {"asset_type": "blog", "title": "Draft", "content_markdown": "synergy"},
        {"state": "REWRITE", "violations": ["forbidden jargon: synergy"]},
    )
    assert result["status"] == "OPTIMIZED"
    assert result["asset"]["content_markdown"]
    assert result["changes"]


def test_repurposer_supports_multiple_target_formats():
    os.environ["LLM_PROVIDER"] = "mock"
    result = repurpose_content_asset(
        {"asset_type": "blog", "title": "AI", "content_markdown": "Useful insight."},
        "linkedin_post",
    )
    assert result["status"] == "REPURPOSED"
    assert result["asset"]["asset_type"] == "linkedin_post"


def test_live_provider_errors_are_not_converted_to_mock(monkeypatch):
    class FailingProvider:
        provider_name = "openai"
        model_name = "test"
        def generate_structured(self, *args, **kwargs):
            raise LLMProviderError("API failure")
    monkeypatch.setattr(llm_router, "get_provider", lambda provider=None: FailingProvider())
    with pytest.raises(LLMProviderError, match="API failure"):
        optimize_content_asset({"asset_type": "blog", "content_markdown": "x"}, {"state": "REWRITE"}, provider="openai")


def test_export_is_blocked_without_approval(tmp_path):
    gate = HumanApprovalGate()
    with pytest.raises(PermissionError):
        export_approved_campaign("kit-10", {"title": "Kit"}, "json", gate, tmp_path)


def test_approved_export_supports_json_docx_xlsx(tmp_path):
    gate = HumanApprovalGate()
    gate.approve("kit-10-json", "Human Approver")
    gate.approve("kit-10-docx", "Human Approver")
    gate.approve("kit-10-xlsx", "Human Approver")
    kit = {"title": "Approved Kit", "assets": [{"type": "blog"}]}
    for fmt in ("json", "docx", "xlsx"):
        result = export_approved_campaign("kit-10-" + fmt, kit, fmt, gate, tmp_path)
        assert result["approved"] is True
        assert Path(result["path"]).exists()

"""Regression tests for 66degrees writing-guidelines knowledge base and skills."""
from __future__ import annotations

from pathlib import Path

from core.generators.context_builder import build_generation_context
from core.mcp_legacy import tools as mcp_tools
from core.optimization.prompts import build_optimization_prompt
from core.qa.engine import qa_validate_asset
from core.qa.models import QAState
from core.writing.compliance import evaluate_compliance, preserve_facts_on_rewrite
from core.writing.loader import (
    GUIDELINE_FILES,
    expected_source_archive_files,
    get_guideline_version,
    knowledge_root,
    load_guidelines,
)
from core.writing.prompt import build_writing_prompt
from core.writing.skills import SKILL_IDS, select_skills
from clients.surface import PUBLIC_TOOL_NAMES


ROOT = Path(__file__).resolve().parents[1]


def test_source_manifest_accounts_for_all_archive_files():
    manifest = (knowledge_root() / "source_manifest.md").read_text(encoding="utf-8")
    for name in expected_source_archive_files():
        assert name in manifest, f"Archive file not accounted for: {name}"
    assert "14" in manifest or "十四" in manifest or "Archive files" in manifest


def test_guideline_files_exist_and_load():
    loaded = load_guidelines()
    assert loaded, "writing guidelines failed to load"
    for doc_id, filename in GUIDELINE_FILES.items():
        assert doc_id in loaded
        assert (knowledge_root() / "writing_guidelines" / filename).is_file()
    assert get_guideline_version() == "2026.10.26"
    conflicts = (knowledge_root() / "conflicts_and_exceptions.md").read_text(encoding="utf-8")
    assert "Diamond" in conflicts
    assert "Premier" in conflicts


def test_no_secrets_in_knowledge_base():
    text = ""
    for path in knowledge_root().rglob("*"):
        if path.is_file() and path.suffix in {".md", ".txt", ""}:
            text += path.read_text(encoding="utf-8", errors="ignore")
    lowered = text.lower()
    for needle in ("api_key=", "begin private key", "sk-proj-", "xoxb-", "password="):
        assert needle not in lowered


def test_skill_selection_includes_channel_and_ceo_when_relevant():
    email_skills = select_skills("email", mode="generate")
    assert "channel_adaptation" in email_skills
    assert "content_generation" in email_skills
    assert "brand_voice" in email_skills
    ceo_skills = select_skills(
        "thought_leadership",
        brief_data={"metadata": {"voice": "CEO press release for Ben Kessler"}},
        mode="generate",
    )
    assert "ceo_voice" in ceo_skills
    assert set(SKILL_IDS) >= set(email_skills)


def test_prompt_subset_not_entire_knowledge_base():
    prompt = build_writing_prompt("blog", brief_data={"audience": {"primary_persona": "CIO"}}, mode="generate")
    assert prompt["available"] is True
    assert "company_facts" in prompt["doc_ids"]
    # Craft may be omitted under budget; total prompt must stay bounded.
    assert len(prompt["prompt_block"]) < 12000
    assert "Diamond" in prompt["prompt_block"] or "company_facts" in prompt["doc_ids"]


def test_compliant_sample_passes():
    content = {
        "title": "Production AI for insurance leaders",
        "body": (
            "On the path to an AI-native operating model, teams that already run "
            "disciplined estates get measurable ROI with a Google Cloud Diamond Partner "
            "working alongside their architects. Register to compare notes."
        ),
        "cta": "Register now",
    }
    # Avoid banned "journey"; keep hyphen only in AI-native.
    content["body"] = (
        "Leaders who already run disciplined estates get measurable ROI when "
        "forward deployed engineers work alongside their architects as a "
        "Google Cloud Diamond Partner engagement. Register to compare notes."
    )
    result = evaluate_compliance(content, "blog", brief_data=content, mode="qa")
    assert result.status == "pass"
    assert result.hard_failures == []


def test_mandatory_rule_violation_fails():
    content = {
        "body": "As a Google Cloud Premier Partner we unlock seamless AI journeys on AWS and Azure."
    }
    result = evaluate_compliance(content, "blog", mode="qa")
    assert result.status == "needs_revision"
    rules = {f.rule for f in result.hard_failures}
    assert "banned_phrase" in rules or "banned_term" in rules
    assert any("premier" in f.message.lower() or "unlock" in f.message.lower() for f in result.hard_failures)
    assert any("aws" in f.message.lower() or "azure" in f.message.lower() for f in result.hard_failures)


def test_style_warning_without_hard_failure():
    content = {
        "body": (
            "Last time we told you about adoption. Across every layer of the AI stack, "
            "leaders still need clarity."
        )
    }
    result = evaluate_compliance(content, "blog", mode="qa")
    assert result.status == "pass"
    assert result.hard_failures == []
    assert result.warnings
    assert any(w.rule in {"recap_bridge", "mechanical_style"} for w in result.warnings)


def test_unsupported_numerical_claim_fails():
    content = {"body": "Our platform delivers 99.97% uptime for every regulated insurer."}
    result = evaluate_compliance(
        content,
        "blog",
        brief_data={"metadata": {"title": "Uptime story"}},
        mode="qa",
    )
    assert result.status == "needs_revision"
    assert any(f.rule == "unsupported_numerical_claim" for f in result.hard_failures)


def test_incorrect_product_terminology_fails():
    content = {"body": "Deploy PRISM to modernize legacy estates with agentic workflows."}
    result = evaluate_compliance(content, "website", mode="qa")
    assert result.status == "needs_revision"
    assert any(f.rule == "legacy_name" for f in result.hard_failures)


def test_channel_specific_email_subject_limit():
    content = {
        "subject": "You are invited to an exclusive executive dinner in Chicago downtown",
        "title": "An evening with peers",
        "body": "On May 12, we are hosting a working dinner, and we would like you there.",
    }
    result = evaluate_compliance(content, "email", mode="qa")
    assert result.status == "needs_revision"
    assert any(f.rule == "email_subject_length" for f in result.hard_failures)


def test_rewrite_preserves_facts():
    original = "Wood Mackenzie cut forecast time from 35 minutes to under 10 seconds."
    rewritten = "Wood Mackenzie cut forecast time from 35 minutes to under 10 seconds and added 42% magic uplift."
    findings = preserve_facts_on_rewrite(original, rewritten, brief_data={"body": original})
    assert findings
    assert any(f.rule == "rewrite_invented_number" for f in findings)


def test_ambiguous_social_limits_warn_not_crash():
    result = evaluate_compliance(
        {"body": "See you at the dinner."},
        "linkedin_post",
        brief_data={},
        mode="qa",
    )
    assert result.status == "pass"
    assert any(w.rule == "social_limits_unknown" for w in result.warnings)


def test_generate_content_asset_applies_guidelines(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    brief = {
        "metadata": {"title": "AI-native advantage for CIOs"},
        "audience": {"primary_persona": "CIO", "industry_verticals": ["Healthcare"]},
        "value_prop": {"primary_hook": "Move AI into production workflows", "key_takeaways": ["Governed delivery"]},
        "cta_primary": "Talk with us",
    }
    result = mcp_tools.generate_content_asset("blog", brief)
    assert result["qa_status"] == "GENERATED_DRAFT"
    assert result["guideline_version"] == "2026.10.26"
    assert "brand_voice" in result["applicable_skills"]
    assert result["writing_compliance"]["guideline_version"] == "2026.10.26"
    assert result["asset"]["metadata"]["writing_compliance"]["status"] in {
        "pass",
        "needs_revision",
    }
    body = result["asset"]["content_markdown"]
    assert "2026.10.26" not in body
    assert result["asset"]["metadata"]["guideline_version"] == "2026.10.26"
    # Guideline version must not false-trigger unsupported_numerical_claim.
    hard_rules = {f["rule"] for f in result["writing_compliance"]["hard_failures"]}
    assert "unsupported_numerical_claim" not in hard_rules
    assert result["writing_compliance"]["status"] == "pass"


def test_guideline_version_string_is_not_a_numerical_claim():
    """Regression: dotted VERSION metadata must not hard-fail claim scanning."""
    content = {
        "body": (
            "Leaders who already run disciplined estates get measurable ROI when "
            "forward deployed engineers work alongside their architects as a "
            "Google Cloud Diamond Partner engagement. "
            "Guideline version 2026.10.26 is recorded in metadata."
        )
    }
    result = evaluate_compliance(content, "blog", brief_data=content, mode="qa")
    assert result.status == "pass"
    assert not any(f.rule == "unsupported_numerical_claim" for f in result.hard_failures)


def test_optimize_prompt_includes_same_guideline_source():
    context = build_generation_context(
        {"metadata": {"title": "Optimize me"}, "value_prop": {"primary_hook": "Clarity"}},
        content_type="blog",
        writing_mode="optimize",
    )
    system, _user = build_optimization_prompt(
        {"asset_type": "blog", "title": "t", "content_markdown": "body"},
        {"findings": []},
        context=context,
    )
    assert "WRITING GUIDELINES" in system
    assert context.guideline_version == "2026.10.26"
    assert "content_optimization" in context.applicable_skills or "brand_voice" in context.applicable_skills


def test_qa_writing_guidelines_check_not_silent_pass_on_hard_failure():
    report = qa_validate_asset(
        {"content": "We unlock seamless journeys on Azure as a Premier Partner."},
        "blog",
        references=[],
    )
    writing = next(c for c in report.checks if c.name == "writing_guidelines")
    assert writing.state == QAState.REWRITE
    assert report.overall_status == QAState.REWRITE
    assert writing.details["status"] == "needs_revision"
    assert writing.details["hard_failures"]


def test_qa_still_requires_human_approval():
    report = qa_validate_asset(
        {"content": "Leaders get clarity with governed delivery on Google Cloud."},
        "blog",
        references=[],
    )
    assert report.approval_required is True
    assert report.approval_status == "LOCKED"


def test_public_tool_count_unchanged():
    assert len(PUBLIC_TOOL_NAMES) == 16


def test_context_builder_injects_writing_guidelines(tmp_path):
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from core.brand.rules import load_brand_rules
    from core.reference_library.models import ReferenceRecord
    from core.reference_library.sqlite_client import SQLiteReferenceClient

    db = SQLiteReferenceClient(tmp_path / "references.db")
    db.upsert(
        ReferenceRecord(
            id="w1",
            title="Winner",
            content="Governed AI delivery",
            source="66degrees",
            source_type="internal",
            industry="Healthcare",
            performance_score=0.9,
            fetched_at=datetime.now(timezone.utc),
        )
    )

    class DBRetriever:
        def retrieve(self, query, *, industry=None, channel=None, top_k=3):
            return [SimpleNamespace(record=r, score=0.9) for r in db.search(industry=industry, limit=3)]

        @staticmethod
        def competitor_context(records):
            return ""

    context = build_generation_context(
        {
            "metadata": {"title": "Healthcare AI"},
            "audience": {"primary_persona": "CIO", "industry_verticals": ["Healthcare"]},
            "value_prop": {"primary_hook": "Production AI"},
        },
        brand_engine=load_brand_rules(),
        hybrid_retriever=DBRetriever(),
        content_type="blog",
    )
    assert context.guideline_version == "2026.10.26"
    assert context.writing_prompt_block
    assert "brand_voice" in context.applicable_skills
    assert context.content_context["writing_guidelines"]["available"] is True

"""End-to-end mocked campaign workflow: brief → strategy → create → social → QA → optimize → approve → export."""
from pathlib import Path

from clients import public_api as api
from core.brand.rules import load_brand_rules

BRIEF = {
    "metadata": {"title": "Build AI Systems Enterprises Trust", "date": "2026-10-15"},
    "audience": {"primary_persona": "CIO", "industry_verticals": ["Financial Services"]},
    "value_prop": {
        "primary_hook": "Move enterprise AI from pilot to measurable impact",
        "key_takeaways": ["Practical architecture", "Governance"],
    },
    "cta_primary": "Register",
}


def test_full_campaign_journey(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    # 1) Event / brief intake
    brief_result = api.process_event_brief(BRIEF)
    assert brief_result["status"] == "READY_FOR_GENERATION"

    # 2) Strategy
    strategy = api.generate_content_strategy(
        {"objective": BRIEF["value_prop"]["primary_hook"], "audience": BRIEF["audience"]}
    )
    assert strategy["status"] == "READY"
    assert strategy["strategy"]["content_pillars"]

    # 3) Content creation (campaign kit)
    kit_result = api.generate_campaign_kit(BRIEF)
    assert kit_result["qa_status"] == "DRAFT_PENDING_QA"
    kit_id = kit_result["kit_id"]
    kit = kit_result["campaign_kit"]
    assert {"landing_page", "google_ads", "linkedin_ads", "email_campaign"} <= set(kit)

    # 4) Social / repurposing
    social = api.generate_social_posts(kit["landing_page"], ["linkedin"])
    assert social["status"] == "GENERATED"
    assert social["assets"]
    repurposed = api.repurpose_content_asset(kit["landing_page"], ["linkedin_post"])
    assert repurposed["status"] == "REPURPOSED"

    # 5) Brand governance service (reusable, not prompt-only)
    brand = load_brand_rules()
    sample = "We deliver AI and cloud outcomes as a trusted partner."
    brand_result = brand.validate_text(sample)
    assert "valid" in brand_result

    # 6) QA gate
    qa = api.qa_validate_asset(kit["landing_page"], "landing_page")
    assert qa["approval_required"] is True
    assert qa["overall_status"] in {"PASS", "WARNING", "REWRITE"}

    # 7) Optimization loop when QA is not a clean PASS (always safe to call)
    optimized = api.optimize_content_asset(
        kit["landing_page"],
        {"state": qa["overall_status"], "violations": ["Improve clarity"]},
    )
    assert optimized["status"] == "OPTIMIZED"

    # 8) Human approval remains a real gate — export blocked first
    try:
        api.export_campaign_kit(kit_id, "json")
        raise AssertionError("export must require human approval")
    except PermissionError:
        pass

    # 9) Approve then export
    approval = api.approve_campaign_kit(kit_id)
    assert approval["approved"] is True
    exported = api.export_campaign_kit(kit_id, "json")
    assert exported["approved"] is True
    path = Path(exported["path"])
    assert path.exists()
    path.unlink(missing_ok=True)

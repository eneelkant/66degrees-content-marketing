from pathlib import Path
from clients import public_api as api
BRIEF={"metadata":{"title":"Build AI Systems Enterprises Trust","date":"2026-10-15"},"audience":{"primary_persona":"CIO","industry_verticals":["Financial Services"]},"value_prop":{"primary_hook":"Move enterprise AI from pilot to measurable impact","key_takeaways":["Practical architecture","Governance"]},"cta_primary":"Register"}
def test_full_campaign_journey(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER","mock")
    assert api.process_event_brief(BRIEF)["status"]=="READY_FOR_GENERATION"
    kit_result=api.generate_campaign_kit(BRIEF); assert kit_result["qa_status"]=="DRAFT_PENDING_QA"; kit_id=kit_result["kit_id"]; kit=kit_result["campaign_kit"]
    assert {"landing_page","google_ads","linkedin_ads","email_campaign"} <= set(kit)
    qa=api.qa_validate_asset(kit["landing_page"],"landing_page"); assert qa["approval_required"]
    assert api.optimize_content_asset(kit["landing_page"],{"state":"WARNING","violations":["Improve clarity"]})["status"]=="OPTIMIZED"
    try: api.export_campaign_kit(kit_id,"json"); assert False
    except PermissionError: pass
    assert api.approve_campaign_kit(kit_id)["approved"]
    exported=api.export_campaign_kit(kit_id,"json"); assert Path(exported["path"]).exists(); Path(exported["path"]).unlink(missing_ok=True)

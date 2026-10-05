"""Content quality plus explicit Slack and Drive retrieval."""

from core.approval.gate import HumanApprovalGate
from core.generators.campaign_kit import CampaignKitOrchestrator
from core.generators.email_sequence import generate_event_email_sequence
from core.mcp_legacy.tools import generate_content_asset
from core.okf.event_email import EVENT_EMAIL_STAGE_KEYS
from core.quality.pipeline import validate_content_quality
from core.sources.drive_source import retrieve_drive, update_drive_document
from core.sources.retrieve import retrieve_requested_sources
from core.sources.slack_source import retrieve_slack
from exporters.campaign import export_approved_campaign
from clients.surface import PUBLIC_TOOL_NAMES

BRIEF = {
    "metadata": {"title": "Agentic AI for Healthcare"},
    "audience": {"primary_persona": "CIO", "industry_verticals": ["Healthcare"]},
    "value_prop": {
        "primary_hook": "Move AI into measurable healthcare workflows",
        "key_takeaways": ["Secure architecture"],
    },
    "cta_primary": "Register",
}


def test_quality_flags_brand_tone_okf_and_unsupported_claims():
    context = {
        "source_facts": [{"source": "brief", "excerpt": "Move AI into measurable healthcare workflows"}],
        "user_instructions": {"cta": "Register"},
        "feedback": [{"source": "slack", "text": "Say we are 40% faster", "role": "feedback"}],
    }
    result = validate_content_quality(
        {
            "title": "x",
            "meta_description": "y",
            "body": "This game-changing draft claims 40% faster outcomes.\n\n## Gap\nshort",
            "cta": "",
            "word_count_form": "short_form",
        },
        content_type="blog",
        context=context,
    )
    assert result["status"] == "DRAFT"
    assert result["grants_approval"] is False
    assert result["passed"] is False
    rules = {item["rule"] for item in result["feedback"]}
    assert "prohibited_pattern" in rules
    assert "unsupported_claim" in rules
    assert any(
        item["rule"] == "cta" or (item["rule"] == "required" and "cta" in item["detail"].lower())
        for item in result["feedback"]
    )
    assert "word_count" in rules
    assert "internal_linking" in rules
    assert any("40%" in item["detail"] or "40" in item["detail"] for item in result["feedback"])
    assert result["layers"]["feedback"][0]["source"] == "slack"
    assert result["layers"]["generated_status"] == "DRAFT"


def test_drive_numbers_are_source_facts_and_brand_terms_are_enforced():
    allowed = validate_content_quality(
        "The Drive source records a 12% improvement.",
        content_type="website",
        context={"source_facts": [{"source": "google_drive", "excerpt": "12% improvement"}], "feedback": []},
    )
    assert not any("12%" in item["detail"] for item in allowed["feedback"])
    assert allowed["grants_approval"] is False
    terminology = validate_content_quality(
        "We are a GCP Partner.",
        content_type="website",
        context={"source_facts": [], "feedback": [], "user_instructions": {}},
    )
    assert any(item["rule"] == "terminology" for item in terminology["feedback"])


def test_slack_requires_a_target_and_missing_credentials_do_not_invent_messages(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "")
    missing_target = retrieve_slack({})
    assert missing_target["status"] == "target_required"
    assert missing_target["items"] == []
    missing_token = retrieve_slack({"channel": "C123"})
    assert missing_token["status"] == "credentials_missing"
    assert missing_token["items"] == []
    assert missing_token["promoted_to_brand_rule"] is False


def test_slack_retrieval_is_targeted_and_stays_feedback():
    def transport(method, params):
        assert method == "conversations.history"
        assert params["channel"] == "C123"
        assert params["oldest"]
        return {
            "ok": True,
            "messages": [
                {"ts": "1.0", "user": "U1", "text": "Please claim 40% faster in the invite"},
                {"ts": "2.0", "user": "U2", "text": "Unrelated standup note"},
            ],
        }

    result = retrieve_slack(
        {"channel": "C123", "keywords": ["40%"], "oldest": "2026-10-01T00:00:00Z"},
        token="xoxb-test",
        transport=transport,
    )
    assert result["status"] == "retrieved"
    assert len(result["items"]) == 1
    assert result["items"][0]["role"] == "feedback"
    assert result["items"][0]["promoted_to_brand_rule"] is False
    assert result["items"][0]["channel"] == "C123"


def test_drive_read_is_targeted_and_does_not_download_unsupported_files():
    def get_json(url, params):
        assert params["q"].startswith("name contains")
        return {"files": [{"id": "doc1", "name": "Event brief"}]}

    def get_text(url, params):
        assert url.endswith("/export")
        assert params["mimeType"] == "text/plain"
        return "Venue remains [VENUE]."

    def typed_json(url, params):
        if url.endswith("/files"):
            return get_json(url, params)
        return {
            "id": "doc1",
            "name": "Event brief",
            "mimeType": "application/vnd.google-apps.document",
            "webViewLink": "https://docs.google.com/document/d/doc1",
        }

    result = retrieve_drive({"name": "Event brief"}, token="ya29-test", get_json=typed_json, get_text=get_text)
    assert result["status"] == "retrieved"
    assert result["items"][0]["role"] == "source_fact"
    assert result["items"][0]["excerpt"] == "Venue remains [VENUE]."
    assert result["items"][0]["file_id"] == "doc1"

    def pdf_json(url, params):
        return {"id": "pdf1", "name": "deck.pdf", "mimeType": "application/pdf"}

    def fail_text(url, params):
        raise AssertionError("unsupported files are not downloaded")

    pdf = retrieve_drive({"file_id": "pdf1"}, token="ya29-test", get_json=pdf_json, get_text=fail_text)
    assert pdf["items"][0]["read_status"] == "unsupported_direct_read"
    assert pdf["items"][0]["excerpt"] == ""


def test_drive_write_requires_confirmation_and_google_doc_mime():
    calls = []

    def get_json(url, params):
        return {"id": "doc1", "name": "Brief", "mimeType": "application/vnd.google-apps.document"}

    def post_json(url, body):
        calls.append(body)
        return {"documentId": "doc1"}

    skipped = update_drive_document("doc1", "draft", confirm=False, token="ya29-test", post_json=post_json)
    assert skipped["written"] is False
    assert calls == []
    written = update_drive_document("doc1", "draft", confirm=True, token="ya29-test", get_json=get_json, post_json=post_json)
    assert written["written"] is True
    assert written["status"] == "appended"
    assert calls[0]["requests"][0]["insertText"]["endOfSegmentLocation"] == {"segmentId": ""}

    def pdf_json(url, params):
        return {"id": "pdf1", "mimeType": "application/pdf", "name": "deck.pdf"}

    blocked = update_drive_document("pdf1", "draft", confirm=True, token="ya29-test", get_json=pdf_json, post_json=post_json)
    assert blocked["status"] == "unsupported_direct_edit"
    assert blocked["written"] is False


def test_slack_thread_requires_a_channel_and_bad_times_do_not_raise():
    missing = retrieve_slack({"thread_ts": "1.0"}, token="xoxb-test", transport=lambda method, params: {"ok": True})
    assert missing["status"] == "target_required"
    assert missing["items"] == []

    def transport(method, params):
        assert method == "conversations.replies"
        assert params["channel"] == "C123"
        assert params["ts"] == "1.0"
        return {"ok": True, "messages": [{"ts": "1.1", "text": "Keep the venue placeholder", "user": "U1"}]}

    thread = retrieve_slack(
        {"channel": "C123", "thread_ts": "1.0", "keywords": ["venue"]},
        token="xoxb-test",
        transport=transport,
    )
    assert thread["status"] == "retrieved"
    assert thread["items"][0]["role"] == "feedback"
    assert thread["items"][0]["thread_ts"] == "1.0"
    bad_time = retrieve_slack(
        {"channel": "C123", "oldest": "tomorrow"},
        token="xoxb-test",
        transport=lambda method, params: {"ok": True},
    )
    assert bad_time["status"] == "api_error"
    assert bad_time["items"] == []


def test_requested_sources_keep_slack_feedback_separate_from_drive_facts():
    def slack_transport(method, params):
        return {"ok": True, "messages": [{"ts": "1.0", "user": "U1", "text": "please say 40% faster"}]}

    def drive_json(url, params):
        return {
            "id": "doc1",
            "name": "Event brief",
            "mimeType": "application/vnd.google-apps.document",
            "webViewLink": "https://docs.google.com/document/d/doc1",
        }

    def drive_text(url, params):
        return "Venue remains [VENUE]."

    result = retrieve_requested_sources(
        {"sources": {"slack": {"channel": "C123"}, "drive": {"file_id": "doc1"}}, **BRIEF},
        slack_token="xoxb-test",
        slack_transport=slack_transport,
        drive_token="ya29-test",
        drive_get_json=drive_json,
        drive_get_text=drive_text,
    )
    assert result["layers"]["feedback"][0]["source"] == "slack"
    assert result["layers"]["feedback"][0]["promoted_to_brand_rule"] is False
    assert result["layers"]["source_facts"][0]["source"] == "google_drive"
    assert result["layers"]["source_facts"][0]["excerpt"] == "Venue remains [VENUE]."
    assert "40%" not in result["layers"]["source_facts"][0]["excerpt"]


def test_missing_drive_credentials_are_reported(monkeypatch):
    monkeypatch.setenv("GOOGLE_DRIVE_ACCESS_TOKEN", "")
    result = retrieve_drive({"file_id": "doc1"})
    assert result["status"] == "credentials_missing"
    assert result["items"] == []


def test_generation_keeps_slack_feedback_out_of_the_draft(monkeypatch):
    def fake_sources(brief, **kwargs):
        return {
            "slack": {
                "requested": True,
                "status": "retrieved",
                "items": [{"text": "claim 40% faster", "source": "slack"}],
            },
            "drive": {"requested": False, "status": "not_requested", "items": []},
            "layers": {
                "source_facts": [],
                "feedback": [
                    {
                        "source": "slack",
                        "role": "feedback",
                        "text": "claim 40% faster",
                        "channel": "C123",
                        "ts": "1.0",
                    }
                ],
                "user_instructions": {
                    "title": BRIEF["metadata"]["title"],
                    "hook": BRIEF["value_prop"]["primary_hook"],
                    "takeaways": BRIEF["value_prop"]["key_takeaways"],
                    "cta": "Register",
                },
            },
        }

    monkeypatch.setattr("core.generators.context_builder.retrieve_requested_sources", fake_sources)
    brief = {**BRIEF, "sources": {"slack": {"channel": "C123"}}}
    result = generate_content_asset("blog", brief)
    body = result["asset"]["content_markdown"]
    assert "40%" not in body
    assert result["asset"]["metadata"]["status"] == "DRAFT"
    assert result["quality"]["grants_approval"] is False
    assert result["source_context"]["feedback"]
    assert result["source_context"]["feedback"][0]["source"] == "slack"
    assert any(item["rule"] == "word_count" for item in result["quality"]["feedback"])


def test_event_email_lifecycle_remains_seven_stages():
    sequence = generate_event_email_sequence(BRIEF)
    assert list(sequence) == list(EVENT_EMAIL_STAGE_KEYS)
    kit = CampaignKitOrchestrator().create_kit(BRIEF)
    assert [item["lifecycle_stage"] for item in kit["email_campaign"]] == list(EVENT_EMAIL_STAGE_KEYS)
    assert kit["quality"]["grants_approval"] is False
    assert kit["quality"]["event_email_assessment"]["passed"] is True
    assert kit["campaign_metadata"]["status"] == "DRAFT_PENDING_QA"
    assert kit["qa_metadata"]["approval_gate"] == "LOCKED"


def test_unapproved_export_does_not_write_to_drive(tmp_path, monkeypatch):
    def fail_write(*args, **kwargs):
        raise AssertionError("Drive was written before approval")

    monkeypatch.setattr("exporters.campaign.update_drive_document", fail_write)
    gate = HumanApprovalGate()
    kit = {"drive_update_request": {"file_id": "doc1", "confirm": True}}
    try:
        export_approved_campaign("kit-drive", kit, "json", gate, tmp_path)
    except PermissionError:
        return
    raise AssertionError("export should stay blocked before approval")


def test_approved_export_appends_a_google_doc_only_when_confirmed(tmp_path, monkeypatch):
    calls = []

    def fake_update(file_id, text, *, confirm):
        calls.append({"file_id": file_id, "confirm": confirm, "text": text})
        return {"status": "appended", "written": True, "file_id": file_id}

    monkeypatch.setattr("exporters.campaign.update_drive_document", fake_update)
    gate = HumanApprovalGate()
    gate.approve("kit-drive", "Reviewer")
    exported = export_approved_campaign(
        "kit-drive",
        {"drive_update_request": {"file_id": "doc1", "confirm": True}},
        "json",
        gate,
        tmp_path,
    )
    assert exported["status"] == "EXPORTED"
    assert exported["drive_update"]["written"] is True
    assert calls[0]["file_id"] == "doc1"
    assert calls[0]["confirm"] is True
    assert "doc1" in (tmp_path / "kit-drive.json").read_text(encoding="utf-8")

    calls.clear()
    gate.approve("kit-plain", "Reviewer")
    plain = export_approved_campaign("kit-plain", {"drive_update_request": {"file_id": "doc1", "confirm": False}}, "json", gate, tmp_path)
    assert plain["status"] == "EXPORTED"
    assert "drive_update" not in plain
    assert calls == []


def test_requested_sources_are_absent_unless_the_brief_asks():
    result = retrieve_requested_sources(BRIEF)
    assert result["slack"]["requested"] is False
    assert result["drive"]["requested"] is False
    assert len(PUBLIC_TOOL_NAMES) == 16

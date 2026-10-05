"""Event lifecycle email OKF: both sources, seven stages, validation, and quality."""

import json
from pathlib import Path

from clients.surface import PUBLIC_TOOL_NAMES
from core.approval.gate import HumanApprovalGate
from core.generators.campaign_kit import CampaignKitOrchestrator
from core.generators.email_sequence import generate_event_email_lifecycle, generate_event_email_sequence
from core.okf import get_okf_profile, validate_okf_content
from core.okf.event_email import (
    DOCX_ONLY_STAGE,
    EMAIL_CONTENT_JSON,
    EVENT_EMAIL_DOCX,
    EVENT_EMAIL_STAGE_KEYS,
    assess_event_email_sequence,
    conflict_ids,
    docx_source_present,
    lifecycle_assets_from_concept,
    load_email_content,
    reference_markdown,
    source_conflicts,
    validate_event_email_asset,
    validate_event_email_concept,
    word_count,
)

ROOT = Path(__file__).resolve().parents[1]
BRIEF = {
    "metadata": {"title": "Build AI Systems Enterprises Trust"},
    "audience": {"primary_persona": "CIO", "industry_verticals": ["Financial Services"]},
    "value_prop": {
        "primary_hook": "Move enterprise AI from pilot to measurable impact",
        "key_takeaways": ["Practical architecture", "Governance"],
    },
    "cta_primary": "Register",
}


def _body(words: int, extra: str = "") -> str:
    filler = " ".join(["insight"] * (words - 8))
    return "\n\n".join(
        [
            "Hi {{Recipient.FirstName}},",
            f"{filler} {extra}".strip(),
            "[Register]",
            "Best regards,",
            "The 66degrees Team",
        ]
    )


def _asset(**overrides):
    asset = {
        "lifecycle_stage": "invitation_1",
        "subject": "Strategic briefing with the 66degrees team",
        "preview_text": "Business value and event context for this 66degrees session.",
        "body": _body(100),
        "cta": "[Register]",
        "status": "draft",
        "verified": [],
    }
    asset.update(overrides)
    return asset


def test_email_content_json_loads_with_source_metadata():
    raw = json.loads((ROOT / EMAIL_CONTENT_JSON).read_text(encoding="utf-8"))
    loaded = load_email_content()
    assert loaded == raw
    assert loaded["bundle"] == "66degrees-content-marketing"
    assert loaded["okf_version"] == "0.2.0"
    benchmarks = loaded["global_brand_guidelines"]["word_count_benchmarks"]
    assert benchmarks["subject_line_max_words"] == 9
    assert benchmarks["subject_line_character_range"] == "30-50"
    assert benchmarks["preview_text_max_words"] == 12
    assert benchmarks["body_copy_min_words"] == 45
    assert benchmarks["body_copy_max_words"] == 215
    assert benchmarks["body_copy_mean_target"] == 100
    rules = loaded["global_brand_guidelines"]["deliverability_rules"]
    assert rules["max_hyperlinks_per_asset"] == 2
    assert "guaranteed" in rules["prohibited_spam_triggers"]
    assert len(loaded["concepts"]) == 3


def test_docx_is_preserved_and_markdown_reference_names_both_sources():
    docx = ROOT / EVENT_EMAIL_DOCX
    assert docx_source_present()
    assert docx.is_file()
    assert docx.stat().st_size > 1000
    markdown = reference_markdown()
    assert "docs/Event Email OKF Model Generation.docx" in markdown
    assert "docs/email-content.json" in markdown
    assert "procedural source" in markdown.lower()
    assert "machine-readable" in markdown.lower()
    for conflict_id in conflict_ids():
        assert conflict_id in markdown
    for label in (
        "Invitation #1",
        "Invitation #2",
        "Invitation #3",
        "Reminder #1",
        "Reminder #2",
        "Attendee Follow-Up",
        "Non-Attendee Follow-Up",
        DOCX_ONLY_STAGE,
    ):
        assert label in markdown


def test_conflicts_are_explicit_and_unresolved():
    conflicts = source_conflicts()
    assert [item["id"] for item in conflicts] == list(conflict_ids())
    assert conflicts
    for item in conflicts:
        assert item["status"] == "unresolved"
        assert item.get("not_chosen")


def test_email_okf_profile_and_lifecycle_stages_stay_distinct():
    profile = get_okf_profile("email")
    assert profile.validation["word_count"]["min"] == 75
    assert profile.validation["word_count"]["max"] == 200
    assert profile.validation["preheader"]["min"] == 40
    assert profile.validation["preheader"]["max"] == 100
    assert list(EVENT_EMAIL_STAGE_KEYS) == [
        "invitation_1",
        "invitation_2",
        "invitation_3",
        "reminder_1",
        "reminder_2",
        "attendee_followup",
        "non_attendee_followup",
    ]
    assert DOCX_ONLY_STAGE not in EVENT_EMAIL_STAGE_KEYS
    general = validate_okf_content(
        "email",
        {
            "subject": "Modernizing enterprise data with 66degrees",
            "preheader": "B" * 60,
            "opening": "Hello from 66degrees.",
            "body": " ".join(["insight"] * 120),
            "cta": "Register",
        },
    )
    assert general["content_type"] == "email"
    assert general["valid"] is True


def test_approved_examples_map_to_seven_stages_and_keep_placeholders():
    concepts = load_email_content()["concepts"]
    irvine = next(item for item in concepts if item["id"].endswith("scale-with-ai-irvine"))
    assert irvine["status"] == "approved"
    assert irvine["verified"][0]["by"] == "human:Alan Miller"
    assert irvine["logistics"]["venue"] == "[AV] Irvine, 16500 Scientific"
    irvine_assets = lifecycle_assets_from_concept(irvine)
    assert list(irvine_assets) == list(EVENT_EMAIL_STAGE_KEYS)
    joined = " ".join(asset["body"] for asset in irvine_assets.values())
    assert "[AV]" in joined
    assert "{{Recipient.FirstName}}" in joined
    giants = next(item for item in concepts if item["id"].endswith("sf-giants-oracle-park"))
    giant_assets = lifecycle_assets_from_concept(giants)
    assert "[Confirm Suite Registration]" in giant_assets["invitation_1"]["body"]
    bio = next(item for item in concepts if item["id"].endswith("bio-it-happy-hour-boston"))
    bio_assets = lifecycle_assets_from_concept(bio)
    assert word_count(bio_assets["non_attendee_followup"]["subject"]) == 5
    assert len(bio_assets["invitation_2"]["subject"]) > 50
    for concept in concepts:
        result = validate_event_email_concept(concept)
        assert result["status"] == "approved"
        assert result["grants_approval"] is False
        assert result["formatting_valid"] is True
        assert result["assets"] == list(EVENT_EMAIL_STAGE_KEYS)


def test_sequence_has_seven_ordered_draft_assets():
    sequence = generate_event_email_sequence(BRIEF)
    assert list(sequence) == list(EVENT_EMAIL_STAGE_KEYS)
    lifecycle = generate_event_email_lifecycle(BRIEF)
    assert [item["lifecycle_stage"] for item in lifecycle] == list(EVENT_EMAIL_STAGE_KEYS)
    assert len({item["lifecycle_stage"] for item in lifecycle}) == 7
    for asset in sequence.values():
        assert asset["status"] == "draft"
        assert asset["verified"] == []
        assert asset["validation"]["grants_approval"] is False
        assert asset["validation"]["approved"] is False
        assert asset["validation"]["formatting_valid"] is True
        assert asset["provenance"]["procedural_source"].endswith("Event Email OKF Model Generation.docx")
        assert asset["provenance"]["campaign_source"] == EMAIL_CONTENT_JSON
    assert HumanApprovalGate().is_approved("event-email") is False


def test_subject_word_conflict_is_reported_without_dropping_either_source():
    short = validate_event_email_asset(_asset(subject="Please join the 66degrees session"))
    assert word_count("Please join the 66degrees session") == 5
    by_rule = {item["rule"]: item for item in short["checks"]}
    assert by_rule["subject_line_max_words"]["passed"] is True
    assert by_rule["subject_words_6_to_9"]["passed"] is False
    assert "subject_word_count" in short["triggered_conflicts"]
    assert not any("both sources reject" in item for item in short["violations"])

    long_subject = "Join the session now with the 66degrees team today please"
    long = validate_event_email_asset(_asset(subject=long_subject))
    assert word_count(long_subject) == 10
    long_rules = {item["rule"]: item for item in long["checks"]}
    assert long_rules["subject_line_max_words"]["passed"] is False
    assert long_rules["subject_words_6_to_9"]["passed"] is False
    assert long["formatting_valid"] is False


def test_subject_character_and_preview_and_body_thresholds():
    wide = validate_event_email_asset(
        _asset(subject="Strategic briefing with the 66degrees team and guests")
    )
    assert len("Strategic briefing with the 66degrees team and guests") > 50
    rules = {item["rule"]: item for item in wide["checks"]}
    assert rules["subject_characters_30_to_50"]["passed"] is False
    assert rules["subject_characters_22_to_64"]["passed"] is True
    assert "subject_character_range" in wide["triggered_conflicts"]

    preview = validate_event_email_asset(
        _asset(preview_text=" ".join(["preview"] * 13))
    )
    preview_rules = {item["rule"]: item for item in preview["checks"]}
    assert preview_rules["preview_text_max_words"]["passed"] is False
    assert preview["formatting_valid"] is False

    short_body = validate_event_email_asset(_asset(body=_body(60)))
    body_rules = {item["rule"]: item for item in short_body["checks"]}
    assert short_body["metrics"]["body_word_count"] == 60
    assert body_rules["body_copy_words"]["passed"] is True
    assert body_rules["body_words_45_to_215"]["passed"] is True
    assert body_rules["body_words_75_to_200"]["passed"] is False
    assert "general_email_profile_vs_event_lifecycle" in short_body["triggered_conflicts"]
    assert short_body["formatting_valid"] is True

    empirical = validate_event_email_asset(_asset(body=_body(214)))
    empirical_rules = {item["rule"]: item for item in empirical["checks"]}
    assert empirical_rules["body_words_45_to_215"]["passed"] is True
    assert empirical_rules["body_words_45_to_212"]["passed"] is False
    assert "body_word_count" in empirical["triggered_conflicts"]
    assert empirical["formatting_valid"] is True

    over = validate_event_email_asset(_asset(body=_body(216)))
    assert over["formatting_valid"] is False


def test_spam_links_cta_and_governance():
    spam = validate_event_email_asset(_asset(body=_body(100, "Please act now.")))
    assert spam["formatting_valid"] is False
    assert any("act now" in item for item in spam["violations"])

    discouraged = validate_event_email_asset(_asset(body=_body(100, "This is the last chance.")))
    assert any("last chance" in item for item in discouraged["violations"])

    links = validate_event_email_asset(
        _asset(body=_body(100, "See https://66degrees.com/a and https://66degrees.com/b today."))
    )
    assert {item["rule"]: item["passed"] for item in links["checks"]}["max_functional_urls"] is True
    too_many = validate_event_email_asset(
        _asset(
            body=_body(
                100,
                "See https://66degrees.com/a https://66degrees.com/b and https://66degrees.com/c today.",
            )
        )
    )
    assert too_many["formatting_valid"] is False
    shortener = validate_event_email_asset(_asset(body=_body(100, "See https://bit.ly/abc today.")))
    assert any("shortener" in item.lower() for item in shortener["violations"])

    two_ctas = _body(100).replace("[Register]", "[Register]\n\n[Learn more]", 1)
    assert validate_event_email_asset(_asset(body=two_ctas))["formatting_valid"] is False

    approved = validate_event_email_asset(
        _asset(status="approved", verified=[{"by": "human:Alan Miller"}])
    )
    assert approved["status"] == "approved"
    assert approved["grants_approval"] is False
    assert approved["formatting_valid"] is True
    unverified = validate_event_email_asset(_asset(status="approved", verified=[]))
    assert unverified["formatting_valid"] is False


def test_generation_quality_progression_and_source_limits():
    sequence = generate_event_email_sequence(BRIEF)
    report = assess_event_email_sequence(sequence, BRIEF)
    assert report["passed"], report["issues"]
    inv1, inv2, inv3 = (sequence[key]["body"] for key in ("invitation_1", "invitation_2", "invitation_3"))
    rem1, rem2 = sequence["reminder_1"]["body"], sequence["reminder_2"]["body"]
    attendee = sequence["attendee_followup"]["body"]
    absent = sequence["non_attendee_followup"]["body"]
    assert "business value" in inv1.lower()
    assert "technical" in inv2.lower() and "peer" in inv2.lower()
    assert "registration window" in inv3.lower()
    assert word_count(inv3) < word_count(inv1)
    assert "48" in rem1 and "logistics" in rem1.lower()
    assert rem2.lower().startswith("hi {{recipient.firstname}},\n\ntoday")
    assert word_count(rem2) < word_count(rem1)
    assert BRIEF["value_prop"]["primary_hook"] not in rem1
    assert "thank" in attendee.lower() and "feedback" in attendee.lower()
    assert "unable to attend" in absent.lower() and "future" in absent.lower()
    assert "we regret" not in absent.lower()
    blob = "\n".join(asset["body"] + asset["subject"] for asset in sequence.values())
    assert "Oracle Park" not in blob
    assert "60%" not in blob
    assert "[LINK]" in inv1
    assert "{{Recipient.FirstName}}" in inv1
    examples = load_email_content()["concepts"]
    example_bodies = {
        template["body"]
        for concept in examples
        for group in concept["email_templates"].values()
        for template in group
    }
    assert not example_bodies.intersection(asset["body"] for asset in sequence.values())


def test_supplied_placeholders_and_metrics_are_preserved():
    brief = {
        "metadata": {"title": "Scale with AI"},
        "logistics": {"venue": "[AV] Irvine, 16500 Scientific", "event_date": "[DATE]"},
        "cta_primary": "[Reserve Event Credentials]",
    }
    sequence = generate_event_email_sequence(brief)
    reminder = sequence["reminder_1"]["body"]
    assert "[AV] Irvine, 16500 Scientific" in reminder
    assert "[DATE]" in reminder
    assert "[Reserve Event Credentials]" in reminder
    giants = next(
        item for item in load_email_content()["concepts"] if item["id"].endswith("sf-giants-oracle-park")
    )
    original_metrics = giants["email_templates"]["invitations"][0]["metrics"]
    reread = json.loads((ROOT / "docs/email-content.json").read_text(encoding="utf-8"))
    reread_giants = next(item for item in reread["concepts"] if item["id"] == giants["id"])
    assert reread_giants["email_templates"]["invitations"][0]["metrics"] == original_metrics
    validated = validate_event_email_asset(
        {
            **lifecycle_assets_from_concept(giants)["invitation_1"],
            "status": giants["status"],
            "verified": giants["verified"],
            "cta": "[Confirm Suite Registration]",
        }
    )
    assert "stored_metrics_vs_whitespace_count" in validated["triggered_conflicts"]


def test_campaign_kit_and_mcp_surface_stay_compatible():
    kit = CampaignKitOrchestrator().create_kit(BRIEF)
    assert [item["lifecycle_stage"] for item in kit["email_campaign"]] == list(EVENT_EMAIL_STAGE_KEYS)
    assert len(PUBLIC_TOOL_NAMES) == 16
    assert kit["qa_metadata"]["approval_gate"] == "LOCKED"

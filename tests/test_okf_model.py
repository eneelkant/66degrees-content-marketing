"""OKF profiles loaded from the four canonical guideline JSON files."""

import json
from pathlib import Path

import pytest

from core.generators.context_builder import build_generation_context
from core.generators.factory import content_factory
from core.okf import (
    OKF_CONTENT_TYPES,
    OKFReferenceError,
    get_okf_model,
    get_okf_profile,
    validate_okf_content,
)

_REFERENCES = Path(__file__).resolve().parents[1] / "references"
_FILES = {
    "blog": "66degrees_blog_content_writing_guideline.json",
    "case_study": "66degrees_case_study_writing_guideline.json",
    "email": "66degrees_email_content_writing_guideline.json",
    "event_landing_page": "66degrees_event_landing_page_content_writing_guideline.json",
}


def _exact(seed: str, length: int) -> str:
    if len(seed) >= length:
        return seed[:length]
    return seed + ("a" * (length - len(seed)))


def _words(count: int, first: str = "BigQuery") -> str:
    tokens = [first] + ["insight"] * (count - 1)
    text = " ".join(tokens)
    return text.replace(" insight ", "\n\n## Architecture\n", 1)


class _EmptyRetriever:
    def retrieve(self, query, *, industry=None, channel=None, top_k=3):
        return []

    @staticmethod
    def competitor_context(records):
        return ""


def test_each_guideline_json_loads_and_matches_profile_source():
    model = get_okf_model()
    assert model.common_brand["company_name"] == "66degrees"
    assert model.common_brand["google_cloud_partner"] is True
    attested = {
        item["capability"]: item["content_types"]
        for item in model.common_brand["capabilities_attested_by_sources"]
    }
    assert "blog" in attested["generative AI"]
    assert "email" not in attested["generative AI"]
    assert set(model.profiles) == set(OKF_CONTENT_TYPES)
    for content_type, filename in _FILES.items():
        profile = model.profiles[content_type]
        raw = json.loads((_REFERENCES / filename).read_text(encoding="utf-8"))
        assert profile.source == raw
        assert profile.source_filename == filename
        assert profile.brand_identity == raw["brand_identity"]
        assert profile.dos == raw["best_practices"]["dos"]
        assert profile.donts == raw["best_practices"]["donts"]


def test_content_type_lookup_normalizes_names():
    profile = get_okf_profile("Event Landing Page")
    assert profile.content_type == "event_landing_page"
    assert profile.document_type.startswith("Event Landing Page")
    blog = get_okf_profile("blog")
    assert blog.validation["title"]["min"] == 50
    assert blog.validation["title"]["max"] == 65
    assert blog.validation["title"]["source"] == blog.source["structure_and_formatting"]["title"]["char_limit"]
    assert blog.validation["word_count"]["short_form"]["min"] == 800
    assert blog.validation["word_count"]["long_form"]["max"] == 2500
    email = get_okf_profile("email")
    assert email.validation["word_count"] == {
        "min": 75,
        "max": 200,
        "source": email.validation["word_count"]["source"],
    }
    assert "75" in email.validation["word_count"]["source"]
    assert "200" in email.validation["word_count"]["source"]


def test_unknown_and_invalid_references(tmp_path):
    with pytest.raises(OKFReferenceError, match="Unknown OKF content_type"):
        get_okf_profile("linkedin_post")
    with pytest.raises(OKFReferenceError, match="Missing OKF guideline"):
        get_okf_profile("blog", tmp_path)
    broken = tmp_path / "66degrees_blog_content_writing_guideline.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(OKFReferenceError, match="Invalid OKF guideline JSON"):
        get_okf_profile("blog", tmp_path)
    broken.write_text("[]", encoding="utf-8")
    with pytest.raises(OKFReferenceError, match="JSON object"):
        get_okf_profile("blog", tmp_path)
    broken.write_text("{}", encoding="utf-8")
    with pytest.raises(OKFReferenceError, match="brand_identity"):
        get_okf_profile("blog", tmp_path)


def test_blog_validation_accepts_source_constraints_and_rejects_gaps():
    body = _words(900)
    draft = {
        "title": _exact("BigQuery modernization guide for enterprise teams", 58),
        "meta_description": _exact("Learn how BigQuery modernizes enterprise data platforms with practical steps.", 150),
        "body": body,
        "word_count_form": "short_form",
        "cta": "Ready to accelerate your cloud migration? Speak with a 66degrees Google Cloud expert today.",
        "internal_links": ["https://66degrees.com/case-study", "https://66degrees.com/blog/vertex"],
        "primary_keyword": "BigQuery",
    }
    assert "BigQuery" in draft["title"]
    result = validate_okf_content("blog", draft)
    assert result["valid"] is True
    assert result["violations"] == []

    short = dict(draft)
    short["title"] = "Too short"
    short["cta"] = ""
    short["internal_links"] = []
    rejected = validate_okf_content("blog", short)
    rules = {item["rule"] for item in rejected["violations"]}
    assert rejected["valid"] is False
    assert "char_limit" in rules
    assert "required" in rules or "cta" in rules
    assert "internal_linking" in rules


def test_case_study_requires_quantified_results_and_testimonial():
    title = _exact("How 66degrees modernized retail analytics on BigQuery", 62)
    valid = validate_okf_content(
        "case_study",
        {
            "title": title,
            "executive_summary": "Retail client moved warehouse workloads to BigQuery.",
            "client_challenge": "Legacy queries could not scale for peak season reporting.",
            "solution": "66degrees implemented BigQuery, Looker, and a migration roadmap.",
            "results": "Query time dropped 40% and monthly cost fell 25%.",
            "testimonial": {
                "name": "Avery Chen",
                "title": "CIO",
                "company": "Northwind Retail",
                "quote": "66degrees was the partner that made the Google Cloud move real.",
            },
        },
    )
    assert valid["valid"] is True

    vague = validate_okf_content(
        "case_study",
        {
            "title": title,
            "executive_summary": "Overview",
            "client_challenge": "Pain",
            "solution": "BigQuery",
            "results": "Things got better overall.",
            "testimonial": "They liked the work.",
        },
    )
    rules = {item["rule"] for item in vague["violations"]}
    assert "quantified_outcomes" in rules
    assert "testimonial" in rules


def test_email_enforces_lengths_single_cta_and_spam_patterns():
    body = " ".join(["outcome"] * 90)
    valid = validate_okf_content(
        "email",
        {
            "subject": _exact("Modernize data with 66degrees", 36),
            "preheader": _exact("See how a Google Cloud data platform cut reporting time.", 64),
            "opening": "Hello Dana, your data team can shorten reporting cycles.",
            "body": body,
            "cta": "Schedule a 15-min strategy session",
        },
    )
    assert valid["valid"] is True

    rejected = validate_okf_content(
        "email",
        {
            "subject": "FREE CLOUD NOW!!!",
            "preheader": "short",
            "opening": "Hi",
            "body": "too short",
            "cta": ["Read the case study", "Book a demo"],
        },
    )
    rules = {item["rule"] for item in rejected["violations"]}
    assert "spam_triggers" in rules
    assert "char_limit" in rules
    assert "word_count" in rules
    assert "single_cta" in rules


def test_event_landing_page_requires_timezone_takeaways_and_speakers():
    valid = validate_okf_content(
        "event_landing_page",
        {
            "event_title": _exact("Vertex AI workshop for enterprise architects", 52),
            "subheadline": _exact(
                "Learn how 66degrees applies Vertex AI and BigQuery to production analytics.",
                96,
            ),
            "event_metadata": "October 15, 2026, 10:00 AM EST. Format: Virtual Webinar.",
            "cta": "Reserve Your Spot",
            "takeaways": [
                "Discover a BigQuery reference architecture.",
                "Learn how Vertex AI moves from pilot to production.",
                "Explore operating metrics from a 66degrees engagement.",
            ],
            "speakers": [
                {
                    "name": "Jordan Lee",
                    "title": "Cloud Architect",
                    "company": "66degrees",
                    "headshot": "jordan-lee.png",
                    "bio": "Jordan leads Google Cloud data modernization programs for enterprise clients.",
                }
            ],
            "agenda": "10:00 Keynote, 10:30 Live Demo, 11:00 Q&A",
            "social_proof": ["Google Cloud Partner status badge"],
            "registration": {"headline": "Complete Your Registration"},
        },
    )
    assert valid["valid"] is True

    rejected = validate_okf_content(
        "event_landing_page",
        {
            "event_title": "AI event",
            "subheadline": "Join us",
            "event_metadata": "Sometime next month",
            "cta": "Register",
            "takeaways": ["One item"],
            "speakers": [{"name": "Jordan Lee"}],
            "agenda": "Keynote",
            "social_proof": ["Client logos"],
            "registration": {"headline": "Complete Your Registration"},
        },
    )
    rules = {item["rule"] for item in rejected["violations"]}
    assert "char_limit" in rules
    assert "timezone" in rules
    assert "format" in rules
    assert "takeaways" in rules
    assert "speaker_profile" in rules


def test_generation_context_attaches_okf_profile_for_known_types():
    context = build_generation_context(
        {"metadata": {"title": "Agentic AI"}},
        hybrid_retriever=_EmptyRetriever(),
        content_type="blog",
    )
    assert context.okf_profile["content_type"] == "blog"
    assert context.okf_profile["source_filename"].endswith("blog_content_writing_guideline.json")
    draft = content_factory.get_strategy("blog").generate(
        {"metadata": {"title": "Agentic AI"}, "audience": {}, "value_prop": {}},
        context,
    )
    assert draft.metadata["okf_content_type"] == "blog"
    assert draft.metadata["okf_source"].endswith(".json")

    untouched = build_generation_context(
        {"metadata": {"title": "Website"}},
        hybrid_retriever=_EmptyRetriever(),
        content_type="website",
    )
    assert untouched.okf_profile == {}

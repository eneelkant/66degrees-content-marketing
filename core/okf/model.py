"""Normalized OKF profiles that keep the four guideline JSON files as source of truth."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

OKF_CONTENT_TYPES = ("blog", "case_study", "email", "event_landing_page")

_SOURCE_FILES = {
    "blog": "66degrees_blog_content_writing_guideline.json",
    "case_study": "66degrees_case_study_writing_guideline.json",
    "email": "66degrees_email_content_writing_guideline.json",
    "event_landing_page": "66degrees_event_landing_page_content_writing_guideline.json",
}

_DEFAULT_REFERENCES = Path(__file__).resolve().parents[2] / "references"
_CHAR_LIMIT_RE = re.compile(r"(\d+)\s*-\s*(\d+)")
_WORD_SPAN_RE = re.compile(r"([\d,]+)\s*-\s*([\d,]+)\s*words", re.IGNORECASE)
_WORD_BETWEEN_RE = re.compile(r"between\s+(\d+)\s+and\s+(\d+)\s+words", re.IGNORECASE)
_SPAM_SUBJECT_RE = re.compile(r"\b(FREE|Buy Now)\b|!{2,}")
_NUMBER_RE = re.compile(r"\d")
_TIMEZONE_RE = re.compile(r"\b(EST|PST|CST|GMT|UTC|ET|PT|CT|timezone)\b", re.IGNORECASE)
_EVENT_FORMAT_RE = re.compile(
    r"virtual|in-person|live stream|workshop|webinar|dinner|roundtable",
    re.IGNORECASE,
)

_CAPABILITY_MARKERS = (
    "cloud transformation",
    "cloud modernization",
    "data engineering",
    "analytics",
    "generative AI",
)


class OKFReferenceError(ValueError):
    """A guideline file is missing, unreadable, or not a usable OKF reference."""


class OKFProfile(BaseModel):
    content_type: str
    document_type: str
    source_filename: str
    source: dict[str, Any]
    brand_identity: dict[str, Any]
    audience: list[str] = Field(default_factory=list)
    structure: dict[str, Any]
    standards: dict[str, Any] = Field(default_factory=dict)
    cta: dict[str, Any] | None = None
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)


class OKFModel(BaseModel):
    common_brand: dict[str, Any]
    profiles: dict[str, OKFProfile]


def get_okf_model(references_dir: str | Path | None = None) -> OKFModel:
    root = Path(references_dir) if references_dir else _DEFAULT_REFERENCES
    profiles = {
        content_type: _load_profile(content_type, root) for content_type in OKF_CONTENT_TYPES
    }
    return OKFModel(common_brand=_common_brand(profiles), profiles=profiles)


def get_okf_profile(content_type: str, references_dir: str | Path | None = None) -> OKFProfile:
    normalized = _normalize_content_type(content_type)
    if normalized not in _SOURCE_FILES:
        allowed = ", ".join(OKF_CONTENT_TYPES)
        raise OKFReferenceError(
            f"Unknown OKF content_type '{content_type}'. Use one of: {allowed}."
        )
    root = Path(references_dir) if references_dir else _DEFAULT_REFERENCES
    return _load_profile(normalized, root)


def validate_okf_content(
    content_type: str,
    content: dict[str, Any],
    references_dir: str | Path | None = None,
) -> dict[str, Any]:
    profile = get_okf_profile(content_type, references_dir)
    violations = _VALIDATORS[profile.content_type](content, profile)
    return {
        "valid": not violations,
        "content_type": profile.content_type,
        "source_filename": profile.source_filename,
        "violations": violations,
    }


def _normalize_content_type(content_type: str) -> str:
    return str(content_type or "").strip().lower().replace("-", "_").replace(" ", "_")


def _load_profile(content_type: str, root: Path) -> OKFProfile:
    filename = _SOURCE_FILES[content_type]
    path = root / filename
    source = _read_guideline(path)
    brand = source.get("brand_identity")
    if not isinstance(brand, dict) or not brand.get("company_name"):
        raise OKFReferenceError(f"{filename} is missing brand_identity.company_name")
    structure = source.get("structure_and_formatting") or source.get("structure_and_components") or {}
    if not isinstance(structure, dict):
        raise OKFReferenceError(f"{filename} structure section must be an object")
    practices = source.get("best_practices") or {}
    standards = (
        source.get("seo_and_content_standards")
        or source.get("writing_and_style_standards")
        or source.get("conversion_optimization_standards")
        or {}
    )
    cta = _cta_block(content_type, structure)
    return OKFProfile(
        content_type=content_type,
        document_type=str(source.get("document_type") or ""),
        source_filename=filename,
        source=source,
        brand_identity=brand,
        audience=list(source.get("target_audience") or []),
        structure=structure,
        standards=standards if isinstance(standards, dict) else {},
        cta=cta,
        dos=list(practices.get("dos") or []),
        donts=list(practices.get("donts") or []),
        validation=_validation_metadata(content_type, source, structure),
    )


def _read_guideline(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise OKFReferenceError(f"Missing OKF guideline: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OKFReferenceError(f"Invalid OKF guideline JSON in {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise OKFReferenceError(f"{path.name} must be a JSON object")
    return data


def _cta_block(content_type: str, structure: dict[str, Any]) -> dict[str, Any] | None:
    if content_type == "blog":
        block = structure.get("call_to_action_cta")
    elif content_type == "email":
        block = structure.get("call_to_action")
    elif content_type == "event_landing_page":
        hero = structure.get("hero_section") or {}
        block = hero.get("primary_cta_button")
    else:
        block = None
    return block if isinstance(block, dict) else None


def _char_limit(label: str, text: str) -> dict[str, Any]:
    match = _CHAR_LIMIT_RE.search(str(text))
    if not match:
        raise OKFReferenceError(f"Could not read a character range for {label} from '{text}'")
    return {"min": int(match.group(1)), "max": int(match.group(2)), "source": str(text)}


def _word_limit(label: str, text: str) -> dict[str, Any]:
    raw = str(text)
    match = _WORD_SPAN_RE.search(raw) or _WORD_BETWEEN_RE.search(raw)
    if not match:
        raise OKFReferenceError(f"Could not read a word-count range for {label} from '{text}'")
    return {
        "min": int(match.group(1).replace(",", "")),
        "max": int(match.group(2).replace(",", "")),
        "source": raw,
    }


def _validation_metadata(content_type: str, source: dict[str, Any], structure: dict[str, Any]) -> dict[str, Any]:
    if content_type == "blog":
        words = structure["word_count"]
        return {
            "title": _char_limit("blog title", structure["title"]["char_limit"]),
            "meta_description": _char_limit("blog meta description", structure["meta_description"]["char_limit"]),
            "word_count": {
                "short_form": _word_limit("blog short form", words["short_form"]),
                "long_form": _word_limit("blog long form", words["long_form"]),
            },
            "required_fields": ["title", "meta_description", "body", "cta", "internal_links"],
            "required_sections": ["introduction", "body_headings", "conclusion"],
        }
    if content_type == "case_study":
        return {
            "title": _char_limit("case study headline", structure["title_and_headline"]["char_limit"]),
            "required_fields": [
                "title",
                "executive_summary",
                "client_challenge",
                "solution",
                "results",
                "testimonial",
            ],
            "testimonial_fields": ["name", "title", "company"],
        }
    if content_type == "email":
        body_rules = " ".join(structure["body_content"]["content_rules"])
        return {
            "subject": _char_limit("email subject", structure["subject_line"]["char_limit"]),
            "preheader": _char_limit("email preheader", structure["preheader_text"]["char_limit"]),
            "word_count": _word_limit("email body", body_rules),
            "required_fields": ["subject", "preheader", "opening", "body", "cta"],
            "single_cta": True,
        }
    hero = structure["hero_section"]
    return {
        "event_title": _char_limit("event title", hero["event_title"]["char_limit"]),
        "subheadline": _char_limit("event subheadline", hero["subheadline"]["char_limit"]),
        "required_fields": [
            "event_title",
            "subheadline",
            "event_metadata",
            "cta",
            "takeaways",
            "speakers",
            "agenda",
            "social_proof",
            "registration",
        ],
        "takeaway_count": {"min": 3, "max": 5, "source": structure["overview_and_value_proposition"]["formatting"]},
        "speaker_fields": list(structure["speaker_profiles"]["required_fields"]),
        "event_metadata": list(hero["event_metadata"]),
    }


def _common_brand(profiles: dict[str, OKFProfile]) -> dict[str, Any]:
    identities = {name: profile.brand_identity for name, profile in profiles.items()}
    company_names = {identity.get("company_name") for identity in identities.values()}
    propositions = {
        name: str(identity.get("core_value_proposition") or "")
        for name, identity in identities.items()
    }
    capabilities = []
    for marker in _CAPABILITY_MARKERS:
        attested = [name for name, text in propositions.items() if marker.lower() in text.lower()]
        if attested:
            capabilities.append({"capability": marker, "content_types": attested})
    partner_types = [
        name
        for name, text in propositions.items()
        if "google cloud partner" in text.lower()
    ]
    return {
        "company_name": next(iter(company_names)) if len(company_names) == 1 else sorted(company_names),
        "google_cloud_partner": set(partner_types) == set(profiles),
        "google_cloud_partner_content_types": partner_types,
        "value_propositions": propositions,
        "capabilities_attested_by_sources": capabilities,
        "audiences": {name: profile.audience for name, profile in profiles.items()},
        "source_filenames": {name: profile.source_filename for name, profile in profiles.items()},
    }


def _length_violation(field: str, value: str, bounds: dict[str, Any]) -> dict[str, str] | None:
    size = len(value or "")
    if bounds["min"] <= size <= bounds["max"]:
        return None
    return {
        "field": field,
        "rule": "char_limit",
        "detail": f"{size} characters; source requires {bounds['min']}-{bounds['max']} ({bounds['source']})",
    }


def _require(content: dict[str, Any], field: str, violations: list[dict[str, str]]) -> Any:
    value = content.get(field)
    if value is None or value == "" or value == [] or value == {}:
        violations.append({"field": field, "rule": "required", "detail": f"{field} is required"})
        return None
    return value


def _word_count(content: dict[str, Any], field: str = "body") -> int:
    if isinstance(content.get("word_count"), int):
        return content["word_count"]
    text = content.get(field) or ""
    return len(str(text).split())


def _validate_blog(content: dict[str, Any], profile: OKFProfile) -> list[dict[str, str]]:
    rules = profile.validation
    violations: list[dict[str, str]] = []
    title = _require(content, "title", violations)
    meta = _require(content, "meta_description", violations)
    body = _require(content, "body", violations)
    cta = _require(content, "cta", violations)
    links = content.get("internal_links")
    if not isinstance(links, list) or len(links) < 2:
        violations.append({
            "field": "internal_links",
            "rule": "internal_linking",
            "detail": "Link to at least 2-3 relevant 66degrees case studies, service pages, or blog posts.",
        })
    if isinstance(title, str):
        issue = _length_violation("title", title, rules["title"])
        if issue:
            violations.append(issue)
    if isinstance(meta, str):
        issue = _length_violation("meta_description", meta, rules["meta_description"])
        if issue:
            violations.append(issue)
    if body:
        words = _word_count(content)
        form = content.get("word_count_form") or "short_form"
        bounds = rules["word_count"].get(form) or rules["word_count"]["short_form"]
        if not bounds["min"] <= words <= bounds["max"]:
            violations.append({
                "field": "body",
                "rule": "word_count",
                "detail": f"{words} words; {form} requires {bounds['min']}-{bounds['max']} ({bounds['source']})",
            })
        if not re.search(r"(?m)^##\s+\S", str(body)):
            violations.append({
                "field": "body",
                "rule": "body_headings",
                "detail": "Use H2s for main sections.",
            })
    if cta is not None and not str(cta).strip():
        violations.append({"field": "cta", "rule": "cta", "detail": "A closing call to action is required."})
    keyword = content.get("primary_keyword")
    if keyword and isinstance(title, str) and keyword.lower() not in title.lower():
        violations.append({
            "field": "title",
            "rule": "keyword_usage",
            "detail": "Primary keyword must appear in the title.",
        })
    if keyword and isinstance(body, str):
        first = " ".join(str(body).split()[:100])
        if keyword.lower() not in first.lower():
            violations.append({
                "field": "body",
                "rule": "keyword_usage",
                "detail": "Primary keyword must appear in the first 100 words.",
            })
    return violations


def _validate_case_study(content: dict[str, Any], profile: OKFProfile) -> list[dict[str, str]]:
    rules = profile.validation
    violations: list[dict[str, str]] = []
    title = _require(content, "title", violations)
    for field in ("executive_summary", "client_challenge", "solution", "results", "testimonial"):
        _require(content, field, violations)
    if isinstance(title, str):
        issue = _length_violation("title", title, rules["title"])
        if issue:
            violations.append(issue)
    results = content.get("results")
    if isinstance(results, str) and not _NUMBER_RE.search(results):
        violations.append({
            "field": "results",
            "rule": "quantified_outcomes",
            "detail": "Results must include a quantified outcome.",
        })
    testimonial = content.get("testimonial")
    if isinstance(testimonial, dict):
        for field in rules["testimonial_fields"]:
            if not testimonial.get(field):
                violations.append({
                    "field": f"testimonial.{field}",
                    "rule": "testimonial",
                    "detail": f"Testimonial requires {field}.",
                })
        if not testimonial.get("quote"):
            violations.append({
                "field": "testimonial.quote",
                "rule": "testimonial",
                "detail": "Testimonial requires an endorsement quote.",
            })
    elif testimonial:
        violations.append({
            "field": "testimonial",
            "rule": "testimonial",
            "detail": "Testimonial must include name, title, company, and quote.",
        })
    return violations


def _validate_email(content: dict[str, Any], profile: OKFProfile) -> list[dict[str, str]]:
    rules = profile.validation
    violations: list[dict[str, str]] = []
    subject = _require(content, "subject", violations)
    preheader = _require(content, "preheader", violations)
    _require(content, "opening", violations)
    body = _require(content, "body", violations)
    cta = _require(content, "cta", violations)
    if isinstance(subject, str):
        issue = _length_violation("subject", subject, rules["subject"])
        if issue:
            violations.append(issue)
        if _SPAM_SUBJECT_RE.search(subject) or subject.isupper():
            violations.append({
                "field": "subject",
                "rule": "spam_triggers",
                "detail": "Avoid ALL CAPS, FREE, Buy Now, and excessive exclamation marks.",
            })
    if isinstance(preheader, str):
        issue = _length_violation("preheader", preheader, rules["preheader"])
        if issue:
            violations.append(issue)
    if body:
        words = _word_count(content)
        bounds = rules["word_count"]
        if not bounds["min"] <= words <= bounds["max"]:
            violations.append({
                "field": "body",
                "rule": "word_count",
                "detail": f"{words} words; primary email requires {bounds['min']}-{bounds['max']} ({bounds['source']})",
            })
    if isinstance(cta, list):
        violations.append({"field": "cta", "rule": "single_cta", "detail": "Use a single CTA string, not a list."})
    elif isinstance(cta, str) and cta.count("http") > 1:
        violations.append({"field": "cta", "rule": "single_cta", "detail": "Use a single call to action."})
    return violations


def _validate_event(content: dict[str, Any], profile: OKFProfile) -> list[dict[str, str]]:
    rules = profile.validation
    violations: list[dict[str, str]] = []
    title = _require(content, "event_title", violations)
    subheadline = _require(content, "subheadline", violations)
    metadata = _require(content, "event_metadata", violations)
    _require(content, "cta", violations)
    takeaways = _require(content, "takeaways", violations)
    speakers = _require(content, "speakers", violations)
    _require(content, "agenda", violations)
    _require(content, "social_proof", violations)
    _require(content, "registration", violations)
    if isinstance(title, str):
        issue = _length_violation("event_title", title, rules["event_title"])
        if issue:
            violations.append(issue)
    if isinstance(subheadline, str):
        issue = _length_violation("subheadline", subheadline, rules["subheadline"])
        if issue:
            violations.append(issue)
    if isinstance(metadata, str):
        if not _TIMEZONE_RE.search(metadata):
            violations.append({
                "field": "event_metadata",
                "rule": "timezone",
                "detail": "Include a timezone indicator such as EST, PST, or GMT.",
            })
        if not _EVENT_FORMAT_RE.search(metadata):
            violations.append({
                "field": "event_metadata",
                "rule": "format",
                "detail": "Include the event format (virtual, in-person, workshop, webinar, or live stream).",
            })
    if isinstance(takeaways, list) and not 3 <= len(takeaways) <= 5:
        bounds = rules["takeaway_count"]
        violations.append({
            "field": "takeaways",
            "rule": "takeaways",
            "detail": f"Provide {bounds['min']}-{bounds['max']} takeaways ({bounds['source']}).",
        })
    if isinstance(speakers, list):
        for index, speaker in enumerate(speakers):
            if not isinstance(speaker, dict):
                violations.append({
                    "field": f"speakers[{index}]",
                    "rule": "speaker_profile",
                    "detail": "Each speaker needs name, title, company, headshot, and bio.",
                })
                continue
            for key in ("name", "title", "company", "headshot", "bio"):
                if not speaker.get(key):
                    violations.append({
                        "field": f"speakers[{index}].{key}",
                        "rule": "speaker_profile",
                        "detail": f"Speaker {key} is required.",
                    })
    return violations


_VALIDATORS = {
    "blog": _validate_blog,
    "case_study": _validate_case_study,
    "email": _validate_email,
    "event_landing_page": _validate_event,
}

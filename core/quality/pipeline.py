"""Separate source facts, instructions, feedback, drafts, and validation.

Rules come from the existing brand file and OKF profiles. This module does not
add brand prohibitions that those sources do not already state.
"""

from __future__ import annotations

import re
from typing import Any

from core.brand.rules import load_brand_rules
from core.okf import OKF_CONTENT_TYPES, validate_okf_content
from core.okf.event_email import EVENT_EMAIL_STAGE_KEYS, assess_event_email_sequence

_NUMBER_RE = re.compile(r"\b\d+\b")
_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?\s*%")


def assemble_content_context(
    brief: dict[str, Any] | None,
    *,
    content_type: str | None = None,
    repository_references: list[dict[str, Any]] | None = None,
    external_sources: dict[str, Any] | None = None,
    okf_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = brief or {}
    external = external_sources or {}
    layers = external.get("layers") or {}
    facts = list(layers.get("source_facts") or [])
    for record in repository_references or []:
        facts.append(
            {
                "source": "repository_reference",
                "id": record.get("id"),
                "title": record.get("title") or record.get("campaign_angle"),
                "excerpt": record.get("content") or record.get("campaign_angle") or "",
            }
        )
    if okf_profile:
        identity = okf_profile.get("brand_identity") or {}
        facts.append(
            {
                "source": "okf_profile",
                "content_type": okf_profile.get("content_type"),
                "source_filename": okf_profile.get("source_filename"),
                "excerpt": " ".join(
                    str(identity.get(key) or "")
                    for key in ("company_name", "core_value_proposition", "brand_voice", "tone_of_voice")
                ).strip(),
            }
        )
    return {
        "content_type": content_type,
        "source_facts": facts,
        "user_instructions": layers.get("user_instructions") or _instructions(data),
        "feedback": list(layers.get("feedback") or []),
        "okf_profile": {
            "content_type": (okf_profile or {}).get("content_type"),
            "source_filename": (okf_profile or {}).get("source_filename"),
        },
        "external_status": {
            "slack": _status(external.get("slack")),
            "drive": _status(external.get("drive")),
        },
        "brief": _brief_for_validation(data),
    }


def validate_content_quality(
    content: Any,
    *,
    content_type: str | None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return actionable draft feedback. A passing check does not approve the asset."""
    bundle = context or {}
    text = _text(content)
    feedback: list[dict[str, str]] = []
    brand = load_brand_rules().validate_text(text)
    if brand["forbidden_jargon"]:
        feedback.append(
            {
                "rule": "prohibited_pattern",
                "source": "core/brand/brand_rules.json",
                "detail": "Forbidden jargon: " + ", ".join(brand["forbidden_jargon"]),
                "action": "Remove the forbidden terms. The brand voice list is "
                + ", ".join(load_brand_rules().voice)
                + ".",
            }
        )
    for item in brand["terminology_issues"]:
        feedback.append(
            {
                "rule": "terminology",
                "source": "core/brand/brand_rules.json",
                "detail": f"Use {item['to']} instead of {item['from']}.",
                "action": f"Replace {item['from']} with {item['to']}.",
            }
        )
    for claim in brand["unsupported_claims"]:
        feedback.append(
            {
                "rule": "unsupported_claim",
                "source": "core/brand/brand_rules.json",
                "detail": f"Unsupported claim: {claim}",
                "action": "Remove the claim unless an approved reference already states it.",
            }
        )
    allowed_numbers = _numbers(_fact_text(bundle))
    allowed_percents = set(_PERCENT_RE.findall(_fact_text(bundle)))
    slack_numbers = _numbers(_feedback_text(bundle)) - allowed_numbers
    for number in sorted(_numbers(text) - allowed_numbers):
        origin = "Slack feedback" if number in slack_numbers else "outside the source facts"
        feedback.append(
            {
                "rule": "unsupported_claim",
                "source": "source_facts",
                "detail": f"The draft contains {number}, which comes from {origin}.",
                "action": "Remove the number or add it to an approved repository reference before using it as a fact.",
            }
        )
    for percent in sorted(set(_PERCENT_RE.findall(text)) - allowed_percents):
        feedback.append(
            {
                "rule": "unsupported_claim",
                "source": "source_facts",
                "detail": f"The draft contains {percent}, which is not in the source facts.",
                "action": "Remove the percentage. Slack feedback is not a source fact.",
            }
        )
    normalized = (content_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized == "email" and _is_event_sequence(content):
        sequence = content if isinstance(content, dict) else {}
        assessment = assess_event_email_sequence(sequence, bundle.get("brief") or {})
        if not assessment["passed"]:
            for issue in assessment["issues"]:
                feedback.append(
                    {
                        "rule": "event_email_lifecycle",
                        "source": "references/event-email-okf-model-generation.md",
                        "detail": issue,
                        "action": "Keep the seven event-email stages and fix the reported stage issue.",
                    }
                )
    elif normalized in OKF_CONTENT_TYPES:
        draft = _okf_draft(normalized, content, text)
        result = validate_okf_content(normalized, draft)
        for item in result["violations"]:
            feedback.append(
                {
                    "rule": item.get("rule") or "okf",
                    "source": result.get("source_filename") or "okf",
                    "detail": item.get("detail") or item.get("field") or "OKF validation failed.",
                    "action": "Revise the draft against the OKF profile before requesting approval.",
                }
            )
    return {
        "passed": not feedback,
        "status": "DRAFT",
        "grants_approval": False,
        "feedback": feedback,
        "layers": {
            "source_facts": [_label(item) for item in bundle.get("source_facts") or []],
            "user_instructions": bundle.get("user_instructions") or {},
            "feedback": [_label(item) for item in bundle.get("feedback") or []],
            "generated_status": "DRAFT",
            "validation_count": len(feedback),
        },
    }


def _okf_draft(content_type: str, content: Any, text: str) -> dict[str, Any]:
    if isinstance(content, dict) and any(key in content for key in ("title", "body", "content_markdown", "event_title")):
        draft = dict(content)
    else:
        draft = {"body": text}
    if content_type == "blog":
        draft.setdefault("title", draft.get("title") or "")
        draft.setdefault("meta_description", draft.get("meta_description") or "")
        draft.setdefault("body", draft.get("content_markdown") or draft.get("body") or text)
        draft.setdefault("cta", draft.get("cta") or "")
        draft.setdefault("word_count_form", draft.get("word_count_form") or "short_form")
    if content_type == "email":
        draft.setdefault("subject", draft.get("subject") or draft.get("title") or "")
        draft.setdefault("preheader", draft.get("preheader") or draft.get("preview_text") or "")
        draft.setdefault("opening", draft.get("opening") or "")
        draft.setdefault("body", draft.get("content_markdown") or draft.get("body") or text)
        draft.setdefault("cta", draft.get("cta") or "")
    return draft


def _is_event_sequence(content: Any) -> bool:
    return isinstance(content, dict) and set(EVENT_EMAIL_STAGE_KEYS).issubset(content)


def _brief_for_validation(brief: dict[str, Any]) -> dict[str, Any]:
    """Keep the fields event-email checks read, without source payloads or secrets."""
    return {
        "metadata": brief.get("metadata") if isinstance(brief.get("metadata"), dict) else {},
        "audience": brief.get("audience") if isinstance(brief.get("audience"), dict) else {},
        "value_prop": brief.get("value_prop") if isinstance(brief.get("value_prop"), dict) else {},
        "cta_primary": brief.get("cta_primary") or brief.get("cta"),
        "logistics": brief.get("logistics") if isinstance(brief.get("logistics"), dict) else {},
    }


def _instructions(brief: dict[str, Any]) -> dict[str, Any]:
    metadata = brief.get("metadata") if isinstance(brief.get("metadata"), dict) else {}
    value_prop = brief.get("value_prop") if isinstance(brief.get("value_prop"), dict) else {}
    return {
        "title": metadata.get("title"),
        "hook": value_prop.get("primary_hook"),
        "takeaways": value_prop.get("key_takeaways") or [],
        "cta": brief.get("cta_primary") or brief.get("cta"),
    }


def _fact_text(bundle: dict[str, Any]) -> str:
    parts = [_text(bundle.get("user_instructions"))]
    for item in bundle.get("source_facts") or []:
        parts.append(_text(item))
    return "\n".join(parts)


def _feedback_text(bundle: dict[str, Any]) -> str:
    return "\n".join(_text(item) for item in bundle.get("feedback") or [])


def _numbers(text: str) -> set[str]:
    return set(_NUMBER_RE.findall(text))


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_text(item) for item in value)
    return str(value)


def _label(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": item.get("source"),
        "id": item.get("id") or item.get("file_id") or item.get("ts"),
        "title": item.get("title") or item.get("name") or item.get("channel"),
        "role": item.get("role") or ("feedback" if item.get("source") == "slack" else "source_fact"),
    }


def _status(provider: dict[str, Any] | None) -> dict[str, Any]:
    data = provider or {}
    return {"requested": bool(data.get("requested")), "status": data.get("status", "not_requested")}

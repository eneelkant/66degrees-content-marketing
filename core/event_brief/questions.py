from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = (
    "metadata.title",
    "metadata.date",
    "audience.primary_persona",
    "value_prop.primary_hook",
    "cta_primary",
)


def find_missing_fields(brief: dict[str, Any]) -> list[str]:
    metadata = brief.get("metadata", {}) or {}
    audience = brief.get("audience", {}) or {}
    value_prop = brief.get("value_prop", {}) or {}

    values = {
        "metadata.title": metadata.get("title"),
        "metadata.date": metadata.get("date"),
        "audience.primary_persona": audience.get("primary_persona"),
        "value_prop.primary_hook": value_prop.get("primary_hook"),
        "cta_primary": brief.get("cta_primary"),
    }

    return [
        field
        for field in REQUIRED_FIELDS
        if values[field] in (None, "", [])
    ]


def build_questions(missing_fields: list[str]) -> list[str]:
    questions = {
        "metadata.title": "What is the event title?",
        "metadata.date": "What is the event date?",
        "audience.primary_persona": "Who is the primary audience persona?",
        "value_prop.primary_hook": "What is the primary value proposition or hook?",
        "cta_primary": "What is the primary CTA?",
    }

    return [questions[field] for field in missing_fields]

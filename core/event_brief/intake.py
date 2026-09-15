from __future__ import annotations

from typing import Any
from importlib import import_module

from .questions import build_questions, find_missing_fields


def process_event_brief(brief_data: dict[str, Any]) -> dict[str, Any]:
    brief = brief_data or {}

    source = brief.get("source") or {}
    if source.get("type") == "66degrees":
        normalize_event = import_module(
            "core.event_brief.66degrees"
        ).normalize_event
        brief = normalize_event(brief)

    missing = find_missing_fields(brief)

    return {
        "status": "NEEDS_CLARIFICATION" if missing else "READY_FOR_GENERATION",
        "missing_fields": missing,
        "brief": brief,
        "questions": build_questions(missing),
    }

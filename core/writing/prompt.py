"""Build compact writing-guideline prompt blocks for LLM / scaffold context."""
from __future__ import annotations

from typing import Any

from .loader import get_guideline_version, load_guidelines
from .skills import doc_ids_for_skills, select_skills

# Soft per-doc character budget so we never dump the whole KB into a prompt.
_DOC_CHAR_BUDGET = 1800
_TOTAL_CHAR_BUDGET = 9000


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n…[truncated]"


def build_writing_prompt(
    asset_type: str | None = None,
    *,
    brief_data: dict[str, Any] | None = None,
    mode: str = "generate",
    skills: list[str] | None = None,
) -> dict[str, Any]:
    """Return prompt metadata: skills, version, and a compact markdown block.

    If guidelines cannot be loaded, ``available`` is False and callers must not
    claim compliance.
    """
    selected = skills or select_skills(asset_type, brief_data=brief_data, mode=mode)
    version = get_guideline_version()
    guidelines = load_guidelines()
    if not guidelines:
        return {
            "available": False,
            "guideline_version": version,
            "applicable_skills": selected,
            "doc_ids": [],
            "prompt_block": (
                "WRITING GUIDELINES UNAVAILABLE. Do not claim guideline compliance. "
                "Fail closed on brand-critical claims; ask for human review."
            ),
        }

    doc_ids = doc_ids_for_skills(selected)
    # Prefer mandatory docs first; drop craft if over budget.
    priority = [
        "company_facts",
        "messaging",
        "brand_voice",
        "grammar",
        "prohibited",
        "specs",
        "structure",
        "social_email",
        "proof",
        "audience",
        "checklist",
        "ceo_voice",
        "reader_journey",
        "craft",
    ]
    ordered = [d for d in priority if d in doc_ids] + [d for d in doc_ids if d not in priority]

    parts: list[str] = [
        f"66DEGREES WRITING GUIDELINES (version {version})",
        f"Applicable skills: {', '.join(selected)}",
        "Follow these rules. Company facts and messaging bans override craft tips.",
        "Do not invent statistics, client names, logistics, or social proof.",
        "Writing compliance is not human approval.",
        "",
    ]
    used = sum(len(p) for p in parts)
    included: list[str] = []
    for doc_id in ordered:
        body = guidelines.get(doc_id)
        if not body:
            continue
        chunk = f"### {doc_id}\n{_clip(body, _DOC_CHAR_BUDGET)}"
        if used + len(chunk) > _TOTAL_CHAR_BUDGET:
            if doc_id in {"craft", "reader_journey"}:
                continue
            break
        parts.append(chunk)
        parts.append("")
        used += len(chunk)
        included.append(doc_id)

    return {
        "available": True,
        "guideline_version": version,
        "applicable_skills": selected,
        "doc_ids": included,
        "prompt_block": "\n".join(parts).strip(),
    }

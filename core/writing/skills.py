"""Writing skill identifiers and selection by asset type / brief."""
from __future__ import annotations

from typing import Any

# Skill A–G from the integration brief, plus CEO voice as a channel skill.
SKILL_IDS = (
    "brand_voice",
    "audience_messaging",
    "content_generation",
    "content_optimization",
    "content_qa",
    "channel_adaptation",
    "pre_publication_review",
    "ceo_voice",
)

# Which guideline docs each skill needs (kept small for prompt budgets).
SKILL_DOC_IDS: dict[str, tuple[str, ...]] = {
    "brand_voice": ("company_facts", "messaging", "brand_voice", "grammar", "prohibited"),
    "audience_messaging": ("audience", "messaging", "brand_voice"),
    "content_generation": (
        "company_facts",
        "messaging",
        "brand_voice",
        "grammar",
        "structure",
        "specs",
        "prohibited",
        "proof",
    ),
    "content_optimization": (
        "company_facts",
        "messaging",
        "brand_voice",
        "grammar",
        "prohibited",
        "proof",
        "checklist",
    ),
    "content_qa": ("prohibited", "grammar", "specs", "checklist", "proof"),
    "channel_adaptation": ("structure", "social_email", "specs"),
    "pre_publication_review": ("checklist", "prohibited", "specs", "company_facts"),
    "ceo_voice": ("ceo_voice", "company_facts", "proof"),
}

_LEADERSHIP_HINTS = (
    "ceo",
    "ben kessler",
    "ben's voice",
    "press",
    "forbes",
    "media",
    "executive quote",
    "leadership",
    "pr ",
    "analyst",
)

_CHANNEL_EMAIL = {"email", "event_email", "invite", "invite_email", "newsletter"}
_CHANNEL_SOCIAL = {"linkedin_post", "social", "linkedin", "social_post"}
_CHANNEL_ADS = {"google_ads", "linkedin_ads", "ads"}
_CHANNEL_LANDING = {"landing_page", "event_landing_page", "registration", "reg_page"}


def _normalize_asset_type(asset_type: str | None) -> str:
    return (asset_type or "").strip().lower().replace("-", "_").replace(" ", "_")


def _brief_text(brief_data: dict[str, Any] | None) -> str:
    if not brief_data:
        return ""
    parts: list[str] = []
    for key in ("voice", "tone", "mode", "purpose", "asset_type"):
        val = brief_data.get(key)
        if val:
            parts.append(str(val))
    meta = brief_data.get("metadata") or {}
    for key in ("title", "voice", "channel", "format"):
        if meta.get(key):
            parts.append(str(meta[key]))
    return " ".join(parts).lower()


def select_skills(
    asset_type: str | None = None,
    *,
    brief_data: dict[str, Any] | None = None,
    mode: str = "generate",
) -> list[str]:
    """Return ordered skill ids applicable to this request."""
    skills: list[str] = ["brand_voice", "audience_messaging"]
    normalized = _normalize_asset_type(asset_type)
    mode_l = (mode or "generate").lower()

    if mode_l in {"generate", "repurpose", "strategy"}:
        skills.append("content_generation")
    if mode_l in {"optimize", "refine", "rewrite"}:
        skills.append("content_optimization")
    if mode_l in {"qa", "validate", "review", "generate", "optimize", "refine"}:
        skills.append("content_qa")
    if mode_l in {"qa", "validate", "review", "pre_publish"}:
        skills.append("pre_publication_review")

    if normalized in _CHANNEL_EMAIL | _CHANNEL_SOCIAL | _CHANNEL_ADS | _CHANNEL_LANDING:
        skills.append("channel_adaptation")
    elif normalized in {
        "blog",
        "case_study",
        "whitepaper",
        "thought_leadership",
        "website",
        "video_script",
        "campaign_kit",
    }:
        skills.append("channel_adaptation")

    text = _brief_text(brief_data)
    if any(h in text for h in _LEADERSHIP_HINTS) or normalized in {
        "thought_leadership",
        "press",
        "executive",
    }:
        skills.append("ceo_voice")

    # Preserve order, unique
    seen: set[str] = set()
    ordered: list[str] = []
    for skill in skills:
        if skill not in seen and skill in SKILL_IDS:
            seen.add(skill)
            ordered.append(skill)
    return ordered


def doc_ids_for_skills(skills: list[str]) -> list[str]:
    """Union of guideline doc ids for the selected skills, stable order."""
    seen: set[str] = set()
    docs: list[str] = []
    for skill in skills:
        for doc_id in SKILL_DOC_IDS.get(skill, ()):
            if doc_id not in seen:
                seen.add(doc_id)
                docs.append(doc_id)
    return docs

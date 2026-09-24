"""Normalize marketing briefs into internal event/campaign shapes."""
from __future__ import annotations

from typing import Any

from .models import CampaignBrief


REQUIRED_BRIEF_FIELDS = ("campaign_name", "objective")


def validate_marketing_brief(raw: dict[str, Any] | None) -> CampaignBrief:
    data = dict(raw or {})
    missing = [field for field in REQUIRED_BRIEF_FIELDS if not str(data.get(field) or "").strip()]
    if missing:
        raise ValueError(
            "Invalid campaign brief. Missing required fields: "
            + ", ".join(missing)
            + '. Provide at least {"campaign_name": "...", "objective": "..."}.'
        )
    return CampaignBrief.model_validate(data)


def brief_to_event_shape(brief: CampaignBrief) -> dict[str, Any]:
    """Map a marketing brief into the shape expected by campaign kit generators."""
    audience = brief.audience
    if isinstance(audience, str):
        audience_obj = {"primary_persona": audience, "industry_verticals": ["Enterprise"]}
    else:
        audience_obj = dict(audience)

    messages = list(brief.key_messages) or [brief.objective]
    return {
        "metadata": {
            "title": brief.campaign_name,
            "date": brief.deadline or "2026-12-31",
            "campaign_type": brief.campaign_type,
        },
        "audience": audience_obj,
        "value_prop": {
            "primary_hook": brief.objective,
            "key_takeaways": messages,
            "offer": brief.offer,
        },
        "cta_primary": brief.offer or "Register",
        "channels": brief.channels,
        "source": {"type": "66degrees"},
    }

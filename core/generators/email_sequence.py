"""Deterministic event-lifecycle email generation.

The sequence is the shared 66degrees brand model, the general email OKF profile,
the Event Email OKF procedural rules, and the lifecycle facts in the brief.
Approved campaign copy in docs/email-content.json is a reference fixture, not a template
that this generator copies.
"""

from __future__ import annotations

import re
from typing import Any

from core.brand.rules import load_brand_rules
from core.okf.event_email import (
    BRAND_RULES,
    CONCEPT_TYPE,
    EMAIL_CONTENT_JSON,
    EMAIL_GUIDELINE,
    EVENT_EMAIL_DOCX,
    EVENT_EMAIL_STAGES,
    EventEmailStage,
    generation_body_bounds,
    load_email_content,
    validate_event_email_asset,
    word_count,
)
from core.okf.model import get_okf_model

_SUBJECTS = {
    "invitation_1": ("Strategic briefing on {event}", "Strategic briefing with the 66degrees team"),
    "invitation_2": ("Technical briefing on {event}", "Technical context for peers and practitioners"),
    "invitation_3": ("Final registration window: {event}", "Final registration window for this session"),
    "reminder_1": ("Logistics guidance for {event}", "Logistics for your session in two days"),
    "reminder_2": ("Today logistics for {event}", "Day-of logistics for your session today"),
    "attendee_followup": ("Thank you for attending {event}", "Thank you for joining the 66degrees session"),
    "non_attendee_followup": ("A later path after {event}", "A note after the recent 66degrees session"),
}

_PREVIEWS = {
    "invitation_1": "Business value and event context for this 66degrees session.",
    "invitation_2": "A deeper technical discussion for peers evaluating this problem.",
    "invitation_3": "The final registration window is open for this session.",
    "reminder_1": "Arrival and logistics guidance about 48 hours before the session.",
    "reminder_2": "Today's arrival, check-in, and onsite logistics.",
    "attendee_followup": "Thank you for attending. Share feedback and an optional next step.",
    "non_attendee_followup": "A note for those who could not attend, with a future path.",
}

_FILLERS = {
    "invitation_1": (
        "The opening stays on business value and on why this event belongs on the calendar.",
    ),
    "invitation_2": (
        "The technical context stays on the problem and the constraints named for the session.",
    ),
    "invitation_3": (
        "Please treat this as the final registration window, stated plainly.",
    ),
    "reminder_1": (
        "Read the logistics once before you travel and keep them available offline.",
    ),
    "reminder_2": (
        "Read this once at the door and then follow the onsite contact.",
    ),
    "attendee_followup": (
        "Thank you again for the time you spent in the room.",
    ),
    "non_attendee_followup": (
        "The future path stays open without a penalty for missing this date.",
    ),
}


def generate_event_email_sequence(brief_data: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Return the seven lifecycle assets keyed by stage."""
    brief = brief_data or {}
    facts = _facts(brief)
    sequence: dict[str, dict[str, Any]] = {}
    for stage in EVENT_EMAIL_STAGES:
        sequence[stage.key] = _asset(stage, facts)
    return sequence


def generate_event_email_lifecycle(brief_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Ordered seven-asset lifecycle used by the campaign kit."""
    sequence = generate_event_email_sequence(brief_data)
    return [sequence[stage.key] for stage in EVENT_EMAIL_STAGES]


def _facts(brief: dict[str, Any]) -> dict[str, Any]:
    model = get_okf_model()
    brand = load_brand_rules()
    metadata = brief.get("metadata") or {}
    audience = brief.get("audience") or {}
    value_prop = brief.get("value_prop") or {}
    logistics = brief.get("logistics") or {}
    verticals = audience.get("industry_verticals") or []
    industry = verticals[0] if verticals else "[INDUSTRY]"
    takeaways = [str(item).strip() for item in (value_prop.get("key_takeaways") or []) if str(item).strip()]
    partner = "Google Cloud Premier Partner"
    if partner not in brand.mandatory_terminology:
        partner = str(load_email_partner())
    resource = _first(
        brief.get("resource"),
        metadata.get("resource"),
        metadata.get("url"),
        default="[LINK]",
    )
    return {
        "company": str(model.common_brand.get("company_name") or "66degrees"),
        "partner": partner,
        "event": _first(metadata.get("title"), default="[EVENT]"),
        "persona": _first(audience.get("primary_persona"), default="executive"),
        "industry": industry,
        "hook": _first(value_prop.get("primary_hook"), default="the priority named for this event"),
        "takeaway": " and ".join(takeaways[:2]),
        "date": _first(logistics.get("event_date"), metadata.get("event_date"), metadata.get("date"), default="[DATE]"),
        "venue": _first(logistics.get("venue"), metadata.get("venue"), default="[VENUE]"),
        "location": _first(logistics.get("location"), metadata.get("location"), default=""),
        "start": _first(logistics.get("start_time"), metadata.get("start_time"), default="[TIME]"),
        "contact": _first(logistics.get("onsite_contact"), metadata.get("onsite_contact"), default="[CONTACT]"),
        "cta": _cta(brief.get("cta_primary") or brief.get("cta") or "Register"),
        "resource": resource,
        "tags": list(brief.get("tags") or metadata.get("tags") or []),
        "brief": brief,
        "brand_source": BRAND_RULES,
        "email_profile": model.profiles["email"].source_filename,
    }


def load_email_partner() -> str:
    return str(
        load_email_content()["global_brand_guidelines"].get("primary_cloud_partner") or "Google Cloud"
    )


def _asset(stage: EventEmailStage, facts: dict[str, Any]) -> dict[str, Any]:
    subject = _subject(stage.key, facts["event"])
    preview = _PREVIEWS[stage.key]
    body = _body(stage, facts)
    asset = {
        "type": CONCEPT_TYPE,
        "lifecycle_stage": stage.key,
        "stage": stage.label,
        "sequence_number": stage.sequence_number,
        "sub_type": stage.sub_type,
        "subject": subject,
        "preview_text": preview,
        "body": body,
        "cta": f"[{facts['cta']}]",
        "status": "draft",
        "verified": [],
        "sources": _sources(),
        "resource": facts["resource"],
        "tags": facts["tags"],
        "intent": list(stage.intent),
        "rhetorical_style": stage.rhetorical_style,
        "conversion_objective": stage.conversion_objective,
        "provenance": {
            "procedural_source": EVENT_EMAIL_DOCX,
            "campaign_source": EMAIL_CONTENT_JSON,
            "email_okf_profile": EMAIL_GUIDELINE,
            "loaded_email_profile": facts["email_profile"],
            "brand_model": facts["brand_source"],
            "status": "draft",
            "verified": [],
            "approval_note": "Formatting validation does not set status to approved or active.",
            "placeholders": _placeholders(body),
        },
    }
    asset["validation"] = validate_event_email_asset(asset)
    asset["metrics"] = asset["validation"]["metrics"]
    return asset


def _sources() -> list[dict[str, str]]:
    return [
        {"resource": EVENT_EMAIL_DOCX, "role": "procedural model-generation source"},
        {"resource": EMAIL_CONTENT_JSON, "role": "machine-readable lifecycle and campaign source"},
        {"resource": EMAIL_GUIDELINE, "role": "general email OKF profile"},
        {"resource": BRAND_RULES, "role": "shared 66degrees brand model"},
    ]


def _body(stage: EventEmailStage, facts: dict[str, Any]) -> str:
    required, optional = _paragraphs(stage.key, facts)
    low, high = generation_body_bounds(stage)
    paragraphs = _fit(required, optional, _FILLERS[stage.key], facts, low, high)
    return _compose(paragraphs, facts["cta"], facts["company"])


def _paragraphs(key: str, facts: dict[str, Any]) -> tuple[list[str], list[str]]:
    event = facts["event"]
    persona = facts["persona"]
    industry = facts["industry"]
    hook = facts["hook"]
    date = facts["date"]
    venue = facts["venue"]
    start = facts["start"]
    contact = facts["contact"]
    company = facts["company"]
    partner = facts["partner"]
    takeaway = facts["takeaway"]
    priority = f'"{hook}"' if takeaway or hook else hook
    if key == "invitation_1":
        closing = "Bring the priority you want to examine."
        if takeaway:
            closing = f"Bring the priority you want to examine, including {takeaway}."
        required = [
            f"The stated priority for {persona} leaders in {industry} is {priority}.",
            (
                f"{event} is relevant because it puts that priority on a defined agenda. "
                f"{company}, a {partner}, is hosting the session on {date} at {venue}."
            ),
            (
                "The business value is a clearer choice about what to fund, defer, or redesign. "
                "The conversation is consultative and direct, and it uses only the facts supplied for this event."
            ),
            f"{closing} Details: [LINK].",
        ]
    elif key == "invitation_2":
        required = [
            f'A different question follows the opening note. The operational problem around {event} is "{hook}".',
            (
                f"This invitation is for {persona} peers in {industry} who want a technical reading of that "
                "problem and the context a solution has to respect."
            ),
            (
                f"On {date} at {venue}, the session is a place to compare constraints with peers. "
                "It does not repeat the business-value opening."
            ),
            "Attend if this problem is actually on your agenda. Details: [LINK].",
            "Compare the constraint you are living with, not a generic pitch.",
        ]
    elif key == "invitation_3":
        required = [
            f"The final registration window for {event} is now the practical question.",
            f"If you plan to attend on {date} at {venue}, use the link below to confirm.",
            "This note is concise and direct. It does not restate the earlier invitations, and it does not add pressure.",
            "Confirm only if the session is still on your calendar. Details: [LINK].",
            "We will use your confirmation to prepare entry for the roster. No other claim is added here.",
        ]
    elif key == "reminder_1":
        required = [
            f"This is the logistics reminder for {event}, sent with about 48 hours of lead time.",
            f"Date: {date}. Start: {start}. Venue: {venue}. Onsite contact: {contact}.",
            "Review arrival, building access, and credential steps before you travel. Carry the confirmation on your phone.",
            "If your plans change, tell the onsite contact so the place can be released. This reminder does not repeat the invitation argument.",
            "Parking, gate, and badge rules are included only when the brief supplies them. Otherwise the placeholder stands in for the missing fact.",
            "Write down the start time and the onsite contact before you leave for the venue.",
            "Keep the operational details together. Details: [LINK].",
        ]
    elif key == "reminder_2":
        required = [
            f"Today is {event}. This day-of note is limited to immediate logistics.",
            f"Date: {date}. Start: {start}. Venue: {venue}. Onsite contact: {contact}.",
            "Have your confirmation open before you reach the door. Use the onsite contact for entry questions today.",
            "Save the start time, venue, and onsite contact where you can read them at the door.",
            "This message is meant to be read on a phone. It does not repeat the invitation. Details: [LINK].",
        ]
    elif key == "attendee_followup":
        required = [
            f"Thank you for attending {event}.",
            "The value of the session is the conversation you joined, and the priorities you chose to examine there.",
            "If you can, share brief feedback so the next session is more useful. The feedback link is optional.",
            "An optional next step is a follow-up conversation on the topics you raised. There is no obligation to take it.",
            "Your time at the session is appreciated, and the points you raised remain the useful record.",
            "Reply only if a next conversation would help. Silence is a complete response.",
            "Feedback and the optional next step: [LINK].",
        ]
    elif key == "non_attendee_followup":
        required = [
            f"You were unable to attend {event}, and that is fine.",
            "This note acknowledges the absence without pressure and keeps the relationship intact.",
            "A future path is available when the timing is better. You can also request the resource list from the session.",
            "Nothing here asks you to justify the absence.",
            "When you want it, the resource path is the same link, offered without a deadline.",
            "Use it later if the topic is still relevant to your team. Details and future sessions: [LINK].",
        ]
    else:
        raise ValueError(f"Unsupported lifecycle stage {key}")
    optional = []
    if facts["location"]:
        optional.append(f"Location: {facts['location']}.")
    return required, optional


def _fit(
    required: list[str],
    optional: list[str],
    fillers: tuple[str, ...],
    facts: dict[str, Any],
    low: int,
    high: int,
) -> list[str]:
    paragraphs = list(required)
    optional_used: list[str] = []
    for item in optional:
        paragraphs.append(item)
        optional_used.append(item)

    def total(items: list[str]) -> int:
        return word_count(_compose(items, facts["cta"], facts["company"]))

    while total(paragraphs) > high and optional_used:
        paragraphs.pop()
        optional_used.pop()
    for filler in fillers:
        if total(paragraphs) >= low:
            break
        paragraphs.append(filler)
        if total(paragraphs) > high:
            paragraphs.pop()
            break
    return paragraphs


def _compose(paragraphs: list[str], cta: str, company: str) -> str:
    blocks = [
        "Hi {{Recipient.FirstName}},",
        *paragraphs,
        f"[{cta}]",
        "Best regards,",
        f"The {company} Team",
    ]
    return "\n\n".join(blocks)


def _subject(stage_key: str, event: str) -> str:
    pattern, fallback = _SUBJECTS[stage_key]
    candidate = pattern.format(event=event)
    if _subject_ok(candidate):
        return candidate
    if _subject_ok(fallback):
        return fallback
    raise ValueError(f"No valid subject for {stage_key}")


def _subject_ok(text: str) -> bool:
    return 6 <= len(text.split()) <= 9 and 30 <= len(text) <= 50 and "!" not in text


def _cta(value: Any) -> str:
    text = str(value or "Register").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    return text or "Register"


def _first(*values: Any, default: str) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _placeholders(body: str) -> list[str]:
    return sorted(set(re.findall(r"\[[A-Z][A-Z0-9 _-]*\]|\{\{Recipient\.FirstName\}\}", body)))

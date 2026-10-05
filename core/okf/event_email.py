"""Event lifecycle email rules layered on the shared OKF email profile.

`docs/email-content.json` is the machine-readable campaign source.
`docs/Event Email OKF Model Generation.docx` is the procedural source.
The human-readable procedure is `references/event-email-okf-model-generation.md`.

This module does not replace `references/66degrees_email_content_writing_guideline.json`
and it does not change `validate_okf_content("email")`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.okf.model import get_okf_profile

REPO_ROOT = Path(__file__).resolve().parents[2]
EMAIL_CONTENT_JSON = "docs/email-content.json"
EVENT_EMAIL_DOCX = "docs/Event Email OKF Model Generation.docx"
EVENT_EMAIL_REFERENCE = "references/event-email-okf-model-generation.md"
EMAIL_GUIDELINE = "references/66degrees_email_content_writing_guideline.json"
BRAND_RULES = "core/brand/brand_rules.json"

CONCEPT_TYPE = "Lifecycle Email Campaign"
STATUSES = ("draft", "approved", "active")
DOCX_ONLY_STAGE = "Registration Confirmation"

# DOCX engineering sentence: subject lines are 30-50 characters and 6-9 words.
DOCX_SUBJECT_CHARS = (30, 50)
DOCX_SUBJECT_WORDS = (6, 9)
# DOCX CI paragraph: body copy is 45-215 words.
DOCX_BODY_WORDS = (45, 215)
# DOCX prose, not the citation-concatenated table cells: observed body bounds.
DOCX_EMPIRICAL_BODY_WORDS = (45, 212)
# DOCX risk sentence. This is not the acceptance cap.
DOCX_BODY_RISK_WORDS = 220
# DOCX empirical table cells for subject characters are 22 and 64 (no concatenated citation).
DOCX_EMPIRICAL_SUBJECT_CHARS = (22, 64)

# DOCX substitution table. The approved replacement is recorded and not treated as spam.
DOCX_DISCOURAGED_PHRASES = (
    ("exclusive 66degrees swag", "Executive resources and follow-up discussion"),
    ("raffle", "To express our appreciation for your feedback"),
    ("save your spot", "Confirm your attendance"),
    ("seats limited", "Register your team"),
    ("final invitation", "Upcoming session briefing"),
    ("last chance", "Final registration window"),
    ("complimentary hosted bar and free drinks", "Complimentary suite hospitality and catering"),
)

# The DOCX forbids public URL shorteners and does not name hosts.
# These hosts implement that sentence; they are not an additional policy.
DOCX_SHORTENER_HOSTS = (
    "bit.ly",
    "bitly.com",
    "tinyurl.com",
    "tiny.cc",
    "t.co",
    "goo.gl",
    "ow.ly",
    "buff.ly",
)

DOCX_OPERATIONAL_REQUIREMENTS = (
    "SPF records matching the outbound IP address",
    "DKIM signatures using 2048-bit keys",
    "DMARC policy advancing from monitoring toward quarantine or rejection",
    "Complaint rate strictly below 0.1% and never exceeding 0.3%",
    "Functional List-Unsubscribe headers with one-click removal within two days",
    "No more than two functional URLs",
    "No public URL shorteners",
)

_URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)
_STANDALONE_CTA_RE = re.compile(r"^\[[^\]\n]+\]$")
_CAPS_RE = re.compile(r"\b[A-Z]{4,}\b")
_CURRENCY_RE = re.compile(r"[$€£]")
_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?\s*%")


class EventEmailSourceError(ValueError):
    """An event-email source file is missing or does not match the expected shape."""


@dataclass(frozen=True)
class EventEmailStage:
    key: str
    label: str
    sequence_number: int
    group: str
    sub_type: str
    intent: tuple[str, ...]
    typical_body_words: tuple[int, int]
    rhetorical_style: str
    conversion_objective: str


EVENT_EMAIL_STAGES: tuple[EventEmailStage, ...] = (
    EventEmailStage(
        key="invitation_1",
        label="Invitation #1",
        sequence_number=1,
        group="invitations",
        sub_type="Invitation #1",
        intent=(
            "strategic and contextual opening",
            "business value",
            "event relevance",
        ),
        typical_body_words=(95, 130),
        rhetorical_style="Strategic, thesis-led, consultative",
        conversion_objective="Establish business challenge and value proposition",
    ),
    EventEmailStage(
        key="invitation_2",
        label="Invitation #2",
        sequence_number=2,
        group="invitations",
        sub_type="Invitation #2",
        intent=(
            "deeper technical and peer relevance",
            "problem, solution context",
            "stronger audience qualification",
        ),
        typical_body_words=(90, 115),
        rhetorical_style="Technical, peer-oriented, focused",
        conversion_objective="Validate architecture context or peer relevance",
    ),
    EventEmailStage(
        key="invitation_3",
        label="Invitation #3",
        sequence_number=3,
        group="invitations",
        sub_type="Invitation #3",
        intent=(
            "final registration window",
            "concise",
            "direct and professional",
            "avoid spam-style urgency",
        ),
        typical_body_words=(75, 100),
        rhetorical_style="Direct, scheduling-focused, polite",
        conversion_objective="Secure confirmation prior to roster closure",
    ),
    EventEmailStage(
        key="reminder_1",
        label="Reminder #1",
        sequence_number=1,
        group="reminders",
        sub_type="Pre-Event Reminder (48 Hours)",
        intent=(
            "pre-event operational and logistics guidance",
            "about 48 hours before the event where applicable",
        ),
        typical_body_words=(110, 150),
        rhetorical_style="Instructional, thorough, clear",
        conversion_objective="Transmit venue access, schedule, and credential data",
    ),
    EventEmailStage(
        key="reminder_2",
        label="Reminder #2",
        sequence_number=2,
        group="reminders",
        sub_type="Pre-Event Reminder (Day-Of)",
        intent=(
            "day-of communication",
            "concise",
            "mobile-friendly",
            "immediate logistics",
        ),
        typical_body_words=(45, 95),
        rhetorical_style="Brief, mobile-optimized, direct",
        conversion_objective="Direct attendees to check-in and the onsite host",
    ),
    EventEmailStage(
        key="attendee_followup",
        label="Attendee Follow-Up",
        sequence_number=1,
        group="follow_ups",
        sub_type="Post-Event Attendee Follow-Up",
        intent=(
            "thank the attendee",
            "reinforce event value",
            "solicit feedback",
            "optional next step",
        ),
        typical_body_words=(100, 140),
        rhetorical_style="Appreciative, reflective, actionable",
        conversion_objective="Prompt feedback and offer an optional advisory follow-up",
    ),
    EventEmailStage(
        key="non_attendee_followup",
        label="Non-Attendee Follow-Up",
        sequence_number=2,
        group="follow_ups",
        sub_type="Post-Event Non-Attendee Follow-Up",
        intent=(
            "acknowledge absence",
            "no guilt or pressure",
            "preserve the relationship",
            "future or resource path",
        ),
        typical_body_words=(75, 115),
        rhetorical_style="Low-pressure, forward-looking, open",
        conversion_objective="Maintain the relationship and point to a future path",
    ),
)

EVENT_EMAIL_STAGE_KEYS: tuple[str, ...] = tuple(stage.key for stage in EVENT_EMAIL_STAGES)
_STAGE_BY_KEY = {stage.key: stage for stage in EVENT_EMAIL_STAGES}


def repo_path(relative: str) -> Path:
    return REPO_ROOT / relative


def word_count(text: str) -> int:
    return len(str(text or "").split())


def stage_by_key(key: str) -> EventEmailStage:
    try:
        return _STAGE_BY_KEY[key]
    except KeyError as exc:
        allowed = ", ".join(EVENT_EMAIL_STAGE_KEYS)
        raise EventEmailSourceError(f"Unknown lifecycle stage '{key}'. Use one of: {allowed}.") from exc


@lru_cache(maxsize=1)
def load_email_content() -> dict[str, Any]:
    path = repo_path(EMAIL_CONTENT_JSON)
    if not path.is_file():
        raise EventEmailSourceError(f"Missing event email source: {EMAIL_CONTENT_JSON}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EventEmailSourceError(f"Invalid JSON in {EMAIL_CONTENT_JSON}") from exc
    if not isinstance(data, dict):
        raise EventEmailSourceError(f"{EMAIL_CONTENT_JSON} must be a JSON object")
    benchmarks = (
        data.get("global_brand_guidelines", {})
        .get("word_count_benchmarks", {})
    )
    required = (
        "subject_line_max_words",
        "subject_line_character_range",
        "preview_text_max_words",
        "body_copy_min_words",
        "body_copy_max_words",
    )
    missing = [key for key in required if key not in benchmarks]
    if missing:
        raise EventEmailSourceError(f"{EMAIL_CONTENT_JSON} is missing benchmarks: {missing}")
    return data


def docx_source_present() -> bool:
    return repo_path(EVENT_EMAIL_DOCX).is_file()


def reference_markdown() -> str:
    path = repo_path(EVENT_EMAIL_REFERENCE)
    if not path.is_file():
        raise EventEmailSourceError(f"Missing event email reference: {EVENT_EMAIL_REFERENCE}")
    return path.read_text(encoding="utf-8")


def json_benchmarks() -> dict[str, Any]:
    return load_email_content()["global_brand_guidelines"]["word_count_benchmarks"]


def json_deliverability() -> dict[str, Any]:
    return load_email_content()["global_brand_guidelines"]["deliverability_rules"]


def parse_character_range(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", str(value))
    if not match:
        raise EventEmailSourceError(f"Unrecognized character range: {value!r}")
    return int(match.group(1)), int(match.group(2))


def source_conflicts() -> list[dict[str, Any]]:
    """Conflicts left unresolved for human review. Nothing here picks a winner."""
    benchmarks = json_benchmarks()
    subject_range = benchmarks["subject_line_character_range"]
    return [
        {
            "id": "subject_character_range",
            "status": "unresolved",
            "field": "subject",
            "email_content_json": (
                f"word_count_benchmarks.subject_line_character_range = {subject_range}"
            ),
            "docx": (
                "Engineering sentence: subject lines are engineered between 30 and 50 "
                "characters. Empirical table: subject characters minimum 22, maximum 64, "
                "mean 43.1, median 44.0. Approved examples in email-content.json include "
                "subjects longer than 50 characters."
            ),
            "email_guideline": "structure_and_components.subject_line.char_limit = 30-50 characters",
            "not_chosen": (
                "Generated subjects target the shared stated range of 30-50 characters. "
                "The empirical 22-64 observation and the longer approved examples stay "
                "in place and are not rewritten."
            ),
        },
        {
            "id": "subject_word_count",
            "status": "unresolved",
            "field": "subject",
            "email_content_json": (
                f"subject_line_max_words = {benchmarks['subject_line_max_words']}; "
                "no minimum is stated"
            ),
            "docx": (
                "CI validation paragraph: subject line lengths fall strictly within "
                "6 to 9 words. The empirical subject-word table cells extract as 48 and 98 "
                "because a citation marker is concatenated; mean 6.98 makes those cells "
                "unusable, so they are not thresholds."
            ),
            "not_chosen": (
                "A subject of 5 words fails the DOCX rule and passes the JSON maximum. "
                "A subject of 10 words fails both. Both results are reported."
            ),
        },
        {
            "id": "body_word_count",
            "status": "unresolved",
            "field": "body",
            "email_content_json": (
                f"body_copy_min_words = {benchmarks['body_copy_min_words']}, "
                f"body_copy_max_words = {benchmarks['body_copy_max_words']}, "
                f"body_copy_mean_target = {benchmarks.get('body_copy_mean_target')}"
            ),
            "docx": (
                "CI paragraph: body copy range is 45 to 215 words. Prose empirical bounds "
                "are 45 words (San Diego Padres day-of reminder) and 212 words (Detroit "
                "Tigers day-of reminder). A separate risk sentence says copy that exceeds "
                "220 words risks mobile truncation. Extracted table cells 458 and 2128 "
                "concatenate a citation marker and are not thresholds."
            ),
            "not_chosen": (
                "JSON and the DOCX CI paragraph agree on 45-215. The empirical maximum "
                "of 212 and the 220-word risk line are reported beside that cap. "
                "A body of 213-215 words passes 45-215 and exceeds the observed 212."
            ),
        },
        {
            "id": "preview_word_count",
            "status": "unresolved",
            "field": "preview_text",
            "email_content_json": (
                f"preview_text_max_words = {benchmarks['preview_text_max_words']}"
            ),
            "docx": (
                "The CI paragraph does not state a preview-word cap. Empirical preview "
                "table cells extract as 28 and 148, with mean 7.88 and median 8.0. "
                "Those cells are not used as a reconstructed minimum or maximum."
            ),
            "not_chosen": (
                "The validator enforces the explicit JSON maximum of 12 preview words. "
                "It does not enforce a guessed empirical preview cap."
            ),
        },
        {
            "id": "lifecycle_length",
            "status": "unresolved",
            "field": "sequence",
            "email_content_json": (
                "Each approved concept has 3 invitations, 2 reminders, and 2 follow-ups. "
                "Registration confirmation is not a template."
            ),
            "docx": (
                "The sequence introduction says each sequence contains seven fully scripted "
                "emails. The stage table and the narrative examples also include "
                "Registration Confirmation, which would be an eighth email."
            ),
            "not_chosen": (
                "generate_event_email_sequence emits the seven-asset lifecycle and does "
                "not emit Registration Confirmation. The eighth DOCX stage remains documented."
            ),
        },
        {
            "id": "general_email_profile_vs_event_lifecycle",
            "status": "unresolved",
            "field": "body_and_preview",
            "email_guideline": (
                "Primary cold/promotional emails: 75-200 words. Preheader: 40-100 "
                "characters. Required profile fields include a separate opening."
            ),
            "email_content_json": "Body 45-215 words. Preview maximum 12 words. No character cap is stated.",
            "docx": "Body 45-215 words. Day-of typical band is 45-95 words. One body field, not a separate opening.",
            "not_chosen": (
                "validate_okf_content('email') still uses the guideline profile. "
                "Event validation reports the guideline and the event bounds separately. "
                "Generation aims at the overlap where one exists, including day-of copy "
                "at or above 75 words, and still records that the DOCX day-of band starts at 45."
            ),
        },
        {
            "id": "sign_off_shape",
            "status": "unresolved",
            "field": "sign_off",
            "email_guideline": (
                "Professional sign-off with full name, role, 66degrees contact details, "
                "and a link to resources."
            ),
            "email_content_json": 'Approved templates sign off as "Best regards," / "The 66degrees Team".',
            "docx": "Narrative examples use the same 66degrees team sign-off and do not name a sender.",
            "not_chosen": (
                "Generated mail uses the event-source sign-off. A personal name, role, "
                "or phone number is not invented to satisfy the general guideline."
            ),
        },
        {
            "id": "non_attendee_regret_phrasing",
            "status": "unresolved",
            "field": "non_attendee_followup",
            "docx": "Non-attendee style is low-pressure, forward-looking, and open.",
            "email_content_json": (
                'The Irvine non-attendee template says "We regret that you were unable '
                'to join". The Giants non-attendee template says "We missed connecting with you".'
            ),
            "not_chosen": (
                "Those sentences stay in the approved examples. New non-attendee copy "
                "acknowledges absence without regret, guilt, or pressure."
            ),
        },
        {
            "id": "stored_metrics_vs_whitespace_count",
            "status": "unresolved",
            "field": "metrics",
            "email_content_json": (
                "Template metrics.subject_word_count and metrics.body_word_count do not "
                "always equal a whitespace split of the same subject and body."
            ),
            "docx": "The DOCX repeats the same template payload and the same stored metrics.",
            "not_chosen": (
                "The validator counts generated and stored copy with a whitespace split "
                "and preserves the stored metrics unchanged. It does not rewrite either source."
            ),
        },
        {
            "id": "metrics_and_unsupported_claims",
            "status": "unresolved",
            "field": "claims",
            "email_guideline": "Dos include referencing real metrics and success stories from 66degrees case studies.",
            "brand_rules": "Deterministic governance checks only. Do not invent unofficial brand claims.",
            "not_chosen": (
                "Generation copies a number or metric only when that number is already "
                "in the brief. It does not borrow campaign statistics from the approved examples."
            ),
        },
    ]


def conflict_ids() -> tuple[str, ...]:
    return tuple(item["id"] for item in source_conflicts())


def generation_body_bounds(stage: EventEmailStage) -> tuple[int, int]:
    """Overlap of the DOCX typical band and the general email profile, when one exists."""
    profile = get_okf_profile("email")
    guide_min = int(profile.validation["word_count"]["min"])
    guide_max = int(profile.validation["word_count"]["max"])
    low, high = stage.typical_body_words
    overlap_low = max(low, guide_min)
    overlap_high = min(high, guide_max)
    if overlap_low > overlap_high:
        return low, high
    return overlap_low, overlap_high


def lifecycle_assets_from_concept(concept: dict[str, Any]) -> dict[str, dict[str, Any]]:
    templates = concept.get("email_templates") or {}
    invitations = list(templates.get("invitations") or [])
    reminders = list(templates.get("reminders") or [])
    follow_ups = list(templates.get("follow_ups") or [])
    if len(invitations) != 3 or len(reminders) != 2 or len(follow_ups) != 2:
        raise EventEmailSourceError(
            f"Concept {concept.get('id')} does not contain 3 invitations, 2 reminders, and 2 follow-ups."
        )
    mapped: dict[str, dict[str, Any]] = {}
    for stage, asset in zip(EVENT_EMAIL_STAGES[:3], invitations, strict=True):
        mapped[stage.key] = _tagged(stage, asset)
    for stage, asset in zip(EVENT_EMAIL_STAGES[3:5], reminders, strict=True):
        mapped[stage.key] = _tagged(stage, asset)
    attendee = _follow_up(follow_ups, non_attendee=False)
    absent = _follow_up(follow_ups, non_attendee=True)
    mapped["attendee_followup"] = _tagged(stage_by_key("attendee_followup"), attendee)
    mapped["non_attendee_followup"] = _tagged(stage_by_key("non_attendee_followup"), absent)
    return mapped


def validate_event_email_concept(concept: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []
    checks: list[dict[str, Any]] = []
    required = ("type", "title", "description", "sources", "verified", "status")
    for key in required:
        present = key in concept and concept.get(key) not in (None, "", [])
        if key == "verified" and concept.get("status") == "draft":
            present = isinstance(concept.get("verified"), list)
        checks.append(_check("docx-governance", f"required:{key}", present, key))
        if not present:
            violations.append(f"Missing required concept field '{key}'")
    type_ok = concept.get("type") == CONCEPT_TYPE
    checks.append(_check("docx-frontmatter", "type", type_ok, concept.get("type")))
    if not type_ok:
        violations.append(f"type must be {CONCEPT_TYPE!r}")
    status = concept.get("status")
    status_ok = status in STATUSES
    checks.append(_check("docx-frontmatter", "status", status_ok, status))
    if not status_ok:
        violations.append("status must be draft, approved, or active")
    verified = concept.get("verified")
    verified_ok = isinstance(verified, list)
    needs_signoff = status in {"approved", "active"}
    signoff_ok = verified_ok and (not needs_signoff or len(verified) > 0)
    checks.append(_check("docx-governance", "verified_when_executable", signoff_ok, verified))
    if needs_signoff and not signoff_ok:
        violations.append("approved or active concepts require a non-empty verified list")
    try:
        assets = lifecycle_assets_from_concept(concept)
        sequence_ok = list(assets) == list(EVENT_EMAIL_STAGE_KEYS)
    except EventEmailSourceError as exc:
        assets = {}
        sequence_ok = False
        violations.append(str(exc))
    checks.append(_check("email-content.json", "seven_asset_lifecycle", sequence_ok, list(assets)))
    if not sequence_ok and assets:
        violations.append("Lifecycle mapping did not produce the seven stages in order")
    return {
        "formatting_valid": not violations,
        "grants_approval": False,
        "status": status,
        "violations": violations,
        "checks": checks,
        "source_conflicts": source_conflicts(),
        "assets": list(assets),
    }


def validate_event_email_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Report every source check. Formatting success does not approve the asset."""
    profile = get_okf_profile("email")
    benchmarks = json_benchmarks()
    deliverability = json_deliverability()
    subject = str(asset.get("subject") or "")
    preview = str(asset.get("preview_text") or asset.get("preheader") or "")
    body = str(asset.get("body") or "")
    cta = asset.get("cta")
    stage_key = asset.get("lifecycle_stage")
    status = asset.get("status", "draft")
    violations: list[str] = []
    checks: list[dict[str, Any]] = []
    triggered: list[str] = []

    for field, value in (
        ("lifecycle_stage", stage_key),
        ("subject", subject),
        ("preview_text", preview),
        ("body", body),
    ):
        ok = bool(value)
        checks.append(_check("event-email", f"required:{field}", ok, field))
        if not ok:
            violations.append(f"Missing {field}")

    stage_ok = stage_key in _STAGE_BY_KEY
    checks.append(_check("event-email", "lifecycle_stage", stage_ok, stage_key))
    if stage_key and not stage_ok:
        violations.append(f"Unknown lifecycle_stage {stage_key!r}")

    subject_words = word_count(subject)
    subject_chars = len(subject)
    json_max_words = int(benchmarks["subject_line_max_words"])
    json_chars = parse_character_range(str(benchmarks["subject_line_character_range"]))
    json_words_ok = subject_words <= json_max_words
    docx_words_ok = DOCX_SUBJECT_WORDS[0] <= subject_words <= DOCX_SUBJECT_WORDS[1]
    stated_chars_ok = json_chars[0] <= subject_chars <= json_chars[1] and (
        DOCX_SUBJECT_CHARS[0] <= subject_chars <= DOCX_SUBJECT_CHARS[1]
    )
    empirical_chars_ok = (
        DOCX_EMPIRICAL_SUBJECT_CHARS[0] <= subject_chars <= DOCX_EMPIRICAL_SUBJECT_CHARS[1]
    )
    checks.append(_check("docs/email-content.json", "subject_line_max_words", json_words_ok, subject_words))
    checks.append(_check("docx-ci", "subject_words_6_to_9", docx_words_ok, subject_words))
    checks.append(_check("json-and-docx-engineering", "subject_characters_30_to_50", stated_chars_ok, subject_chars))
    checks.append(_check("docx-empirical", "subject_characters_22_to_64", empirical_chars_ok, subject_chars))
    if not json_words_ok and not docx_words_ok:
        violations.append(f"Subject has {subject_words} words; both sources reject a count above 9")
    elif json_words_ok != docx_words_ok:
        triggered.append("subject_word_count")
    if not stated_chars_ok:
        violations.append(f"Subject has {subject_chars} characters; JSON and DOCX engineering range is 30-50")
    if stated_chars_ok != empirical_chars_ok:
        triggered.append("subject_character_range")

    preview_words = word_count(preview)
    preview_chars = len(preview)
    preview_max = int(benchmarks["preview_text_max_words"])
    preview_ok = preview_words <= preview_max
    guide_preview = profile.validation["preheader"]
    guide_preview_ok = guide_preview["min"] <= preview_chars <= guide_preview["max"]
    checks.append(_check("docs/email-content.json", "preview_text_max_words", preview_ok, preview_words))
    checks.append(_check(EMAIL_GUIDELINE, "preheader_characters", guide_preview_ok, preview_chars))
    if not preview_ok:
        violations.append(f"Preview has {preview_words} words; JSON maximum is {preview_max}")
    if preview_ok and not guide_preview_ok:
        triggered.append("general_email_profile_vs_event_lifecycle")

    body_words = word_count(body)
    json_body_ok = (
        int(benchmarks["body_copy_min_words"]) <= body_words <= int(benchmarks["body_copy_max_words"])
    )
    docx_body_ok = DOCX_BODY_WORDS[0] <= body_words <= DOCX_BODY_WORDS[1]
    empirical_body_ok = DOCX_EMPIRICAL_BODY_WORDS[0] <= body_words <= DOCX_EMPIRICAL_BODY_WORDS[1]
    risk_ok = body_words <= DOCX_BODY_RISK_WORDS
    guide_body = profile.validation["word_count"]
    guide_body_ok = guide_body["min"] <= body_words <= guide_body["max"]
    checks.append(_check("docs/email-content.json", "body_copy_words", json_body_ok, body_words))
    checks.append(_check("docx-ci", "body_words_45_to_215", docx_body_ok, body_words))
    checks.append(_check("docx-empirical-prose", "body_words_45_to_212", empirical_body_ok, body_words))
    checks.append(_check("docx-risk-sentence", "body_not_over_220", risk_ok, body_words))
    checks.append(_check(EMAIL_GUIDELINE, "body_words_75_to_200", guide_body_ok, body_words))
    if json_body_ok and docx_body_ok:
        pass
    elif json_body_ok != docx_body_ok:
        triggered.append("body_word_count")
    else:
        violations.append(f"Body has {body_words} words; JSON and DOCX CI range is 45-215")
    if json_body_ok and docx_body_ok and not empirical_body_ok:
        triggered.append("body_word_count")
    if json_body_ok and docx_body_ok and not guide_body_ok:
        triggered.append("general_email_profile_vs_event_lifecycle")
    if json_body_ok and docx_body_ok and not risk_ok:
        triggered.append("body_word_count")

    spam_hits = _spam_hits(f"{subject}\n{preview}\n{body}")
    checks.append(_check("docs/email-content.json", "prohibited_spam_triggers", not spam_hits, spam_hits))
    if spam_hits:
        violations.append(f"Prohibited spam trigger: {', '.join(spam_hits)}")
    discouraged = _discouraged_hits(f"{subject}\n{preview}\n{body}")
    checks.append(_check("docx-substitution-table", "discouraged_phrases", not discouraged, discouraged))
    if discouraged:
        violations.append(f"DOCX discouraged phrase: {', '.join(discouraged)}")

    urls = _URL_RE.findall(f"{subject}\n{preview}\n{body}")
    link_cap = int(deliverability["max_hyperlinks_per_asset"])
    links_ok = len(urls) <= link_cap
    checks.append(_check("json-and-docx", "max_functional_urls", links_ok, urls))
    if not links_ok:
        violations.append(f"{len(urls)} functional URLs; maximum is {link_cap}")
    shorteners = [url for url in urls if _is_shortener(url)]
    checks.append(_check("docx-deliverability", "no_public_url_shorteners", not shorteners, shorteners))
    if shorteners:
        violations.append(f"Public URL shortener: {', '.join(shorteners)}")

    bang_ok = "!" not in subject
    currency_ok = _CURRENCY_RE.search(subject) is None
    caps_ok = _CAPS_RE.search(subject) is None
    checks.append(_check("docx-engineering", "subject_no_exclamation", bang_ok, subject))
    checks.append(_check("docx-engineering", "subject_no_currency", currency_ok, subject))
    checks.append(_check("docx-engineering", "subject_no_capitalization_spike", caps_ok, subject))
    if not bang_ok:
        violations.append("Subject contains an exclamation mark")
    if not currency_ok:
        violations.append("Subject contains a currency sign")
    if not caps_ok:
        violations.append("Subject contains a capitalization spike")

    bracket_ctas = [
        line.strip()
        for line in body.splitlines()
        if _STANDALONE_CTA_RE.fullmatch(line.strip())
    ]
    cta_text = str(cta).strip() if cta is not None else ""
    if cta_text and not (cta_text.startswith("[") and cta_text.endswith("]")):
        cta_text = f"[{cta_text}]"
    cta_count_ok = len(bracket_ctas) == 1
    cta_match_ok = (not cta) or (cta_count_ok and bracket_ctas[0] == cta_text)
    checks.append(_check("event-examples", "single_standalone_cta", cta_count_ok, bracket_ctas))
    checks.append(_check("event-email", "cta_matches_body", cta_match_ok, cta))
    if not cta_count_ok:
        violations.append("Body must contain exactly one standalone bracket CTA")
    elif cta and not cta_match_ok:
        violations.append("CTA field does not match the standalone bracket CTA")

    greeting_ok = "{{Recipient.FirstName}}" in body
    signoff_ok = "The 66degrees Team" in body and "Best regards," in body
    checks.append(_check("event-examples", "recipient_greeting", greeting_ok, "greeting"))
    checks.append(_check("event-examples", "team_signoff", signoff_ok, "sign-off"))
    if not greeting_ok:
        violations.append("Body is missing the {{Recipient.FirstName}} greeting used by the approved examples")
    if not signoff_ok:
        violations.append('Body is missing the "Best regards," / "The 66degrees Team" sign-off')
    status_ok = status in STATUSES
    verified = asset.get("verified", [])
    executable = status in {"approved", "active"}
    signoff_ok_status = isinstance(verified, list) and (not executable or len(verified) > 0)
    checks.append(_check("docx-governance", "status_enum", status_ok, status))
    checks.append(_check("docx-governance", "verification_before_execution", signoff_ok_status, verified))
    if not status_ok:
        violations.append("status must be draft, approved, or active")
    if not signoff_ok_status:
        violations.append("approved or active assets require human verification")

    stored = asset.get("metrics") if isinstance(asset.get("metrics"), dict) else None
    if stored:
        stored_match = (
            stored.get("subject_word_count") == subject_words
            and stored.get("body_word_count") == body_words
        )
        checks.append(_check("docs/email-content.json", "stored_metrics_match_whitespace", stored_match, stored))
        if not stored_match:
            triggered.append("stored_metrics_vs_whitespace_count")

    # Deduplicate while preserving order.
    seen: set[str] = set()
    triggered_unique = []
    for item in triggered:
        if item not in seen:
            seen.add(item)
            triggered_unique.append(item)

    return {
        "formatting_valid": not violations,
        "grants_approval": False,
        "approved": False,
        "status": status,
        "violations": violations,
        "checks": checks,
        "triggered_conflicts": triggered_unique,
        "source_conflicts": source_conflicts(),
        "metrics": {
            "subject_word_count": subject_words,
            "subject_character_count": subject_chars,
            "preview_word_count": preview_words,
            "preview_character_count": preview_chars,
            "body_word_count": body_words,
            "count_method": "whitespace_split",
        },
    }


def assess_event_email_sequence(sequence: dict[str, dict[str, Any]], brief: dict[str, Any] | None = None) -> dict[str, Any]:
    issues: list[str] = []
    if list(sequence) != list(EVENT_EMAIL_STAGE_KEYS):
        issues.append("Sequence keys are not the seven lifecycle stages in order")
    bodies = []
    subjects = []
    for key in EVENT_EMAIL_STAGE_KEYS:
        asset = sequence.get(key) or {}
        bodies.append(str(asset.get("body") or ""))
        subjects.append(str(asset.get("subject") or ""))
        if asset.get("lifecycle_stage") != key:
            issues.append(f"{key} lifecycle_stage mismatch")
        if asset.get("status") != "draft":
            issues.append(f"{key} status is not draft")
        if asset.get("verified"):
            issues.append(f"{key} has verification without a human approval action")
        validation = asset.get("validation") or {}
        if validation.get("grants_approval") is not False:
            issues.append(f"{key} validation grants approval")
        if validation.get("formatting_valid") is not True:
            issues.append(f"{key} failed formatting validation")
    if len(set(bodies)) != 7:
        issues.append("Lifecycle bodies are not distinct")
    if len(set(subjects)) != 7:
        issues.append("Lifecycle subjects are not distinct")
    if len(bodies) == 7:
        _intent_issues(bodies, subjects, brief or {}, issues)
    return {"passed": not issues, "issues": issues}


def _intent_issues(bodies: list[str], subjects: list[str], brief: dict[str, Any], issues: list[str]) -> None:
    inv1, inv2, inv3, rem1, rem2, attendee, absent = bodies
    if "business value" not in inv1.lower():
        issues.append("Invitation #1 does not state business value")
    if "technical" not in inv2.lower() or "peer" not in inv2.lower() or "problem" not in inv2.lower():
        issues.append("Invitation #2 does not carry technical, peer, and problem context")
    if inv1.strip() == inv2.strip() or inv2.strip() == inv3.strip():
        issues.append("Invitation copy repeats the previous invitation")
    if "registration window" not in inv3.lower():
        issues.append("Invitation #3 does not state the final registration window")
    if word_count(inv3) >= word_count(inv1):
        issues.append("Invitation #3 is not more concise than Invitation #1")
    for banned in ("last chance", "act now", "free!!!", "!!!"):
        if banned in inv3.lower():
            issues.append(f"Invitation #3 uses spam-style urgency: {banned}")
    if "48" not in rem1 or "logistics" not in rem1.lower():
        issues.append("Reminder #1 is missing 48-hour logistics guidance")
    if not rem2.lower().startswith("hi {{recipient.firstname}},\n\ntoday"):
        issues.append("Reminder #2 does not open as day-of communication")
    if "logistics" not in rem2.lower() or word_count(rem2) >= word_count(rem1):
        issues.append("Reminder #2 is not a shorter logistics note than Reminder #1")
    hook = str((brief.get("value_prop") or {}).get("primary_hook") or "").strip()
    if len(hook.split()) >= 4:
        if hook.lower() in rem1.lower() or hook.lower() in rem2.lower():
            issues.append("A reminder repeats the invitation hook")
    if "thank" not in attendee.lower() or "feedback" not in attendee.lower():
        issues.append("Attendee follow-up does not thank the reader and ask for feedback")
    if "optional" not in attendee.lower():
        issues.append("Attendee follow-up does not offer an optional next step")
    if "unable to attend" not in absent.lower() or "future" not in absent.lower():
        issues.append("Non-attendee follow-up does not acknowledge absence and offer a future path")
    for guilt in ("sorry you missed", "you should have", "we regret", "last chance", "disappointed"):
        if guilt in absent.lower():
            issues.append(f"Non-attendee follow-up uses pressure language: {guilt}")
    if attendee.strip() == absent.strip():
        issues.append("Attendee and non-attendee follow-ups are the same")
    brief_text = json.dumps(brief)
    brief_percents = set(_PERCENT_RE.findall(brief_text))
    for key, body in zip(EVENT_EMAIL_STAGE_KEYS, bodies, strict=True):
        for percent in _PERCENT_RE.findall(body):
            if percent not in brief_percents:
                issues.append(f"{key} introduces a percentage that is not in the brief")
        numbers = set(re.findall(r"\b\d+\b", body))
        allowed = set(re.findall(r"\b\d+\b", brief_text))
        if key == "reminder_1":
            allowed.add("48")
        extra = numbers - allowed
        if extra:
            issues.append(f"{key} introduces numbers that are not in the brief: {sorted(extra)}")
    for subject in subjects:
        if "!" in subject or _CURRENCY_RE.search(subject) or _CAPS_RE.search(subject):
            issues.append(f"Subject violates DOCX engineering constraints: {subject}")


def _tagged(stage: EventEmailStage, asset: dict[str, Any]) -> dict[str, Any]:
    tagged = dict(asset)
    tagged["lifecycle_stage"] = stage.key
    tagged["stage"] = stage.label
    return tagged


def _follow_up(follow_ups: list[dict[str, Any]], *, non_attendee: bool) -> dict[str, Any]:
    matches = []
    for asset in follow_ups:
        label = str(asset.get("sub_type") or "").lower()
        is_non = "non-attendee" in label or "non attendee" in label
        if is_non == non_attendee:
            matches.append(asset)
    if len(matches) != 1:
        kind = "non-attendee" if non_attendee else "attendee"
        raise EventEmailSourceError(f"Expected one {kind} follow-up, found {len(matches)}")
    return matches[0]


def _check(source: str, rule: str, passed: bool, observed: Any) -> dict[str, Any]:
    return {"source": source, "rule": rule, "passed": passed, "observed": observed}


def _spam_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits = []
    for phrase in json_deliverability().get("prohibited_spam_triggers") or []:
        token = str(phrase).lower()
        if " " in token or "!" in token:
            found = token in lowered
        else:
            found = re.search(rf"\b{re.escape(token)}\b", lowered) is not None
        if found:
            hits.append(token)
    return hits


def _discouraged_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase, _replacement in DOCX_DISCOURAGED_PHRASES if phrase in lowered]


def _is_shortener(url: str) -> bool:
    host = re.sub(r"^https?://", "", url, flags=re.IGNORECASE).split("/")[0].lower()
    host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host in DOCX_SHORTENER_HOSTS

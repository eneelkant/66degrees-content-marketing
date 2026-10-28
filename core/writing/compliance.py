"""Deterministic writing-guideline compliance checks."""
from __future__ import annotations

import re
from typing import Any

from .loader import get_guideline_version, load_guidelines
from .models import ComplianceFinding, ComplianceResult
from .skills import select_skills

# Em dash, en dash, and horizontal bar — hyphen-minus alone is allowed for AI-Native etc.
_DASH_RE = re.compile(r"[\u2012\u2013\u2014\u2015]")
_NUMBER_RE = re.compile(
    r"(?<![\w.])(?:\$\s*)?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?"
    r"|(?<![\w.])(?:\$\s*)?\d+(?:\.\d+)?\s*%"
    r"|(?<![\w.])(?:\$\s*)?\d{4,}(?:\.\d+)?"
)
_STANDALONE_CREDENTIAL_RE = re.compile(
    r"(?i)^\s*we are (?:a |an |the )?(?:google cloud )?diamond partner\.?\s*$",
    re.MULTILINE,
)
_SENTENCE_CASE_VIOLATION_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,})\b"
)

# Phrases that are hard failures per company facts / messaging v17.
_HARD_PHRASES: tuple[tuple[str, str, str], ...] = (
    ("google cloud premier partner", "company_facts", "Use Google Cloud Diamond Partner; never Premier."),
    ("premier partner", "company_facts", "Use Google Cloud Diamond Partner; never Premier."),
    ("gcp partner", "company_facts", "Use Google Cloud Diamond Partner."),
    ("the agentic enterprise", "company_facts", "Use The AI-Native Enterprise."),
    ("chrysalisos", "company_facts", "ChrysalisOS is retired; never mention it."),
    ("ai-native consultancy", "messaging", "Say company, not AI-native consultancy."),
    ("agent garden", "messaging", "Say Industry Agent Libraries."),
    ("automate the past", "messaging", "Remove banned phrase 'automate the past'."),
    ("paradigm shift", "messaging", "Do not pair paradigm with shift."),
    ("build, adopt, evolve", "messaging", "Do not use Build, Adopt, Evolve as a named framework."),
    ("architecting the ai-native enterprise", "messaging", "Banned competitor-fingerprint phrase."),
    ("66degrees builds ai for the enterprise", "company_facts", "Literally false; remove."),
    ("we build ai native enterprises", "company_facts", "Literally false; remove."),
    ("speed to value", "messaging", "Banned competitor-fingerprint phrase."),
    ("cutting edge", "messaging", "Banned competitor-fingerprint phrase."),
    ("world class", "messaging", "Banned competitor-fingerprint phrase."),
    ("world-class", "messaging", "Banned competitor-fingerprint phrase."),
    ("purpose built", "messaging", "Banned competitor-fingerprint phrase."),
    ("purpose-built", "messaging", "Banned competitor-fingerprint phrase."),
    ("powerful ally", "messaging", "Banned competitor-fingerprint phrase."),
    ("own the outcome", "messaging", "Banned competitor-fingerprint phrase."),
    ("finish line", "messaging", "Banned competitor-fingerprint phrase."),
    ("we do this by", "messaging", "Banned competitor-fingerprint phrase."),
)

_HARD_WORD_BANS: tuple[tuple[str, str, str], ...] = (
    ("seamless", "messaging", "Remove banned term 'seamless'."),
    ("unlock", "messaging", "Remove banned term 'unlock'."),
    ("unlocks", "messaging", "Remove banned term 'unlock'."),
    ("journey", "messaging", "Remove banned term 'journey' (messaging ban)."),
    ("journeys", "messaging", "Remove banned term 'journey' (messaging ban)."),
    ("destination", "messaging", "Remove banned term 'destination'."),
)

_COMPETITOR_CLOUD_RE = re.compile(r"(?i)\b(aws|azure|amazon web services|microsoft azure)\b")
_RECAP_BRIDGE_RE = re.compile(r"(?i)\b(last time we (told|shared|said)|as (we|I) (mentioned|said) (last|before))\b")
_TRIAD_ABSTRACTION_RE = re.compile(
    r"(?i)\b(every layer of the|across the entire|end.to.end AI stack|convene|unfolds)\b"
)
_FEAR_PRESSURE_RE = re.compile(
    r"(?i)\b(don't miss out|limited seats remaining|act now or|falling behind|left behind)\b"
)


_SKIP_CLAIM_KEYS = {
    "metadata",
    "updated_at",
    "created_at",
    "campaign_id",
    "asset_id",
    "kit_id",
    "id",
    "fetched_at",
    "reference_metadata",
    "hybrid_score",
    "performance_score",
    "llm_provider",
    "llm_model",
    "guideline_version",
    "applicable_skills",
    "writing_compliance",
    "quality",
    "status",
    "context_injected",
    "references_used_count",
    "strategy",
    "writing_guidelines_available",
}
_ISO_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?\b"
)


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_text(v) for v in value)
    if value is None:
        return ""
    return str(value)


def _flatten_for_claims(value: Any) -> str:
    """Flatten copy for numerical-claim checks, skipping runtime metadata."""
    if isinstance(value, str):
        return _ISO_TIMESTAMP_RE.sub(" ", value)
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            if str(key).lower() in _SKIP_CLAIM_KEYS:
                continue
            parts.append(_flatten_for_claims(item))
        return " ".join(parts)
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_for_claims(v) for v in value)
    if value is None:
        return ""
    return str(value)


def _finding(
    severity: str,
    rule: str,
    message: str,
    *,
    source: str,
    suggested_fix: str,
    section: str | None = None,
) -> ComplianceFinding:
    return ComplianceFinding(
        severity=severity,  # type: ignore[arg-type]
        rule=rule,
        message=message,
        source=source,
        section=section,
        suggested_fix=suggested_fix,
    )


def _allowed_number_blob(brief_data: dict[str, Any] | None, proof_excerpts: list[str] | None) -> str:
    parts = [_flatten_text(brief_data or {})]
    for excerpt in proof_excerpts or []:
        parts.append(excerpt)
    # Always allow figures that appear in the messaging proof spine / company facts.
    parts.append(
        "35 10 18 22 285 660 56 25 30 11.3 55 3500 100 196 300 90 70 4.8 4 19 12 2023 2025 2026 "
        "50 80 60 10000 20000 3.7 10 2024 2020 2021 2022 2027 2028"
    )
    # Guideline VERSION strings (e.g. 2026.10.26) are metadata, not performance claims.
    version = get_guideline_version()
    if version and version != "unavailable":
        parts.append(version)
    return " ".join(parts)


def evaluate_compliance(
    content: Any,
    asset_type: str | None = None,
    *,
    brief_data: dict[str, Any] | None = None,
    proof_excerpts: list[str] | None = None,
    mode: str = "qa",
    skills: list[str] | None = None,
) -> ComplianceResult:
    """Evaluate content against deterministic writing rules.

    Subjective style quality is limited to soft warnings. Missing guideline files
    yield status ``unavailable`` — never a silent pass claiming compliance.
    """
    selected = skills or select_skills(asset_type, brief_data=brief_data, mode=mode)
    version = get_guideline_version()
    guidelines = load_guidelines()
    if not guidelines:
        return ComplianceResult(
            status="unavailable",
            guideline_version=version,
            applicable_skills=selected,
            loaded=False,
            hard_failures=[
                _finding(
                    "hard_failure",
                    "guidelines_missing",
                    "Writing guidelines could not be loaded; compliance cannot be claimed.",
                    source="content_knowledge/",
                    suggested_fix="Restore content_knowledge/writing_guidelines and retry.",
                )
            ],
            suggested_fixes=["Restore content_knowledge/writing_guidelines and retry."],
        )

    text = _flatten_text(content)
    claim_text = _flatten_for_claims(content)
    lowered = text.lower()
    hard: list[ComplianceFinding] = []
    warnings: list[ComplianceFinding] = []

    for phrase, source, fix in _HARD_PHRASES:
        if phrase in lowered:
            hard.append(
                _finding(
                    "hard_failure",
                    "banned_phrase",
                    f"Banned phrase detected: '{phrase}'.",
                    source=f"writing_guidelines/{source}.md",
                    suggested_fix=fix,
                    section=phrase,
                )
            )

    for word, source, fix in _HARD_WORD_BANS:
        if re.search(rf"(?i)\b{re.escape(word)}\b", text):
            hard.append(
                _finding(
                    "hard_failure",
                    "banned_term",
                    f"Banned term detected: '{word}'.",
                    source=f"writing_guidelines/{source}.md",
                    suggested_fix=fix,
                    section=word,
                )
            )

    for match in _COMPETITOR_CLOUD_RE.finditer(text):
        hard.append(
            _finding(
                "hard_failure",
                "competitor_cloud",
                f"Competitor cloud mentioned: '{match.group(0)}'.",
                source="writing_guidelines/messaging_and_terminology.md",
                suggested_fix="Remove competitor cloud references; focus on Google Cloud partnership.",
                section=match.group(0),
            )
        )

    for match in _DASH_RE.finditer(text):
        hard.append(
            _finding(
                "hard_failure",
                "no_dashes",
                f"Dash character U+{ord(match.group(0)):04X} is not allowed.",
                source="writing_guidelines/grammar_and_style.md",
                suggested_fix="Rewrite without em/en dashes; use commas or new sentences. Keep AI-Native hyphen.",
                section=match.group(0),
            )
        )
        break  # one finding is enough

    if _STANDALONE_CREDENTIAL_RE.search(text):
        hard.append(
            _finding(
                "hard_failure",
                "embedded_credential",
                "Standalone credential brag detected.",
                source="writing_guidelines/brand_voice.md",
                suggested_fix="Embed the Diamond Partner fact inside a sentence about the reader.",
            )
        )

    if _FEAR_PRESSURE_RE.search(text):
        hard.append(
            _finding(
                "hard_failure",
                "no_fear_pressure",
                "Fear, pressure, or manufactured-scarcity framing detected.",
                source="writing_guidelines/brand_voice.md",
                suggested_fix="Use winner-side, calm, true constraints only.",
            )
        )

    # Channel-specific hard limits
    normalized = (asset_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"email", "event_email", "invite_email"} and isinstance(content, dict):
        subject = str(content.get("subject") or content.get("Subject") or "")
        if subject and len(subject) >= 40:
            hard.append(
                _finding(
                    "hard_failure",
                    "email_subject_length",
                    f"Email subject is {len(subject)} characters; must be under 40.",
                    source="writing_guidelines/social_and_email.md",
                    suggested_fix="Shorten the subject; put value in the first three words.",
                    section="subject",
                )
            )
        title = str(content.get("title") or content.get("Title") or "")
        if title:
            words = len(re.findall(r"\b\w+\b", title))
            if words > 14:
                hard.append(
                    _finding(
                        "hard_failure",
                        "email_title_words",
                        f"Email title has {words} words; maximum is 14 (target 12).",
                        source="writing_guidelines/social_and_email.md",
                        suggested_fix="Shorten the title to 12 words or fewer.",
                        section="title",
                    )
                )

    if normalized == "google_ads" and isinstance(content, dict):
        for i, headline in enumerate(content.get("headlines") or []):
            if len(str(headline)) > 30:
                hard.append(
                    _finding(
                        "hard_failure",
                        "google_ads_headline_length",
                        f"Headline {i + 1} exceeds 30 characters.",
                        source="writing_guidelines/specs_and_guardrails.md",
                        suggested_fix="Shorten the headline to 30 characters or fewer.",
                        section=f"headlines[{i}]",
                    )
                )
                break

    if normalized == "linkedin_ads" and isinstance(content, dict):
        primary = str(content.get("primary_text") or "")
        headline = str(content.get("headline") or "")
        if len(primary) > 600:
            hard.append(
                _finding(
                    "hard_failure",
                    "linkedin_primary_length",
                    "LinkedIn primary text exceeds 600 characters.",
                    source="writing_guidelines/social_and_email.md",
                    suggested_fix="Shorten primary text; aim for 150 characters before truncation.",
                    section="primary_text",
                )
            )
        if len(headline) > 200:
            hard.append(
                _finding(
                    "hard_failure",
                    "linkedin_headline_length",
                    "LinkedIn headline exceeds 200 characters.",
                    source="writing_guidelines/social_and_email.md",
                    suggested_fix="Shorten headline; aim for 70 characters.",
                    section="headline",
                )
            )

    # Unsupported numerical claims: numbers in copy not present in brief/proof blob.
    # Skip runtime metadata / ISO timestamps so campaign kits are not false-failed.
    allowed_blob = _allowed_number_blob(brief_data, proof_excerpts).lower()
    for match in _NUMBER_RE.finditer(claim_text):
        token = match.group(0)
        compact = re.sub(r"[^\d.]", "", token)
        if not compact:
            continue
        # Calendar years alone are not performance claims.
        if re.fullmatch(r"20[2-3]\d", compact):
            continue
        if compact not in re.sub(r"[^\d.]", " ", allowed_blob) and compact not in allowed_blob.replace(",", ""):
            digits = re.sub(r"\D", "", compact)
            if digits and digits not in re.sub(r"\D", "", allowed_blob):
                hard.append(
                    _finding(
                        "hard_failure",
                        "unsupported_numerical_claim",
                        f"Numerical claim '{token}' is not present in the brief or proof excerpts.",
                        source="writing_guidelines/proof_and_evidence.md",
                        suggested_fix="Remove the number or cite a Proof Library / brief source.",
                        section=token,
                    )
                )
                break

    # Incorrect product terminology (legacy names as current products)
    if re.search(r"(?i)\bprism\b", text) and "paradigm" not in lowered:
        hard.append(
            _finding(
                "hard_failure",
                "legacy_name",
                "PRISM must be translated to Paradigm°.",
                source="writing_guidelines/company_facts.md",
                suggested_fix="Replace PRISM with Paradigm°.",
            )
        )

    # Soft warnings
    if _RECAP_BRIDGE_RE.search(text):
        warnings.append(
            _finding(
                "warning",
                "recap_bridge",
                "Recap-bridge language may violate 'say it once' across a sequence.",
                source="writing_guidelines/brand_voice.md",
                suggested_fix="Add new material instead of recapping prior emails.",
            )
        )
    if _TRIAD_ABSTRACTION_RE.search(text):
        warnings.append(
            _finding(
                "warning",
                "mechanical_style",
                "Possible mechanical / AI-sounding phrasing detected.",
                source="writing_guidelines/brand_voice.md",
                suggested_fix="Prefer plain verbs and one concrete thought at a time.",
            )
        )
    if lowered.count("diamond partner") + lowered.count("partner of the year") > 2:
        warnings.append(
            _finding(
                "warning",
                "credential_stack",
                "Multiple credential mentions; prefer one embedded credential per asset.",
                source="writing_guidelines/brand_voice.md",
                suggested_fix="Keep a single embedded credential.",
            )
        )
    if "ceo_voice" in selected and re.search(r"(?i)ai-first and ai-native", text):
        warnings.append(
            _finding(
                "warning",
                "ceo_v17_conflict",
                "CEO phrasing 'AI-first and AI-native' kept; flag for Taha vs messaging v17.",
                source="writing_guidelines/ceo_voice.md",
                suggested_fix="Retain for CEO-voice assets; do not silently rewrite.",
            )
        )
    if normalized in {"linkedin_post", "social", "social_post"} and not (
        brief_data or {}
    ).get("approved_template_counts"):
        warnings.append(
            _finding(
                "warning",
                "social_limits_unknown",
                "No approved social template counts in brief; cannot invent character limits.",
                source="writing_guidelines/social_and_email.md",
                suggested_fix="Supply approved_template_counts from a prior approved post of this type.",
            )
        )

    suggested = []
    for item in hard + warnings:
        if item.suggested_fix and item.suggested_fix not in suggested:
            suggested.append(item.suggested_fix)

    status: str
    if hard:
        status = "needs_revision"
    else:
        status = "pass"

    return ComplianceResult(
        status=status,  # type: ignore[arg-type]
        guideline_version=version,
        applicable_skills=selected,
        hard_failures=hard,
        warnings=warnings,
        suggested_fixes=suggested,
        loaded=True,
        details={"asset_type": asset_type, "char_count": len(text)},
    )


def preserve_facts_on_rewrite(
    original: Any,
    rewritten: Any,
    *,
    brief_data: dict[str, Any] | None = None,
) -> list[ComplianceFinding]:
    """Flag numbers that appear in the original but were altered or dropped incorrectly.

    Used by optimization tests: rewriting must not invent new numbers.
    """
    findings: list[ComplianceFinding] = []
    original_nums = {m.group(0) for m in _NUMBER_RE.finditer(_flatten_text(original))}
    rewritten_nums = {m.group(0) for m in _NUMBER_RE.finditer(_flatten_text(rewritten))}
    invented = rewritten_nums - original_nums
    allowed = set()
    for m in _NUMBER_RE.finditer(_allowed_number_blob(brief_data, None)):
        allowed.add(m.group(0))
    for token in invented:
        compact = re.sub(r"[^\d.]", "", token)
        if any(compact in re.sub(r"[^\d.]", "", a) for a in allowed):
            continue
        findings.append(
            _finding(
                "hard_failure",
                "rewrite_invented_number",
                f"Rewrite introduced numerical claim '{token}' not in the original or brief.",
                source="writing_guidelines/proof_and_evidence.md",
                suggested_fix="Preserve verified numbers; do not invent new statistics.",
                section=token,
            )
        )
    return findings

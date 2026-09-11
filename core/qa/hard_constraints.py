import re
from typing import Any
from .models import QACheck, QAState


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_text(v) for v in value)
    return str(value)


def validate_hard_constraints(content: Any, asset_type: str) -> QACheck:
    details: dict[str, Any] = {}
    violations: list[str] = []

    if asset_type == "google_ads":
        headlines = content.get("headlines", []) if isinstance(content, dict) else []
        descriptions = content.get("descriptions", []) if isinstance(content, dict) else []
        paths = content.get("display_paths", []) if isinstance(content, dict) else []
        details.update(headlines=len(headlines), descriptions=len(descriptions), display_paths=len(paths))
        if len(headlines) != 15:
            violations.append(f"Google Ads requires exactly 15 headlines; found {len(headlines)}")
        if len(descriptions) != 4:
            violations.append(f"Google Ads requires exactly 4 descriptions; found {len(descriptions)}")
        long_headlines = [x for x in headlines if len(x) > 30]
        long_descriptions = [x for x in descriptions if len(x) > 90]
        long_paths = [x for x in paths if len(x) > 15]
        if long_headlines:
            violations.append(f"{len(long_headlines)} headline(s) exceed 30 characters")
        if long_descriptions:
            violations.append(f"{len(long_descriptions)} description(s) exceed 90 characters")
        if long_paths:
            violations.append(f"{len(long_paths)} display path(s) exceed 15 characters")
        details.update(long_headlines=long_headlines, long_descriptions=long_descriptions, long_display_paths=long_paths)

    elif asset_type == "linkedin_ads":
        primary_text = content.get("primary_text", "") if isinstance(content, dict) else ""
        headline = content.get("headline", "") if isinstance(content, dict) else ""
        details.update(primary_text_characters=len(primary_text), headline_characters=len(headline))
        if len(primary_text) > 600:
            violations.append("LinkedIn primary text exceeds 600 characters")
        if len(headline) > 200:
            violations.append("LinkedIn headline exceeds 200 characters")

    elif asset_type == "email":
        text = _flatten_text(content)
        details["word_count"] = len(re.findall(r"\b\w+\b", text))
        details["character_count"] = len(text)
        if not text.strip():
            violations.append("Email content is empty")

    state = QAState.REWRITE if violations else QAState.PASS
    return QACheck(
        name="hard_constraints",
        state=state,
        message="; ".join(violations) if violations else "All channel hard constraints passed.",
        details=details | {"violations": violations},
    )

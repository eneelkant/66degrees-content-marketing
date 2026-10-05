"""Collect explicit Slack and Drive requests from a brief."""

from __future__ import annotations

from typing import Any

from core.security.input import sanitize_string
from core.sources.drive_source import retrieve_drive
from core.sources.slack_source import retrieve_slack


def retrieve_requested_sources(brief: dict[str, Any] | None, **transports: Any) -> dict[str, Any]:
    """Read Slack or Drive only when the brief asks for that source."""
    data = brief or {}
    sources = data.get("sources") if isinstance(data.get("sources"), dict) else {}
    slack_spec = sources.get("slack") if isinstance(sources.get("slack"), dict) else None
    drive_spec = sources.get("drive") if isinstance(sources.get("drive"), dict) else None
    slack = retrieve_slack(slack_spec, token=transports.get("slack_token"), transport=transports.get("slack_transport"))
    drive = retrieve_drive(
        drive_spec,
        token=transports.get("drive_token"),
        get_json=transports.get("drive_get_json"),
        get_text=transports.get("drive_get_text"),
    )
    slack = _sanitize_provider(slack)
    drive = _sanitize_provider(drive)
    return {
        "slack": slack,
        "drive": drive,
        "layers": {
            "source_facts": _drive_facts(drive),
            "feedback": _slack_feedback(slack),
            "user_instructions": _user_instructions(data),
        },
    }


def _user_instructions(brief: dict[str, Any]) -> dict[str, Any]:
    metadata = brief.get("metadata") if isinstance(brief.get("metadata"), dict) else {}
    audience = brief.get("audience") if isinstance(brief.get("audience"), dict) else {}
    value_prop = brief.get("value_prop") if isinstance(brief.get("value_prop"), dict) else {}
    return {
        "title": metadata.get("title"),
        "audience": audience.get("primary_persona"),
        "hook": value_prop.get("primary_hook"),
        "takeaways": value_prop.get("key_takeaways") or [],
        "cta": brief.get("cta_primary") or brief.get("cta"),
    }


def _drive_facts(drive: dict[str, Any]) -> list[dict[str, Any]]:
    facts = []
    for item in drive.get("items") or []:
        if item.get("read_status") in {"exported_text", "media_text"} and item.get("excerpt"):
            facts.append(
                {
                    "source": "google_drive",
                    "file_id": item.get("file_id"),
                    "name": item.get("name"),
                    "web_view_link": item.get("web_view_link"),
                    "excerpt": item.get("excerpt"),
                }
            )
    return facts


def _slack_feedback(slack: dict[str, Any]) -> list[dict[str, Any]]:
    feedback = []
    for item in slack.get("items") or []:
        feedback.append(
            {
                "source": "slack",
                "role": "feedback",
                "promoted_to_brand_rule": False,
                "channel": item.get("channel"),
                "ts": item.get("ts"),
                "user": item.get("user"),
                "text": item.get("text"),
            }
        )
    return feedback


def _sanitize_provider(result: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(result)
    cleaned["message"] = sanitize_string(str(result.get("message") or ""))
    items = []
    for item in result.get("items") or []:
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        for key in ("text", "excerpt", "message"):
            if key in copied and isinstance(copied[key], str):
                copied[key] = sanitize_string(copied[key])
        items.append(copied)
    cleaned["items"] = items
    return cleaned

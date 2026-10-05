"""Targeted Slack retrieval. Messages are feedback, not brand rules."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Callable

import httpx

from config.settings import get_settings

SLACK_API = "https://slack.com/api"
_CHANNEL_ID = re.compile(r"^[CGD][A-Z0-9]+$")
SlackCall = Callable[[str, dict[str, Any]], dict[str, Any]]


def slack_token_from_env() -> str | None:
    if "SLACK_BOT_TOKEN" in os.environ:
        return os.environ.get("SLACK_BOT_TOKEN", "").strip() or None
    value = get_settings().slack_bot_token
    return value.strip() if isinstance(value, str) and value.strip() else None


def retrieve_slack(
    spec: dict[str, Any] | None,
    *,
    token: str | None = None,
    transport: SlackCall | None = None,
) -> dict[str, Any]:
    """Retrieve messages only when `spec` is an explicit request."""
    if spec is None:
        return _result(requested=False, status="not_requested", items=[])
    channel = str(spec.get("channel") or "").strip()
    thread_ts = str(spec.get("thread_ts") or spec.get("thread") or "").strip()
    if not channel and not thread_ts:
        return _result(
            requested=True,
            status="target_required",
            items=[],
            message="Slack retrieval requires a channel or a channel plus thread_ts. The workspace is not listed by default.",
        )
    if thread_ts and not channel:
        return _result(
            requested=True,
            status="target_required",
            items=[],
            message="Slack thread retrieval requires both channel and thread_ts.",
        )
    resolved_token = token if token is not None else slack_token_from_env()
    if not resolved_token:
        return _result(
            requested=True,
            status="credentials_missing",
            items=[],
            message="Set SLACK_BOT_TOKEN to retrieve Slack messages. No messages were retrieved.",
        )
    call = transport or _http_transport(resolved_token)
    try:
        channel_id, channel_name = _resolve_channel(call, channel)
    except _SlackError as exc:
        return _result(requested=True, status="api_error", items=[], message=str(exc))
    if channel and not channel_id:
        return _result(
            requested=True,
            status="channel_not_found",
            items=[],
            message=f"No Slack channel matched {channel!r}.",
        )
    limit = _limit(spec.get("limit"))
    params: dict[str, Any] = {"channel": channel_id, "limit": limit}
    try:
        oldest = _unix(spec.get("oldest") or spec.get("since"))
        latest = _unix(spec.get("latest") or spec.get("until"))
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        method = "conversations.replies" if thread_ts else "conversations.history"
        if thread_ts:
            params["ts"] = thread_ts
        payload = call(method, params)
    except _SlackError as exc:
        return _result(requested=True, status="api_error", items=[], message=str(exc))
    if not payload.get("ok"):
        return _result(
            requested=True,
            status="api_error",
            items=[],
            message=f"Slack API returned {payload.get('error', 'unknown_error')}.",
        )
    keywords = [str(word).strip().lower() for word in (spec.get("keywords") or []) if str(word).strip()]
    items = []
    for message in payload.get("messages") or []:
        text = str(message.get("text") or "")
        if keywords and not all(word in text.lower() for word in keywords):
            continue
        items.append(
            {
                "source": "slack",
                "role": "feedback",
                "promoted_to_brand_rule": False,
                "channel": channel_id,
                "channel_name": channel_name,
                "ts": message.get("ts"),
                "thread_ts": message.get("thread_ts") or thread_ts or None,
                "user": message.get("user"),
                "text": text,
            }
        )
    return _result(
        requested=True,
        status="retrieved",
        items=items[:limit],
        message="Slack messages are feedback context. They are not brand rules.",
        query={"channel": channel_id, "thread_ts": thread_ts or None, "keywords": keywords},
    )


def _resolve_channel(call: SlackCall, channel: str) -> tuple[str, str | None]:
    if not channel:
        return "", None
    if _CHANNEL_ID.match(channel):
        return channel, None
    payload = call("conversations.list", {"limit": 200, "exclude_archived": True, "types": "public_channel,private_channel"})
    if not payload.get("ok"):
        raise _SlackError(f"Slack API returned {payload.get('error', 'unknown_error')}.")
    wanted = channel.lstrip("#").lower()
    for item in payload.get("channels") or []:
        name = str(item.get("name") or "")
        if name.lower() == wanted:
            return str(item.get("id") or ""), name
    return "", None


def _http_transport(token: str) -> SlackCall:
    def call(method: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.get(
                f"{SLACK_API}/{method}",
                headers={"Authorization": f"Bearer {token}"},
                params={key: value for key, value in params.items() if value is not None},
                timeout=20.0,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            raise _SlackError("Slack request failed.") from exc
        if not isinstance(body, dict):
            raise _SlackError("Slack returned a non-object response.")
        return body

    return call


def _limit(value: Any) -> int:
    try:
        parsed = int(value) if value is not None else 20
    except (TypeError, ValueError):
        parsed = 20
    return min(max(parsed, 1), 50)


def _unix(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return text
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _SlackError(f"Unrecognized Slack time {text!r}. Use a unix timestamp or ISO-8601.") from exc
    return str(parsed.timestamp())


def _result(*, requested: bool, status: str, items: list[dict[str, Any]], message: str = "", query: dict | None = None) -> dict[str, Any]:
    return {
        "provider": "slack",
        "requested": requested,
        "status": status,
        "role": "feedback",
        "promoted_to_brand_rule": False,
        "message": message,
        "query": query or {},
        "items": items,
    }


class _SlackError(ValueError):
    pass

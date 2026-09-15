from __future__ import annotations

from typing import Any


def normalize_event(brief_data: dict[str, Any]) -> dict[str, Any]:
    brief = dict(brief_data or {})
    source = dict(brief.get("source") or {})

    source["type"] = "66degrees"
    brief["source"] = source

    return brief

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.reference_library.sqlite_client import SQLiteReferenceClient


DB_PATH = Path(__file__).resolve().parents[2] / "references" / "references.db"


def find_event(query: str) -> dict[str, Any] | None:
    """Find the closest stored Google Cloud event by title/source text."""
    query = (query or "").strip().lower()
    if not query:
        return None

    db = SQLiteReferenceClient(DB_PATH)
    records = db.search(limit=100)

    candidates = [
        record
        for record in records
        if record.metadata.get("source_id") == "google_cloud_events"
    ]

    ranked = sorted(
        candidates,
        key=lambda record: _match_score(query, record),
        reverse=True,
    )

    if not ranked or _match_score(query, ranked[0]) == 0:
        return None

    return normalize_event(ranked[0])


def normalize_event(record: Any) -> dict[str, Any]:
    """Convert a Google Cloud reference record into the campaign brief shape."""
    content = record.content or ""
    raw_title = record.title or "Google Cloud Event"

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]

    title_lines = [
        line.strip()
        for line in raw_title.splitlines()
        if line.strip()
    ]

    if len(title_lines) > 1:
        title = title_lines[0]
    else:
        title = raw_title

    date = _extract_line(
        content,
        [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ],
    )

    description = _first_description(content, title)

    source = record.source or ""

    if "](" in source:
        source = source.split("](", 1)[1].split(")", 1)[0]

    return {
        "metadata": {
            "title": title,
            "date": date,
            "event_format": "online" if "ONLINE" in content.upper() else None,
            "location": None,
        },
        "audience": {
            "primary_persona": _infer_persona(content),
            "industry_verticals": [],
        },
        "value_prop": {
            "primary_hook": description,
            "key_takeaways": [],
        },
        "cta_primary": "Register",
        "agenda": [],
        "speakers": [],
        "source": {
            "type": "google_cloud",
            "url": source,
        },
    }

def _match_score(query: str, record: Any) -> int:
    haystack = f"{record.title} {record.content} {record.source}".lower()
    terms = [term for term in query.split() if len(term) > 2]
    return sum(term in haystack for term in terms)


def _extract_line(content: str, prefixes: list[str]) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in prefixes):
            return stripped
    return None


def _first_description(content: str, title: str) -> str:
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]

    months = (
        "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
    )

    for line in lines:
        upper = line.upper()

        if line == title:
            continue

        if upper in {"ONLINE", "ON DEMAND"}:
            continue

        if any(upper.startswith(month) for month in months):
            continue

        if upper.endswith("MIN") or upper.endswith("HR") or upper.endswith("HRS"):
            continue

        return line

    return title

def _infer_persona(content: str) -> str | None:
    text = content.lower()

    if "security leaders" in text or "it security" in text:
        return "Security leaders"
    if "business leaders" in text:
        return "Business leaders"
    if "it infrastructure" in text or "architecture" in text:
        return "IT and architecture leaders"

    return None

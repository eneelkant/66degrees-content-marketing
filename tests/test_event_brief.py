from core.event_brief.google_cloud import find_event
from core.event_brief.intake import process_event_brief
from core.reference_library.models import ReferenceRecord
from core.reference_library.sqlite_client import SQLiteReferenceClient


def _seed_google_cloud_event(db_path):
    db = SQLiteReferenceClient(db_path)
    db.upsert(
        ReferenceRecord(
            id="gce-fixture-1",
            title="Cloud Roadmap: Infrastructure for the Agentic Era",
            content=(
                "ONLINE\n"
                "Jun 12, 2026\n"
                "Learn how cloud roadmap infrastructure supports the agentic era."
            ),
            source="https://cloudonair.withgoogle.com/events/cloud-roadmap-infrastructure-agentic-era",
            source_type="external",
            authority_level="approved",
            metadata={"source_id": "google_cloud_events"},
        )
    )
    return db_path


def test_66degrees_event_needs_required_fields():
    result = process_event_brief(
        {
            "metadata": {
                "title": "AI Leadership Summit",
            }
        }
    )

    assert result["status"] == "NEEDS_CLARIFICATION"
    assert "metadata.date" in result["missing_fields"]
    assert "audience.primary_persona" in result["missing_fields"]
    assert "value_prop.primary_hook" in result["missing_fields"]
    assert result["questions"]


def test_google_cloud_event_can_be_found_from_reference_library(tmp_path):
    db_path = _seed_google_cloud_event(tmp_path / "references.db")
    event = find_event("cloud roadmap infrastructure agentic era", db_path=db_path)

    assert event is not None
    assert event["metadata"]["title"]
    assert event["metadata"]["date"]
    assert event["metadata"]["event_format"] == "online"
    assert event["source"]["type"] == "google_cloud"
    assert event["source"]["url"].startswith("https://")


def test_66degrees_event_is_marked_as_internal_source():
    from importlib import import_module

    normalize_66degrees_event = import_module(
        "core.event_brief.66degrees"
    ).normalize_event

    result = normalize_66degrees_event(
        {
            "metadata": {
                "title": "AI Leadership Summit",
            }
        }
    )

    assert result["source"]["type"] == "66degrees"


def test_66degrees_intake_normalizes_source():
    from core.event_brief.intake import process_event_brief

    result = process_event_brief(
        {
            "metadata": {
                "title": "AI Leadership Summit",
                "date": "2026-10-15",
            },
            "audience": {
                "primary_persona": "CIO",
            },
            "value_prop": {
                "primary_hook": "Turn AI ambition into operating reality.",
            },
            "cta_primary": "Register",
            "source": {
                "type": "66degrees",
            },
        }
    )

    assert result["status"] == "READY_FOR_GENERATION"
    assert result["brief"]["source"]["type"] == "66degrees"


def test_public_api_process_event_brief_uses_event_intake():
    from clients.public_api import process_event_brief

    result = process_event_brief(
        {
            "metadata": {
                "title": "AI Leadership Summit",
            }
        }
    )

    assert result["status"] == "NEEDS_CLARIFICATION"
    assert "metadata.date" in result["missing_fields"]
    assert result["questions"]


def test_google_cloud_event_source_url_is_plain_url(tmp_path):
    from core.event_brief.google_cloud import find_event

    db_path = _seed_google_cloud_event(tmp_path / "references.db")
    event = find_event("cloud roadmap infrastructure agentic era", db_path=db_path)

    assert event is not None
    url = event["source"]["url"]

    assert url.startswith("https://")
    assert not url.startswith("[")
    assert "](" not in url
    assert not url.endswith(")")


def test_find_event_returns_none_when_reference_db_missing(tmp_path):
    missing = tmp_path / "does-not-exist.db"
    assert find_event("cloud roadmap", db_path=missing) is None

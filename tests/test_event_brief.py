from core.event_brief.google_cloud import find_event
from core.event_brief.intake import process_event_brief


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


def test_google_cloud_event_can_be_found_from_reference_library():
    event = find_event("cloud roadmap infrastructure agentic era")

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


def test_google_cloud_event_source_url_is_plain_url():
    from core.event_brief.google_cloud import find_event

    event = find_event("cloud roadmap infrastructure agentic era")

    assert event is not None
    url = event["source"]["url"]

    assert url.startswith("https://")
    assert not url.startswith("[")
    assert "](" not in url
    assert not url.endswith(")")

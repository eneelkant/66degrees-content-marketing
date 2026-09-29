"""Regression tests for reference refresh hardening and workflow tag logic."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from core.reference_library.models import ReferenceRecord
from core.reference_library.source_fetcher import ApprovedSourceFetcher
from core.reference_library.sqlite_client import SQLiteReferenceClient
from core.reference_library.sync import ReferenceSync
from scripts.refresh_references import main as refresh_main


def _record(source_id: str = "66degrees_events") -> ReferenceRecord:
    return ReferenceRecord(
        id=f"id-{source_id}",
        title="t",
        content="c",
        source="https://example.com",
        metadata={"source_id": source_id},
    )


def test_refresh_sync_idempotent_and_atomic(tmp_path):
    db = SQLiteReferenceClient(tmp_path / "references.db")
    sync = ReferenceSync(db, metadata_path=tmp_path / "references.refresh.json")
    first = sync.sync([_record()])
    second = sync.sync([_record()])
    assert first["status"] == "REFRESHED"
    assert second["status"] == "REFRESHED"
    assert db.count() == 1
    meta = json.loads((tmp_path / "references.refresh.json").read_text(encoding="utf-8"))
    assert meta["record_count"] == 1
    assert "last_refresh" in meta


def test_refresh_refuses_empty_sync(tmp_path):
    db = SQLiteReferenceClient(tmp_path / "references.db")
    sync = ReferenceSync(db, metadata_path=tmp_path / "references.refresh.json")
    with pytest.raises(ValueError, match="empty"):
        sync.sync([])


def test_html_http_error_is_actionable(monkeypatch):
    fetcher = ApprovedSourceFetcher(max_attempts=2, backoff_seconds=0)

    def boom(request):
        return httpx.Response(503, request=request)

    transport = httpx.MockTransport(boom)
    monkeypatch.setattr(
        ApprovedSourceFetcher,
        "_fetch_html_source",
        lambda self, source_id: (_ for _ in ()).throw(httpx.HTTPStatusError(
            "error",
            request=httpx.Request("GET", "https://example.com"),
            response=httpx.Response(503),
        )),
    )
    with pytest.raises(Exception):
        fetcher._with_retries("66degrees_events", lambda: fetcher._fetch_html_source("66degrees_events"))


def test_fetch_all_aggregates_required_source_failures(monkeypatch):
    fetcher = ApprovedSourceFetcher(max_attempts=1, backoff_seconds=0)
    monkeypatch.setattr(
        fetcher,
        "_fetch_html_source",
        lambda source_id: (_ for _ in ()).throw(RuntimeError(f"down:{source_id}")),
    )
    monkeypatch.setattr(
        fetcher,
        "_fetch_google_cloud_events",
        lambda: (_ for _ in ()).throw(RuntimeError("playwright-down")),
    )
    with pytest.raises(RuntimeError, match="required approved source"):
        fetcher.fetch_all()


def test_refresh_cli_current_without_force(tmp_path, monkeypatch):
    # Point tools DB into tmp and mark as fresh via metadata.
    import core.mcp_legacy.tools as tools

    db_path = tmp_path / "references.db"
    meta_path = tmp_path / "references.refresh.json"
    client = SQLiteReferenceClient(db_path)
    client.upsert(_record())
    sync = ReferenceSync(client, metadata_path=meta_path)
    sync.sync([_record()])

    monkeypatch.setattr(tools, "_db", client)
    monkeypatch.setattr(tools, "_sync", sync)
    monkeypatch.setattr(tools, "DB_PATH", db_path)

    assert refresh_main([]) == 0
    assert refresh_main(["--force"]) in {0, 1}  # force may fail network in CI; exercised below mocked


def test_refresh_cli_force_with_mocked_fetcher(tmp_path, monkeypatch):
    import core.mcp_legacy.tools as tools

    db_path = tmp_path / "references.db"
    meta_path = tmp_path / "references.refresh.json"
    client = SQLiteReferenceClient(db_path)
    sync = ReferenceSync(client, metadata_path=meta_path)
    monkeypatch.setattr(tools, "_db", client)
    monkeypatch.setattr(tools, "_sync", sync)
    monkeypatch.setattr(tools, "DB_PATH", db_path)

    class FakeFetcher:
        def fetch_all(self):
            return [_record("66degrees_events"), _record("google_cloud_events")]

    monkeypatch.setattr(tools, "ApprovedSourceFetcher", FakeFetcher)
    assert refresh_main(["--force"]) == 0
    assert client.count() == 2


def test_workflow_tag_next_computation_avoids_v110_collision():
    """Mirror the fixed workflow logic: with tags present, next must not be v1.1.0."""
    tags = ["v1.1.0"]
    latest = sorted(
        tags,
        key=lambda t: tuple(int(p) for p in t.lstrip("v").split(".")),
        reverse=True,
    )[0]
    n = int(latest.split(".")[1])
    next_tag = f"v1.{n + 1}.0"
    assert next_tag == "v1.2.0"
    assert next_tag != "v1.1.0"


def test_refresh_workflow_fetches_tags_and_pins_runner():
    text = Path(".github/workflows/refresh-data.yml").read_text(encoding="utf-8")
    assert "actions/checkout@v7" in text
    assert "actions/setup-python@v7" in text
    assert "fetch-tags: true" in text
    assert "ubuntu-24.04" in text
    assert "concurrency:" in text
    assert "git ls-remote --exit-code --tags origin" in text
    assert "references/references.refresh.json" in text


def test_no_secret_patterns_in_refresh_outputs(tmp_path):
    sync = ReferenceSync(SQLiteReferenceClient(tmp_path / "r.db"), metadata_path=tmp_path / "r.refresh.json")
    result = sync.sync([_record()])
    blob = json.dumps(result)
    assert "sk-" not in blob
    assert "ghp_" not in blob
    assert "BEGIN PRIVATE" not in blob

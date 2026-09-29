"""MCP access partition and remote auth safety tests."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from clients.access import (
    PROTECTED_TOOLS,
    READ_ORIENTED_TOOLS,
    WRITE_ORIENTED_TOOLS,
    assert_surface_partition,
)
from clients.http_security import MCPAuthCORS
from clients.surface import PUBLIC_TOOL_NAMES
from core.campaign.state_machine import CampaignStatus, assert_exportable, transition


def test_sixteen_tool_contract_and_partition():
    assert len(PUBLIC_TOOL_NAMES) == 16
    assert_surface_partition()
    assert "approve_campaign" in PROTECTED_TOOLS
    assert "export_campaign" in PROTECTED_TOOLS
    assert "create_campaign" in PROTECTED_TOOLS
    assert "get_campaign_status" in READ_ORIENTED_TOOLS
    assert WRITE_ORIENTED_TOOLS.isdisjoint(READ_ORIENTED_TOOLS)
    assert PROTECTED_TOOLS <= WRITE_ORIENTED_TOOLS
    assert "qa_validate_asset" in READ_ORIENTED_TOOLS


def test_remote_auth_rejects_missing_credentials():
    async def _run():
        calls = []

        async def app(scope, receive, send):
            calls.append("app")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        wrapper = MCPAuthCORS(app, expected_token="secret-token", allowed_origins=["*"])
        sent = []

        async def send(message):
            sent.append(message)

        async def receive():
            return {"type": "http.request"}

        await wrapper({"type": "http", "headers": []}, receive, send)
        assert sent[0]["status"] == 401
        assert "app" not in calls

    asyncio.run(_run())


def test_remote_auth_accepts_bearer_token():
    async def _run():
        async def app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send({"type": "http.response.body", "body": b"ok"})

        wrapper = MCPAuthCORS(app, expected_token="secret-token", allowed_origins=["*"])
        sent = []

        async def send(message):
            sent.append(message)

        async def receive():
            return {"type": "http.request"}

        await wrapper(
            {"type": "http", "headers": [[b"authorization", b"Bearer secret-token"]]},
            receive,
            send,
        )
        assert sent[0]["status"] == 200

    asyncio.run(_run())


def test_non_loopback_requires_token(monkeypatch):
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    from config.settings import get_settings

    get_settings.cache_clear()
    import clients.chatgpt.sse_server as sse

    monkeypatch.setattr(
        sse,
        "get_settings",
        lambda: type(
            "S",
            (),
            {
                "mcp_auth_token": None,
                "mcp_api_key": None,
                "cors_allowed_origins": ["*"],
            },
        )(),
    )
    host = "0.0.0.0"
    settings = sse.get_settings()
    with pytest.raises(SystemExit):
        if host not in {"127.0.0.1", "localhost", "::1"} and not (
            settings.mcp_auth_token or settings.mcp_api_key
        ):
            raise SystemExit("refusing")


def test_human_approval_still_required_before_export():
    with pytest.raises(PermissionError):
        assert_exportable(CampaignStatus.APPROVAL_PENDING)
    approved = transition(CampaignStatus.APPROVAL_PENDING, CampaignStatus.APPROVED)
    assert_exportable(approved)


def test_public_mcp_docs_do_not_claim_hosted_endpoint():
    readme = Path("README.md").read_text(encoding="utf-8")
    docs = Path("docs/PUBLIC_MCP_ACCESS.md").read_text(encoding="utf-8")
    assert "Internal Use Only" not in readme
    assert "not an MCP server" in readme
    assert "not** an MCP endpoint" in docs or "not an MCP endpoint" in docs
    assert "GitHub login" in readme
    assert "MCP_AUTH_TOKEN" in docs
    assert "no first-party hosted" in docs.lower() or "does **not** ship" in readme or "does not ship" in readme.lower()

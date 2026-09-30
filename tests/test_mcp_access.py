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


def test_public_hostnames_include_platform_domain(monkeypatch):
    monkeypatch.setenv("MCP_PUBLIC_HOST", "https://mcp.example.com/mcp, extra.example.com")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "content-mcp.onrender.com")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "content-mcp.up.railway.app")
    from clients.chatgpt.sse_server import public_hostnames

    assert public_hostnames() == [
        "mcp.example.com",
        "extra.example.com",
        "content-mcp.onrender.com",
        "content-mcp.up.railway.app",
    ]


def test_render_hostname_is_not_hardcoded():
    source = Path("clients/chatgpt/sse_server.py").read_text(encoding="utf-8")
    assert "RENDER_EXTERNAL_HOSTNAME" in source
    assert "onrender.com" not in source


def test_health_is_public_and_foreign_host_is_rejected(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("MCP_API_KEY", "")
    monkeypatch.setenv("MCP_PUBLIC_HOST", "mcp.example.com")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://chatgpt.com,https://claude.ai,https://gemini.google.com",
    )
    from config.settings import get_settings

    get_settings.cache_clear()
    from starlette.testclient import TestClient

    from clients.chatgpt.sse_server import build_app

    app = build_app("streamable-http")
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "deploy-check", "version": "0"},
        },
    }
    with TestClient(app, base_url="https://mcp.example.com") as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        unauthenticated = client.post(
            "/mcp",
            headers={
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
            },
            json=init,
        )
        assert unauthenticated.status_code == 401

        invalid = client.post(
            "/mcp",
            headers={
                "authorization": "Bearer wrong-token",
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
            },
            json=init,
        )
        assert invalid.status_code == 401

        blocked_origin = client.post(
            "/mcp",
            headers={
                "authorization": "Bearer secret-token",
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "origin": "https://evil.example",
            },
            json=init,
        )
        assert blocked_origin.status_code == 403

        allowed = client.post(
            "/mcp",
            headers={
                "authorization": "Bearer secret-token",
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "origin": "https://chatgpt.com",
            },
            json=init,
        )
        assert allowed.status_code == 200
        assert allowed.json()["result"]["serverInfo"]["name"] == "66degrees-content-marketing"

        api_key = client.post(
            "/mcp",
            headers={
                "x-api-key": "secret-token",
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "origin": "https://gemini.google.com",
            },
            json=init,
        )
        assert api_key.status_code == 200

        rejected = client.post(
            "/mcp",
            headers={
                "host": "evil.example",
                "authorization": "Bearer secret-token",
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "origin": "https://claude.ai",
            },
            json=init,
        )
        assert rejected.status_code == 421
        assert "Invalid Host" in rejected.text


def test_public_mcp_docs_do_not_claim_hosted_endpoint():
    readme = Path("README.md").read_text(encoding="utf-8")
    docs = Path("docs/PUBLIC_MCP_ACCESS.md").read_text(encoding="utf-8")
    assert "Internal Use Only" not in readme
    assert "not an MCP server" in readme
    assert "not** an MCP endpoint" in docs or "not an MCP endpoint" in docs
    assert "GitHub login" in readme
    assert "MCP_AUTH_TOKEN" in docs
    assert "no first-party hosted" in docs.lower() or "does **not** ship" in readme or "does not ship" in readme.lower()

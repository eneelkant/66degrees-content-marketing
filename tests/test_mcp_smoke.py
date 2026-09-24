"""MCP smoke tests — discovery and a safe tool call without production credentials."""
from __future__ import annotations

import asyncio
import os

import pytest

from clients.claude.server import mcp
from clients.surface import PUBLIC_TOOL_NAMES


@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")


def test_mcp_discovers_locked_public_surface():
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert names == set(PUBLIC_TOOL_NAMES)
    assert len(names) == 16


def test_mcp_tool_schemas_are_objects():
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        schema = tool.inputSchema
        assert isinstance(schema, dict), tool.name
        assert schema.get("type") == "object", tool.name
        assert "properties" in schema, tool.name


def test_mcp_safe_tool_call_process_event_brief():
    result = asyncio.run(
        mcp.call_tool(
            "process_event_brief",
            {
                "brief_data": {
                    "metadata": {"title": "Smoke Event"},
                }
            },
        )
    )
    # FastMCP may return CallToolResult or structured content depending on SDK.
    payload = result
    if hasattr(result, "structuredContent") and result.structuredContent is not None:
        payload = result.structuredContent
    elif hasattr(result, "data") and result.data is not None:
        payload = result.data
    elif isinstance(result, list) and result and hasattr(result[0], "text"):
        import json

        payload = json.loads(result[0].text)
    assert payload["status"] == "NEEDS_CLARIFICATION"
    assert payload["missing_fields"]
    assert payload["questions"]


def test_mcp_module_entrypoints_importable():
    import clients.claude.server as claude_server
    import clients.chatgpt.sse_server as chatgpt_server

    assert claude_server.mcp is mcp
    assert callable(chatgpt_server.main)
    assert os.getenv("LLM_PROVIDER") == "mock"

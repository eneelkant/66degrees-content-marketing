import json
from pathlib import Path

from clients.surface import PUBLIC_TOOL_NAMES
from clients.gemini.adapter import TOOL_DEFINITIONS

EXPECTED = list(PUBLIC_TOOL_NAMES)


def test_locked_public_tool_surface():
    assert list(PUBLIC_TOOL_NAMES) == EXPECTED
    assert [item["name"] for item in TOOL_DEFINITIONS] == EXPECTED
    assert len(EXPECTED) == 11


def test_no_internal_specialists_leak_into_gemini_definitions():
    names = {item["name"] for item in TOOL_DEFINITIONS}
    assert not any("strategist" in n or "producer" in n or "architect" in n for n in names)


def test_client_configs_preserve_surface():
    root = Path(__file__).resolve().parents[1]
    claude = json.loads((root / "config/claude_desktop_config.example.json").read_text())
    chatgpt = json.loads((root / "clients/chatgpt/openai_agents_config.json").read_text())
    gemini = json.loads((root / "clients/gemini/gemini_cli_config.json").read_text())
    assert "66degrees-content-marketing" in claude["mcpServers"]
    assert chatgpt["mcp"]["allowed_tools"] == EXPECTED
    assert "66degrees-content-marketing" in gemini["mcpServers"]


def test_transport_entrypoints_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "clients/claude/server.py").exists()
    assert (root / "clients/chatgpt/sse_server.py").exists()
    assert (root / "clients/gemini/adapter.py").exists()

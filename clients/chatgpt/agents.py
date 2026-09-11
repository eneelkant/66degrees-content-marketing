"""OpenAI Agents SDK bridge for the remote MCP server.

The dependency is imported lazily so the core repository remains provider-neutral.
"""
from __future__ import annotations


def build_hosted_mcp_tool(server_url: str, *, require_approval: str = "always"):
    try:
        from agents.mcp import HostedMCPTool
    except ImportError as exc:  # pragma: no cover - optional integration dependency
        raise RuntimeError("Install the OpenAI Agents SDK to use the ChatGPT Agents adapter.") from exc
    return HostedMCPTool(
        tool_config={
            "type": "mcp",
            "server_label": "66degrees-content-marketing",
            "server_url": server_url,
            "require_approval": require_approval,
        }
    )

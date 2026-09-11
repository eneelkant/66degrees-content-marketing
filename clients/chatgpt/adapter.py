"""OpenAI/ChatGPT adapter metadata and response normalization."""
from clients.surface import PUBLIC_TOOL_NAMES

OPENAI_MCP_CONFIG = {
    "type": "mcp",
    "server_label": "66degrees-content-marketing",
    "server_url": "https://YOUR-DOMAIN.example.com/mcp",
    "allowed_tools": list(PUBLIC_TOOL_NAMES),
    "require_approval": "always",
}


def format_result(result: dict) -> dict:
    return {"content": result, "markdown": _markdown(result)}


def _markdown(result: dict) -> str:
    status = result.get("qa_status") or result.get("status", "UNKNOWN")
    return f"**Status:** {status}"

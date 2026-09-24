#!/usr/bin/env bash
# Lightweight integrity checks for agents (imports, surface lock, settings).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required. Run ./scripts/setup.sh first." >&2
  exit 1
fi

export PYTHONPATH=.
export LLM_PROVIDER="${LLM_PROVIDER:-mock}"

echo ">> Python version"
uv run python -c "import sys; assert sys.version_info[:2]==(3,12), sys.version; print(sys.version.split()[0])"

echo ">> Import integrity"
uv run python - <<'PY'
from clients.surface import PUBLIC_TOOL_NAMES
from clients import public_api
from clients.claude.server import mcp, TOOL_NAME_MAP
from config.settings import Settings
from core.brand.rules import load_brand_rules
from core.approval.gate import HumanApprovalGate

assert len(PUBLIC_TOOL_NAMES) == 16
assert set(TOOL_NAME_MAP) == set(PUBLIC_TOOL_NAMES)
assert load_brand_rules().mandatory_terminology
gate = HumanApprovalGate()
assert gate.is_approved("x") is False
s = Settings()
print("check_ok", "tools", len(PUBLIC_TOOL_NAMES), "llm_default", s.llm_provider)
PY

echo ">> MCP tool discovery"
uv run python - <<'PY'
import asyncio
from clients.claude.server import mcp
from clients.surface import PUBLIC_TOOL_NAMES

async def main():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    missing = set(PUBLIC_TOOL_NAMES) - names
    assert not missing, f"Missing MCP tools: {missing}"
    for tool in tools:
        assert tool.inputSchema and tool.inputSchema.get("type") == "object", tool.name
    print("mcp_ok", "discovered", len(names))

asyncio.run(main())
PY

echo "All checks passed."

#!/usr/bin/env bash
# Install a reproducible local environment for agents and developers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required. Install from https://docs.astral.sh/uv/ and retry." >&2
  exit 1
fi

EXPECTED_PY="$(tr -d '[:space:]' < .python-version)"
echo ">> Syncing Python ${EXPECTED_PY} dependencies with uv (dev group)…"
uv sync --group dev

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ">> Created .env from .env.example (LLM_PROVIDER=mock)."
else
  echo ">> .env already present — left unchanged."
fi

mkdir -p data core/exports references

echo ">> Validating imports…"
PYTHONPATH=. uv run python -c "from clients.surface import PUBLIC_TOOL_NAMES; from clients.claude.server import mcp; assert len(PUBLIC_TOOL_NAMES)==16; print('imports_ok tools=', len(PUBLIC_TOOL_NAMES))"

echo "Setup complete. Next: ./scripts/check.sh && ./scripts/test.sh"
echo "Start MCP (stdio): ./scripts/run-mcp.sh"

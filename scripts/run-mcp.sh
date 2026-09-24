#!/usr/bin/env bash
# Start the local MCP server (stdio by default; HTTP optional).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required. Run ./scripts/setup.sh first." >&2
  exit 1
fi

export PYTHONPATH=.
export LLM_PROVIDER="${LLM_PROVIDER:-mock}"

MODE="${1:-stdio}"

case "$MODE" in
  stdio)
    echo "Starting MCP on stdio (Claude Desktop / Cursor local)…" >&2
    exec uv run python -m clients.claude.server
    ;;
  http|streamable-http)
    HOST="${MCP_HOST:-127.0.0.1}"
    PORT="${MCP_PORT:-8000}"
    echo "Starting MCP Streamable HTTP on ${HOST}:${PORT}…" >&2
    echo "Remote mode requires MCP_AUTH_TOKEN or MCP_API_KEY in .env." >&2
    exec uv run python -m clients.chatgpt.sse_server --transport streamable-http --host "$HOST" --port "$PORT"
    ;;
  sse)
    HOST="${MCP_HOST:-127.0.0.1}"
    PORT="${MCP_PORT:-8000}"
    echo "Starting MCP SSE on ${HOST}:${PORT}…" >&2
    exec uv run python -m clients.chatgpt.sse_server --transport sse --host "$HOST" --port "$PORT"
    ;;
  *)
    echo "Usage: $0 [stdio|http|sse]" >&2
    exit 2
    ;;
esac

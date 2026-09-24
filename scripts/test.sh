#!/usr/bin/env bash
# Run the deterministic test suite (no production credentials required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required. Run ./scripts/setup.sh first." >&2
  exit 1
fi

export LLM_PROVIDER="${LLM_PROVIDER:-mock}"
export PYTHONPATH=.

echo ">> pytest (LLM_PROVIDER=${LLM_PROVIDER})"
uv run pytest -q "$@"

# Task: repository-health-check

## Objective
Verify the repo installs, imports, checks, and tests cleanly for Cursor agents.

## Required inputs
- Clean working tree (optional)
- Network for first `uv sync` only

## Inspect
- `scripts/setup.sh`, `scripts/check.sh`, `scripts/test.sh`
- `.python-version`, `pyproject.toml`, `uv.lock`
- `.env.example`

## Expected output
- setup / check / test all exit 0
- Report any failing command with root cause

## Validation
```bash
./scripts/setup.sh && ./scripts/check.sh && ./scripts/test.sh
```

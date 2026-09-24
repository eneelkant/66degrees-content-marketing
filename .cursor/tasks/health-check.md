# Task: /health-check

## Objective
Verify the repository is operable for Cursor agents.

## Inputs
- None

## MCP tools
- None required (shell)

## Commands
```bash
./scripts/setup.sh
./scripts/check.sh
./scripts/test.sh
```

## Expected output
- All commands exit 0
- 16 MCP tools discovered

## Validation
- Report failing command + root cause if any

## Safety
- Use `LLM_PROVIDER=mock`; do not require live credentials

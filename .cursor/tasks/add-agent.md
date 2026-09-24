# Task: add-agent

## Objective
Add or extend an internal specialist capability without expanding the public MCP surface unless explicitly required.

## Required inputs
- Capability name and stage (plan / create / govern)
- Input/output schema
- Whether it needs a new public tool (default: no)

## Inspect
- `clients/surface.py` (locked 11 tools)
- `core/generators/`, `core/qa/`, `core/optimization/`
- Existing tests for the nearest sibling capability

## Expected output
- Implementation under `core/`
- Tests with `LLM_PROVIDER=mock`
- Docs update if behavior is user-visible

## Validation
- Public tool count remains 11 unless a new tool was explicitly approved
- `./scripts/test.sh` passes

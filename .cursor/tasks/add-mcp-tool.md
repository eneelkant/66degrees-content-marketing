# Task: add-mcp-tool

## Objective
Add a public MCP tool across all client adapters with matching names and schemas.

## Required inputs
- Tool name, description, arguments
- Implementation plan in `clients/public_api.py`

## Inspect
- `clients/surface.py`
- `clients/public_api.py`
- `clients/claude/server.py`, `clients/chatgpt/`, `clients/gemini/`
- MCP smoke tests

## Expected output
- Name added to `PUBLIC_TOOL_NAMES`
- Wrapper in every adapter
- Schema-valid discovery via `mcp.list_tools()`
- Unit + smoke tests

## Validation
```bash
./scripts/check.sh && ./scripts/test.sh -k mcp
```

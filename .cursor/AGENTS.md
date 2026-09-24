# Cursor Agent Operating Manual — 66degrees Content Marketing

## Repository purpose

This repository is an AI-powered **66degrees content marketing** system using MCP and multiple specialist capabilities. It turns marketing / event briefs into campaign-ready content with brand governance, QA, human approval, and export.

## Agent principles

Cursor must:

1. Inspect before modifying.
2. Preserve existing architecture unless there is a strong reason to change it.
3. Prefer small, testable changes.
4. Never expose secrets.
5. Never hard-code API keys.
6. Never silently remove functionality.
7. Add tests for meaningful behavior changes.
8. Run relevant tests after changes.
9. Update documentation when behavior changes.
10. Keep human approval in the content workflow.
11. Preserve brand governance.
12. Never bypass QA gates merely to make tests pass.

## Architecture map

| Concern | Location |
|---|---|
| Locked public MCP surface (11 tools) | `clients/surface.py`, `clients/public_api.py` |
| Claude / Cursor stdio MCP server | `clients/claude/server.py` |
| ChatGPT remote HTTP MCP | `clients/chatgpt/sse_server.py` |
| Gemini adapter | `clients/gemini/` |
| Brand rules (JSON) | `core/brand/brand_rules.json` + `core/brand/rules.py` |
| QA pipeline | `core/qa/` |
| Human approval gate | `core/approval/gate.py` |
| Export (JSON/DOCX/XLSX) | `exporters/campaign.py` |
| LLM routing (mock/anthropic/openai/gemini) | `core/llm/` |
| Settings / env | `config/settings.py`, `.env.example` |
| Reference library | `core/reference_library/`, `references/` |

## Default verification loop

```bash
./scripts/setup.sh
./scripts/check.sh
./scripts/test.sh
./scripts/run-mcp.sh   # stdio; Ctrl+C when smoke-checked
```

Use `LLM_PROVIDER=mock` for all automated tests. Do not call paid APIs in CI.

## Content workflow (do not bypass)

```
Brief → Strategy → Create → Social/Repurpose → Brand + QA → Optimize loop → Human approve → Export
```

Export **must** fail without explicit approval (`HumanApprovalGate.require_approved`).

## Secrets

- Copy `.env.example` → `.env` locally.
- Never commit `.env`, keys, tokens, or credential JSON.
- Prefer actionable errors that name the missing env var.

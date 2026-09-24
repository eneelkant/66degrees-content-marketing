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
13. Never invent campaign data or claim an external action succeeded without verification.
14. Never publish or export final content without explicit human approval.

## When asked to create a campaign

1. Inspect the campaign brief (require at least `campaign_name` + `objective`).
2. Determine required content types / channels.
3. Run the strategy stage (via `create_campaign` or `generate_content_strategy`).
4. Generate content (`create_campaign` preferred for end-to-end).
5. Repurpose content and generate social assets.
6. Run brand validation.
7. Run QA.
8. Fix QA failures with optimize/refine.
9. Repeat QA as needed.
10. **Stop at human approval** (`APPROVAL_PENDING`).
11. Never publish without approval.
12. Export only after `approve_campaign` / `approve_campaign_kit`.

- Prefer MCP tool `create_campaign` over manually chaining every stage unless the user asks for a single stage.
- On `REVISION_REQUIRED`, fix content and `resume_campaign` — never approve or export.
- Use `idempotency_key` on create when retries must not duplicate campaigns.
- See `docs/PRODUCTION_WORKFLOW.md` for operator lifecycle details.

## Architecture map

| Concern | Location |
|---|---|
| Public MCP surface (16 tools) | `clients/surface.py`, `clients/public_api.py` |
| Campaign orchestrator + state machine | `core/campaign/` |
| Claude / Cursor stdio MCP server | `clients/claude/server.py` |
| Brand rules | `core/brand/` |
| QA pipeline | `core/qa/` |
| Human approval gate | `core/approval/gate.py` |
| Export | `exporters/campaign.py` |
| LLM routing | `core/llm/` |
| Docs | `docs/` |

## Default verification loop

```bash
./scripts/setup.sh
./scripts/check.sh
./scripts/test.sh
./scripts/run-mcp.sh
```

Use `LLM_PROVIDER=mock` for automated tests. Do not call paid APIs in CI.

## Content workflow (do not bypass)

```
Brief → Strategy → Event Intelligence → Content → Repurpose → Social
  → Brand → QA → Optimize loop → Human approve → Export
```

Export **must** fail without approval.

## Secrets

- Copy `.env.example` → `.env` locally.
- Never commit `.env`, keys, tokens, or credential JSON.
- Prefer actionable errors that name the missing env var.

# Pull request description

**Title:** Make repository agent-ready for Cursor and autonomous marketing workflows

## Summary

This branch turns the 66degrees content marketing MCP repository into a Cursor-operable automation platform: reproducible setup, locked MCP surface with campaign orchestration, resumable campaign state, enforced brand/QA/human-approval gates, and documentation for agents and future Cursor Automations.

## Problems discovered

- Clean clones failed Google Cloud event tests because `references.db` is gitignored and empty.
- No agent-friendly setup/check/test/run-mcp scripts or `.env.example`.
- No Cursor operating manual, rules, or reusable tasks.
- No PR CI for check + test (only scheduled reference refresh).
- `generate_social_posts` expected `asset` but repurpose returned `assets`.
- Dotenv `CORS_ALLOWED_ORIGINS` as a plain URL crashed Settings.
- No end-to-end campaign orchestrator with resumable state or explicit status machine.

## Fixes implemented

- Fixture-based event lookup tests; `find_event(..., db_path=)`.
- Scripts: `setup.sh`, `check.sh`, `test.sh`, `run-mcp.sh`.
- `.env.example`, CORS `NoDecode` parsing, actionable LLM missing-key errors.
- Default `LLM_PROVIDER=mock` for safe local/CI runs.
- Cursor `.cursor/AGENTS.md`, rules, and tasks.
- CI workflow running check + test without production secrets.
- MCP smoke tests and expanded mocked E2E journeys.

## MCP improvements

Public surface expanded from 11 specialist tools to **16** tools:

- Original 11 atomic tools preserved.
- Added orchestration: `create_campaign`, `get_campaign_status`, `resume_campaign`, `approve_campaign`, `export_campaign`.
- `create_campaign` runs strategy → content → repurpose/social → brand → QA/optimize and **stops at human approval**.
- Export remains blocked until approval (kit gate + campaign status machine).

## Cursor integration

- `.cursor/AGENTS.md` — operating manual including campaign workflow rules.
- `.cursor/rules/` — architecture, Python, MCP, testing, security, content governance.
- `.cursor/tasks/` — health-check, campaign, strategy, content, social, QA, brand-check, approve, export, and more.
- `docs/CURSOR_AUTOMATION.md` — how to run / automate from Cursor.

## Testing

```bash
./scripts/setup.sh
./scripts/check.sh   # 16 MCP tools discovered
./scripts/test.sh    # 67+ deterministic tests, LLM_PROVIDER=mock
```

Coverage includes state-machine illegal transitions, orchestrated webinar campaign E2E, MCP smoke, approval blocking export, and failure/config errors.

## Security

- No credentials committed; `.env` gitignored.
- Logging redacts sensitive keys.
- Payload sanitization retained.
- Repo-wide secret scan clean for this branch.

## Remaining limitations

- Live LLM / remote MCP auth still require operator-supplied env vars (never fabricated).
- Reference library population still requires network refresh (`scripts/refresh_references.py`) for production content grounding.
- This environment may lack GitHub push credentials; push/PR may need to be completed by a human with repo write access.

## How to verify

```bash
git checkout cursor/agent-readiness-22b2
./scripts/setup.sh && ./scripts/check.sh && ./scripts/test.sh
```

# Production workflow

Practical operator / agent guide for the 66degrees content marketing MCP platform.

## 1. Architecture

```text
Cursor / Claude / ChatGPT / Gemini
        ↓ MCP (16 tools)
clients/public_api.py
        ↓
core/campaign orchestrator  →  specialists (strategy, generators, QA, brand, approval, export)
        ↓
data/campaigns/*.json  (+ in-memory kit/asset session stores)
```

See also: `docs/AGENT_ARCHITECTURE.md`, `docs/MCP_TOOL_CATALOG.md`.

## 2. Campaign lifecycle

Internal statuses:

```text
DRAFT → GENERATED → QA_PENDING → QA_PASSED → APPROVAL_PENDING → APPROVED → EXPORTED
```

Failure / revision:

```text
QA_FAILED | REVISION_REQUIRED | ERROR | REJECTED
```

Operator aliases (`lifecycle_label`):

| Label | Meaning |
|---|---|
| `STRATEGY_READY` | Strategy complete, content not yet |
| `CONTENT_READY` | `GENERATED` |
| `FAILED` | `ERROR` |

## 3. MCP tools

16 public tools — specialists + orchestration. Catalog: `docs/MCP_TOOL_CATALOG.md`.

Preferred end-to-end entry: **`create_campaign`**.

## 4. State machine (hard gates)

Blocked:

- `QA_FAILED → APPROVED`
- `APPROVAL_PENDING → EXPORTED`
- any non-`APPROVED` → `EXPORTED`

Allowed happy path:

- `APPROVAL_PENDING → APPROVED → EXPORTED`

## 5. Human approval

Mandatory. `create_campaign` stops at `APPROVAL_PENDING`.

Human-controlled:

- `approve_campaign` / `approve_campaign_kit`
- production publish outside this repo
- provision of live API keys

Autonomous (safe with mock LLM):

- health check, strategy, content, social, repurpose, brand, QA, optimize, resume, status

## 6. Persistence

- Path: `{DATA_DIR}/campaigns/{campaign_id}.json` (default `./data/campaigns/`)
- Fields: stages, assets, QA, brand, approval, export, errors, provider, timestamps
- Session kit cache: `clients.public_api._KITS` (rehydrated from campaign assets when needed)

## 7. Resume behavior

`resume_campaign(campaign_id)`:

- Skips completed stages
- From `REVISION_REQUIRED` / `QA_FAILED`: resets QA→export stages and retries
- From `APPROVAL_PENDING`: does **not** invent approval
- From `EXPORTED`: idempotent no-op message

Interrupt testing uses `run_until_approval(..., stop_after=stage)`.

## 8. QA

`qa_validate_asset` runs hard constraints, brand rules, originality (and Emailens for email).

Statuses: `PASS` | `WARNING` | `REWRITE`.

After optimize loops, **REWRITE stays `REVISION_REQUIRED`** — never auto-exported.

## 9. Brand validation

Source: `core/brand/brand_rules.json` + `core/brand/rules.py`.

Deterministic checks:

- forbidden jargon
- mandatory terminology replacements
- placeholder patterns (`TBD`, `lorem ipsum`, …)
- unsupported claim patterns (`guaranteed ROI`, …)

Do not invent unofficial brand statistics or executive quotes.

## 10. Failure recovery

| Failure | Behavior |
|---|---|
| Invalid brief | `ValueError` with missing fields |
| LLM missing key / unavailable | `LLMProviderError` subclasses (actionable, no secrets) |
| Invalid structured LLM output | `LLMStructuredOutputError` |
| QA rewrite remaining | `REVISION_REQUIRED`; export blocked |
| Persistence missing id | `FileNotFoundError` |
| Illegal transition | `PermissionError` |
| Duplicate create with `idempotency_key` | Returns existing campaign |
| Repeat approve/export | Idempotent success |

## 11. Cursor usage

1. `./scripts/setup.sh`
2. Read `.cursor/AGENTS.md`
3. Prefer tasks `/health-check`, `/campaign`, `/qa`, `/approve`, `/export`
4. Automation notes: `docs/CURSOR_AUTOMATION.md`

## 12. Local setup

```bash
./scripts/setup.sh
cp -n .env.example .env   # if needed
./scripts/run-mcp.sh      # stdio
```

Python 3.12 + `uv` required.

## 13. Testing

```bash
./scripts/check.sh
./scripts/test.sh
```

Always `LLM_PROVIDER=mock` in CI. No production credentials required.

## 14. GitHub workflow

Branch: `cursor/agent-readiness-22b2`

```bash
git push -u origin cursor/agent-readiness-22b2
gh pr create --title "Make repository agent-ready for Cursor and autonomous marketing workflows" \
  --body-file docs/PR_DESCRIPTION.md
```

CI: `.github/workflows/ci.yml` runs check + test.

## 15. Known limitations

- Live LLM / remote MCP auth require operator env vars
- Reference DB refresh needs network/Playwright
- No Salesforce / LinkedIn / email platform publish integrations in-repo
- In-memory kit store is process-local (campaign JSON is the durable source of truth)

## 16. Future integrations

- Cursor Automations trigger → `create_campaign` → Slack notify for approval
- Wire approved export into CMS / DAM with separate human-controlled connectors
- Optional live provider smoke jobs outside PR CI

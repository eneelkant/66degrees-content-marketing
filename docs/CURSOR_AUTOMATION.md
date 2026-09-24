# Cursor Automation readiness

This repository is designed so a Cursor Agent (and later a Cursor Automation) can operate the marketing workflow without guessing undocumented commands.

## 1. Open the repository in Cursor

1. Clone `https://github.com/eneelkant/66degrees-content-marketing`
2. Open the folder in Cursor
3. Checkout the working branch (e.g. `cursor/agent-readiness-22b2` or `main` after merge)

## 2. Start Agent mode

1. Run `./scripts/setup.sh` once
2. Open Agent / Chat in Cursor
3. Point the agent at `.cursor/AGENTS.md` and `.cursor/tasks/`

## 3. Health check

Ask the agent to run the health-check task, or execute:

```bash
./scripts/check.sh
./scripts/test.sh
```

## 4. Campaign generation

Prefer the MCP tool / public API:

```text
create_campaign({
  "campaign_name": "66degrees Agentic AI Webinar",
  "campaign_type": "webinar",
  "audience": "Enterprise technology leaders",
  "objective": "Generate webinar promotion assets",
  "offer": "Register",
  "key_messages": ["Practical architecture", "Governance"],
  "channels": ["email", "linkedin", "landing_page"],
  "deadline": "2026-11-15"
})
```

Expected: `status=APPROVAL_PENDING`, assets generated, export blocked.

## 5. How MCP tools are used

- Local stdio: `./scripts/run-mcp.sh` or `uv run python -m clients.claude.server`
- Configure Cursor MCP using `config/claude_desktop_config.example.json` (absolute repo path)
- Tool catalog: `docs/MCP_TOOL_CATALOG.md`

## 6. Human approval

Automation **must stop** at approval:

1. `get_campaign_status(campaign_id)`
2. Human reviews assets
3. `approve_campaign(campaign_id)` or `approve_campaign_kit(kit_id)`
4. Only then `export_campaign` / `export_campaign_kit`

Never auto-publish.

## 7. Resume

If interrupted:

```text
resume_campaign(campaign_id)
```

If already `APPROVAL_PENDING`, resume returns a message and does not invent approval.

## 8. Credentials

| Need | Variable | Required for |
|---|---|---|
| Offline tests / mock | `LLM_PROVIDER=mock` | CI, dry-runs |
| Anthropic | `ANTHROPIC_API_KEY` | live anthropic |
| OpenAI | `OPENAI_API_KEY` | live openai |
| Gemini | `GEMINI_API_KEY` | live gemini |
| Remote MCP | `MCP_AUTH_TOKEN` or `MCP_API_KEY` | HTTP transports |

Do not paste secrets into chat. Use `.env` from `.env.example`.

## Autonomous vs human-controlled

### Autonomous (safe with `LLM_PROVIDER=mock`)

```text
Health Check
 → Create Campaign
 → Strategy / Event Intelligence
 → Content / Social / Repurpose
 → Brand Check
 → QA (+ optimize loop)
 → Approval Pending (stop)
 → Status / Resume
```

### Human-controlled (hard gates)

```text
Review assets
 → approve_campaign / approve_campaign_kit
 → export_campaign / export_campaign_kit
 → any external publish / paid media / Salesforce action
```

No automation may export or publish without `APPROVED` status.

## Future Cursor Automation sketch

A scheduled or webhook Cursor Automation can:

1. Trigger on brief intake (Slack/GitHub/webhook — configured in Automations UI)
2. Call agent instructions: run `create_campaign`, post status summary
3. Notify a human for approval
4. On approval signal, call `export_campaign`

Configure that automation in the **Cursor Automations** editor (Agents Window). This repository provides the MCP tools and agent instructions; it does not embed Cursor Automation secrets.

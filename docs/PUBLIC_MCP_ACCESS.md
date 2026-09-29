# Public MCP access for team clients (Claude / ChatGPT / Gemini / Cursor)

## Important distinction

| Thing | Public? | GitHub login required? |
|---|---|---|
| This **GitHub repository** (clone/read) | Yes (public repo) | No for clone/read |
| **MCP tool server** | Only if **you host** it | **Never** for MCP — use service token |

A public GitHub repository is **not** an MCP endpoint. Clients talk to an MCP **transport**, not to `github.com`.

```text
Claude / ChatGPT / Gemini / Cursor
        ↓
MCP Transport (stdio local  |  Streamable HTTP / SSE remote)
        ↓
Auth (local trust  |  MCP_AUTH_TOKEN service credential)
        ↓
Content MCP (16 tools)
        ↓
Campaign Orchestrator
        ↓
QA → Human Approval → Export
```

## What is accessible without GitHub login

1. **Clone** this public repository.
2. **Run local MCP** via stdio (`./scripts/run-mcp.sh`) — no GitHub auth.
3. **Call a team-hosted remote MCP** URL with `MCP_AUTH_TOKEN` / `MCP_API_KEY` — still no GitHub login.

## What requires authentication (not GitHub)

Remote HTTP/SSE MCP must set:

- `MCP_AUTH_TOKEN` or `MCP_API_KEY` (service credential)
- Restricted `CORS_ALLOWED_ORIGINS` in production

Binding `0.0.0.0` without a token is refused by the server.

## Protected / write-oriented operations

Always treat as privileged (see `clients/access.py`):

- `create_campaign`, `resume_campaign`
- `approve_campaign`, `approve_campaign_kit`
- `export_campaign`, `export_campaign_kit`
- generation / optimize / refine / social / repurpose tools

Human approval remains mandatory before export.

## Client setup

### Claude Desktop / Claude Code (local stdio)

Use `config/claude_desktop_config.example.json` — points at local `uv run … clients.claude.server`.

No GitHub login. No remote token for stdio.

### Cursor (local stdio)

Same stdio config as Claude. Open the repo, run `./scripts/setup.sh`, then Agent mode.

### ChatGPT (remote Streamable HTTP)

1. Deploy with Docker Compose (`docker-compose.yml`) or any host running:

```bash
export MCP_AUTH_TOKEN="replace-me"
./scripts/run-mcp.sh http   # or docker compose up
```

2. Point ChatGPT MCP connector at `https://YOUR_HOST/mcp` (path depends on SDK mount) with the service token.
3. Do **not** use a GitHub PAT as the MCP token.

### Gemini

Use `clients/gemini/adapter.py` tool definitions against the same local stdio server or authenticated remote HTTP endpoint.

## Local development

```bash
./scripts/setup.sh
./scripts/run-mcp.sh          # stdio
./scripts/run-mcp.sh http     # 127.0.0.1:8000
```

## Remote deployment (team hosted)

```bash
cp .env.example .env   # set MCP_AUTH_TOKEN, CORS, optional LLM keys
docker compose up --build -d
```

There is **no** first-party hosted public MCP URL shipped by this repository. Operators must deploy the container/process above.

## Environment variables

See `.env.example` — MCP, LLM providers, CORS. Never commit `.env`.

## Security model

- GitHub OAuth/login is **not** part of the MCP auth path.
- Remote MCP uses shared service tokens.
- Local stdio trusts the workstation user.
- Export/approve stay gated by campaign state machine + human approval.
- Secrets must never appear in logs or commits.

## Human approval

```text
QA → APPROVAL_PENDING → HUMAN APPROVAL → APPROVED → EXPORT
```

Automations may create/QA content; they must not invent approval.

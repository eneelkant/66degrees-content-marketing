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

### Public HTTPS (Render)

Use the existing root `Dockerfile` and `render.yaml`. Do not put tokens in the image or in git.

1. In the Render Dashboard, create a Blueprint from this repository (or a Web Service with Docker runtime).
2. Instance type: **Free**. Do not select a paid plan.
3. Branch: `main`. The image `EXPOSE` and start command use port **8000**. `render.yaml` sets `PORT=8000` so Render routes to that port.
4. Health check path: `/health` (GET, no token). Expected body: `{"status":"ok"}`.
5. Environment variables (Render secrets, not git):
   - `MCP_AUTH_TOKEN` — `render.yaml` sets `generateValue: true`. Render stores the value. Do not copy it into the repo or chat.
   - `CORS_ALLOWED_ORIGINS` — `https://chatgpt.com,https://claude.ai,https://gemini.google.com`. Do not use `*`.
   - `LLM_PROVIDER=mock` unless a live provider key is also set in Render.
6. Leave `MCP_PUBLIC_HOST` unset unless you add a custom domain. Render injects `RENDER_EXTERNAL_HOSTNAME`, and the server allowlists that hostname at startup.
7. Keep a single instance (`numInstances: 1`). Campaign session state is in memory. Free instances may sleep after inactivity.

Public URLs after deploy:

- `https://<DOMAIN>/mcp` — Streamable HTTP, `Authorization: Bearer <MCP_AUTH_TOKEN>` or `X-Api-Key`
- `https://<DOMAIN>/health` — `{"status":"ok"}`

`/health` is public. `/mcp` rejects missing or invalid credentials and rejects an `Origin` that is not on the allowlist. Clients that omit `Origin` (Cursor, Claude, ChatGPT, Gemini server-side) are allowed through the CORS check and still require the service token.

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

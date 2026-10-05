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

Remote clients use the deployed Streamable HTTP endpoint. They do not need to clone this repository or install Python or uv.

Production endpoint:

- `https://six6degrees-content-mcp.onrender.com/mcp`
- `https://six6degrees-content-mcp.onrender.com/health`

Put `MCP_AUTH_TOKEN` in the client configuration. The value lives in Render. Do not commit it and do not paste it into chat. `Authorization: Bearer <MCP_AUTH_TOKEN>` and `X-Api-Key` are both accepted. Requests without a matching token receive HTTP 401.

### Cursor (remote Streamable HTTP)

Use `config/cursor_remote_mcp.example.json` in Cursor MCP settings. Cursor desktop sends `Origin: vscode-file://vscode-app`. That origin is accepted and still requires the service token. Do not rely on OAuth for this server: OAuth discovery answers HTTP 404 so Cursor keeps the configured `Authorization` header.

### Cursor (local stdio)

Clone the repo and use the same stdio command as Claude (`config/claude_desktop_config.example.json`). Local stdio does not use the production token.

### Claude (remote Streamable HTTP)

Use `config/claude_remote_mcp.example.json`, or add the production URL in Claude Desktop / Claude.ai as a custom HTTP connector with the bearer token. Browser calls from `https://claude.ai` are on the CORS allowlist.

### Claude (local stdio)

Use `config/claude_desktop_config.example.json`. No remote token.

### Gemini (remote Streamable HTTP)

Use `config/gemini_remote_mcp.example.json` (`httpUrl` plus the bearer header). Browser calls from `https://gemini.google.com` are on the CORS allowlist.

### Gemini (local stdio)

Use `clients/gemini/gemini_cli_config.json`. That command runs the local server and requires a checkout.

### ChatGPT (remote Streamable HTTP)

Point the ChatGPT MCP connector or OpenAI Agents config at the production `/mcp` URL and supply the service token in the client. `clients/chatgpt/openai_agents_config.json` lists the 16 tools. Browser calls from `https://chatgpt.com` are on the CORS allowlist. Do **not** use a GitHub PAT as the MCP token.

Local Docker remains available for operators:

```bash
export MCP_AUTH_TOKEN="replace-me"
./scripts/run-mcp.sh http   # or docker compose up
```

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

`/health` is public. `/mcp` rejects missing or invalid credentials. Browser origins must be the configured list (`https://chatgpt.com`, `https://claude.ai`, `https://gemini.google.com`). Cursor's desktop origin `vscode-file://vscode-app` is also accepted because a website cannot set it. Clients that omit `Origin` still require the service token. `https://evil.example` and `Origin: null` are rejected. CORS is never `*`.

## Environment variables

See `.env.example` — MCP, LLM providers, CORS. Never commit `.env`.

Optional source retrieval, used only when a brief sets `sources.slack` or `sources.drive`:

- `SLACK_BOT_TOKEN` — Slack bot token. Missing token returns `credentials_missing` and no messages.
- `GOOGLE_DRIVE_ACCESS_TOKEN` — OAuth access token. Reads stay in memory. A Google Doc append happens only after approval when `drive_update.confirm` is boolean `true`.

Do not commit either token. CI does not need them. Details are in `docs/CONTENT_QUALITY_AND_SOURCES.md`.

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

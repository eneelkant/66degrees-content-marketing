# 66degrees Content Marketing

Step 4: Reference Library & Brand Context Engine.

- SQLite: structured metadata and performance filtering.
- ChromaDB + local sentence-transformers: optional semantic retrieval adapter.
- Hybrid score: `0.4 * semantic + 0.5 * performance + 0.1 * recency`.
- Brand rules: approved terminology, forbidden jargon, voice, personality, strategic pillars.
- Reference refresh cadence: 45 days.
- Competitor context is XML-wrapped as inspiration only and explicitly guarded against brand drift.

Install optional vector dependencies with `pip install -e '.[reference]'` when network access is available.

## Step 9: Quality & Validation Engine

`qa_validate_asset()` is the master QA gate. It chains:

- hard channel constraints for Google Ads and LinkedIn Ads;
- 66degrees brand-rule validation;
- two-tier originality analysis (RapidFuzz lexical similarity plus an optional Chroma semantic-distance adapter);
- Emailens local email QA via the repo-local `@emailens/engine` package;
- an explicit human approval gate before JSON campaign export.

Install the QA dependency with `pip install -e '.[qa]'`.

For Emailens, install the repo-local engine from `engines/emailens`:

```bash
cd engines/emailens
npm install
```

Emailens is invoked programmatically by `core/qa/emailens.py`; no separate Emailens MCP installation is required for this repository's QA pipeline. The local engine reports content/spam QA; domain-level SPF/DKIM/DMARC checks are not fabricated as a local deliverability score.

## Step 11: Multi-Client Integration

The repository exposes one locked public MCP surface of exactly 11 tools. Specialist strategies remain internal Python capabilities and are not exposed as MCP tools.

Supported clients:

- **Claude Desktop:** stdio FastMCP adapter at `clients/claude/server.py`.
- **ChatGPT/OpenAI:** Streamable HTTP is the preferred remote MCP transport; legacy SSE is available through `clients/chatgpt/sse_server.py`. The OpenAI Agents SDK bridge is in `clients/chatgpt/agents.py`.
- **Gemini CLI:** uses the same stdio MCP server configuration. Gemini CLI also supports SSE and Streamable HTTP endpoints.
- **Gemini SDK:** provider-neutral function declarations are available in `clients/gemini/adapter.py`, with an optional `google-genai` wrapper in `clients/gemini/genai_adapter.py`.

The MCP Python SDK dependency is `mcp>=1.29,<2`; the project uses the SDK's stdio, SSE, and Streamable HTTP transports. Streamable HTTP is preferred for remote deployments, while SSE is retained for clients that still support the legacy transport.

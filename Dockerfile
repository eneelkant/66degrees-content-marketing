# syntax=docker/dockerfile:1
# Team-hosted MCP endpoint (no GitHub login required for clients).
# Auth uses MCP_AUTH_TOKEN / MCP_API_KEY service credentials — not GitHub OAuth.

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app \
    LLM_PROVIDER=mock \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml README.md ./
COPY clients ./clients
COPY config ./config
COPY core ./core
COPY exporters ./exporters
COPY engines ./engines
COPY mcp ./mcp
COPY scripts ./scripts
COPY references ./references

RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Bind 0.0.0.0 only when MCP_AUTH_TOKEN or MCP_API_KEY is provided at runtime.
CMD ["python", "-m", "clients.chatgpt.sse_server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]

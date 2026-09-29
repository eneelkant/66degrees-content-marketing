"""ChatGPT / remote MCP HTTP adapter with optional service-token auth.

Streamable HTTP is preferred; SSE remains for compatible clients.
GitHub login is never required for MCP consumption — use MCP_AUTH_TOKEN /
MCP_API_KEY as a service credential for remote transports.
"""
from __future__ import annotations

import argparse
import os

import uvicorn

from clients.claude.server import mcp
from clients.http_security import MCPAuthCORS
from config.settings import get_settings


def build_app(transport: str = "streamable-http"):
    """Return the ASGI app, wrapping with auth when remote credentials are configured."""
    if transport == "sse":
        app = mcp.sse_app()
    else:
        app = mcp.streamable_http_app()

    settings = get_settings()
    # Localhost binds may omit auth for developer convenience when no token is set.
    # Any non-loopback deploy must set MCP_AUTH_TOKEN or MCP_API_KEY.
    if settings.mcp_auth_token or settings.mcp_api_key:
        return MCPAuthCORS(app)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run remote MCP HTTP transport")
    parser.add_argument(
        "--transport",
        choices=("streamable-http", "sse"),
        default="streamable-http",
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8000")))
    args = parser.parse_args()

    settings = get_settings()
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not (
        settings.mcp_auth_token or settings.mcp_api_key
    ):
        raise SystemExit(
            "Refusing to bind remote MCP on non-loopback host without "
            "MCP_AUTH_TOKEN or MCP_API_KEY. Set a service token in .env "
            "(GitHub login is not used for MCP auth)."
        )

    app = build_app(args.transport)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

"""ChatGPT / remote MCP HTTP adapter with optional service-token auth.

Streamable HTTP is preferred; SSE remains for compatible clients.
GitHub login is never required for MCP consumption — use MCP_AUTH_TOKEN /
MCP_API_KEY as a service credential for remote transports.
"""
from __future__ import annotations

import argparse
import os

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from clients.claude.server import mcp
from clients.http_security import MCPAuthCORS
from config.settings import get_settings

_LOCAL_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
_LOCAL_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
_PLATFORM_HOST_ENV = (
    "MCP_PUBLIC_HOST",
    "RENDER_EXTERNAL_HOSTNAME",
    "RAILWAY_PUBLIC_DOMAIN",
)


def public_hostnames() -> list[str]:
    """Hostnames that may appear in the Host header on a public HTTPS deploy."""
    found: list[str] = []
    for key in _PLATFORM_HOST_ENV:
        for part in os.getenv(key, "").split(","):
            host = part.strip()
            if "://" in host:
                host = host.split("://", 1)[1]
            host = host.split("/", 1)[0].strip()
            if host and host not in found:
                found.append(host)
    return found


def configure_transport_security() -> None:
    """Allow the public hostname while keeping DNS-rebinding checks enabled.

    FastMCP otherwise allowlists only localhost, so a real Host header such as
    the Render service hostname is rejected with 421 before the MCP session starts.
    The hostname comes from the platform environment, not from source code.
    """
    hosts = list(_LOCAL_HOSTS)
    for host in public_hostnames():
        hosts.append(host)
        if not host.endswith(":*"):
            hosts.append(f"{host}:*")
    origins = list(_LOCAL_ORIGINS)
    for origin in get_settings().cors_allowed_origins:
        if origin and origin != "*" and origin not in origins:
            origins.append(origin)
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> JSONResponse:
    """Unauthenticated liveness probe for the HTTPS platform."""
    return JSONResponse({"status": "ok"})


def build_app(transport: str = "streamable-http"):
    """Return the ASGI app, wrapping with auth when remote credentials are configured."""
    configure_transport_security()
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

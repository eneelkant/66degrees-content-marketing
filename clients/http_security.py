"""ASGI auth and origin checks for remote Streamable HTTP / SSE MCP."""
from config.settings import get_settings
from core.security.auth import validate_credentials, AuthenticationError

# Cursor/VS Code desktop sends this Origin. Websites cannot set it.
# The service token is still required.
DESKTOP_CLIENT_ORIGINS = frozenset({"vscode-file://vscode-app"})

_OAUTH_DISCOVERY_ROOTS = (
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-authorization-server",
    "/.well-known/openid-configuration",
)

_CORS_ALLOW_HEADERS = (
    "authorization, content-type, accept, mcp-session-id, "
    "mcp-protocol-version, x-api-key, last-event-id"
)
_CORS_ALLOW_METHODS = "GET, POST, DELETE, OPTIONS"
_CORS_EXPOSE_HEADERS = "mcp-session-id"


def normalize_origin(origin: str) -> str:
    value = origin.strip()
    if len(value) > 1 and value.endswith("/"):
        value = value[:-1]
    return value


def allowed_origin_set(configured) -> set[str]:
    """Explicit browser origins plus known desktop MCP client origins."""
    found = set(DESKTOP_CLIENT_ORIGINS)
    for origin in configured or []:
        if not origin or origin == "*":
            continue
        found.add(normalize_origin(str(origin)))
    return found


def origin_allowed(origin, configured) -> bool:
    """Absent Origin is a non-browser MCP client. ``*`` is not emitted."""
    if origin is None or origin == "":
        return True
    normalized = normalize_origin(str(origin))
    if normalized.lower() == "null":
        return False
    configured_values = list(configured or [])
    if "*" in configured_values:
        return True
    return normalized in allowed_origin_set(configured_values)


def is_oauth_discovery(path: str) -> bool:
    """OAuth metadata probes must not look like a bad service token.

    A 401 on these paths makes Cursor start OAuth and ignore the configured
    Authorization header. This server uses a service token, so the probe is 404.
    """
    value = path or ""
    return any(value == root or value.startswith(root + "/") for root in _OAUTH_DISCOVERY_ROOTS)


def _header_map(scope) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, value in scope.get("headers") or []:
        name = key.decode("latin-1").lower()
        decoded = value.decode("latin-1").strip()
        if name not in found or not found[name]:
            found[name] = decoded
    return found


def _cors_headers(origin: str) -> list[tuple[bytes, bytes]]:
    return [
        (b"access-control-allow-origin", origin.encode("latin-1")),
        (b"vary", b"Origin"),
        (b"access-control-allow-credentials", b"true"),
        (b"access-control-expose-headers", _CORS_EXPOSE_HEADERS.encode("latin-1")),
    ]


class MCPAuthCORS:
    def __init__(self, app, expected_token=None, allowed_origins=None):
        self.app = app
        settings = get_settings()
        self.expected_token = expected_token or settings.mcp_auth_token or settings.mcp_api_key
        self.configured_origins = list(
            allowed_origins if allowed_origins is not None else settings.cors_allowed_origins
        )
        self.allowed_origins = set(self.configured_origins)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path") or ""
        method = scope.get("method") or ""
        # Platform probes must not send the MCP service token.
        if path == "/health" and method in {"GET", "HEAD"}:
            return await self.app(scope, receive, send)
        if is_oauth_discovery(path):
            return await self._reject(send, 404, "Not found")
        headers = _header_map(scope)
        origin = headers.get("origin")
        if not origin_allowed(origin, self.configured_origins):
            return await self._reject(send, 403, "Origin not allowed")
        cors_origin = normalize_origin(origin) if origin else None
        if method == "OPTIONS":
            extra = _cors_headers(cors_origin) if cors_origin else []
            extra.extend(
                [
                    (b"access-control-allow-methods", _CORS_ALLOW_METHODS.encode("latin-1")),
                    (b"access-control-allow-headers", _CORS_ALLOW_HEADERS.encode("latin-1")),
                    (b"access-control-max-age", b"600"),
                ]
            )
            return await self._reject(send, 204, "", extra)
        try:
            validate_credentials(
                authorization=headers.get("authorization"),
                api_key=headers.get("x-api-key"),
                expected_token=self.expected_token,
            )
        except AuthenticationError as exc:
            extra = _cors_headers(cors_origin) if cors_origin else []
            return await self._reject(send, 401, str(exc), extra)

        async def send_with_cors(message):
            if cors_origin and message.get("type") == "http.response.start":
                merged = list(message.get("headers") or [])
                merged.extend(_cors_headers(cors_origin))
                message = {**message, "headers": merged}
            await send(message)

        return await self.app(scope, receive, send_with_cors)

    async def _reject(self, send, status, message, extra_headers=None):
        body = message.encode()
        headers = [
            [b"content-type", b"text/plain"],
            [b"content-length", str(len(body)).encode()],
        ]
        if extra_headers:
            headers.extend(list(item) for item in extra_headers)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

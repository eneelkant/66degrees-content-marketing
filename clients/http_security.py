"""Small ASGI security wrapper for remote MCP transports."""
from config.settings import get_settings
from core.security.auth import validate_credentials, AuthenticationError

class MCPAuthCORS:
    def __init__(self, app, expected_token=None, allowed_origins=None):
        self.app=app
        settings=get_settings()
        self.expected_token=expected_token or settings.mcp_auth_token or settings.mcp_api_key
        self.allowed_origins=set(allowed_origins or settings.cors_allowed_origins)
    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http": return await self.app(scope,receive,send)
        # Platform probes must not send the MCP service token.
        if scope.get("path") == "/health" and scope.get("method") in {"GET", "HEAD"}:
            return await self.app(scope, receive, send)
        headers={k.decode().lower():v.decode() for k,v in scope.get("headers",[])}
        origin=headers.get("origin")
        # Server-side MCP clients omit Origin. Reject only a present Origin
        # that is not on the allowlist.
        if origin and self.allowed_origins and "*" not in self.allowed_origins and origin not in self.allowed_origins:
            return await self._reject(send,403,"Origin not allowed")
        try:
            validate_credentials(authorization=headers.get("authorization"), api_key=headers.get("x-api-key"), expected_token=self.expected_token)
        except AuthenticationError as exc:
            return await self._reject(send,401,str(exc))
        return await self.app(scope,receive,send)
    async def _reject(self,send,status,message):
        body=message.encode()
        await send({"type":"http.response.start","status":status,"headers":[[b"content-type",b"text/plain"],[b"content-length",str(len(body)).encode()]]})
        await send({"type":"http.response.body","body":body})

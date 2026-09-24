"""Transport-oriented MCP auth helpers.

Prefer importing from ``core.security.auth`` in application code. This module
exists for discoverability under the ``mcp/`` directory without registering a
Python package named ``mcp`` (which would shadow the MCP SDK).
"""
from core.security.auth import AuthenticationError, extract_bearer, validate_credentials

__all__ = ["AuthenticationError", "extract_bearer", "validate_credentials"]

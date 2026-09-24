# This directory is intentionally not a Python package (no __init__.py).
# The installed dependency is also named `mcp`; adding __init__.py here would
# shadow the SDK and break `from mcp.server.fastmcp import FastMCP`.
#
# Auth helpers: auth.py (re-exports core.security.auth)
# MCP server entrypoints: clients.claude.server / scripts/run-mcp.sh

"""ChatGPT/remote MCP HTTP adapter.

The current MCP Python SDK supports both legacy SSE and Streamable HTTP. Streamable
HTTP is the preferred remote transport; SSE remains available for compatible clients.
"""
import argparse
from clients.claude.server import mcp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=("streamable-http", "sse"), default="streamable-http")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

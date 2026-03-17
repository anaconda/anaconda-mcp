"""
Minimal MCP server for reproducing the proxy hang bug.

This server has a single tool with configurable delay.
Used to demonstrate that the hang is in mcp-compose proxy,
not in the downstream server.

Usage:
    python echo_server.py
    DELAY=0.8 python echo_server.py  # simulate slow tool
"""

import os
import time

from mcp.server.fastmcp import FastMCP

# Configurable delay to simulate slow tools (like conda operations)
DELAY = float(os.environ.get("DELAY", "0.8"))

mcp = FastMCP("echo", host="127.0.0.1", port=7041)


@mcp.tool()
def ping(message: str = "pong") -> str:
    """Echo the message back (with optional delay)."""
    if DELAY > 0:
        time.sleep(DELAY)
    return message


if __name__ == "__main__":
    print(f"Starting echo server with DELAY={DELAY}s")
    mcp.run(transport="streamable-http")

"""
Suite-wide configuration constants.

Values are read from environment variables that conftest.pytest_configure
propagates from CLI options before any test module is imported.
"""

from __future__ import annotations

import os

# Full URL of the MCP server endpoint.
# Set by conftest from --server-url / MCP_SERVER_URL before test collection.
BASE_URL: str = os.environ.get("MCP_SERVER_URL", "http://localhost:8888/mcp")

# Maximum seconds to wait for a single tool call response.
# A normal error response takes <30 s; the hang bug lasted until the SSE
# timeout (~5 min), so 60 s is enough to catch a regression reliably.
TOOL_TIMEOUT: int = 60

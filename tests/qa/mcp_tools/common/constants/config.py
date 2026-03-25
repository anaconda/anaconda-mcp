"""
Suite-wide configuration constants.

Values are read from environment variables that conftest.pytest_configure
propagates from CLI options before any test module is imported.
"""

from __future__ import annotations

import os

# Full URL of the MCP server endpoint.
# Set by conftest from --server-url / MCP_SERVER_URL before test collection.
# Default port 9888 avoids conflict with IDE MCP servers (Cursor, Claude Desktop use 8888).
BASE_URL: str = os.environ.get("MCP_SERVER_URL", "http://localhost:9888/mcp")

# Downstream server port (environments_mcp_server).
# Default 5041 avoids conflict with IDE downstream servers (typically 4041).
DOWNSTREAM_PORT: int = int(os.environ.get("MCP_DOWNSTREAM_PORT", "5041"))

# Maximum seconds to wait for a single tool call response.
# A normal error response takes <30 s; the hang bug lasted until the SSE
# timeout (~5 min), so 60 s is enough to catch a regression reliably.
TOOL_TIMEOUT: int = 60

# Wall-clock cap for the whole tools/call (POST + body read); see mcp_client.
# pytest-timeout on a test must be >= this if the test uses _call_tool.
TOOL_CALL_WALL_SECONDS: int = TOOL_TIMEOUT + 25

# Number of back-to-back iterations used by KI-011 hang-regression tests to
# accumulate the session state that triggered the production hang (~47 min of
# use). Raising this value increases detection confidence at the cost of
# longer test runtime.
WARM_ITERATIONS: int = 20

# Delay (in seconds) between iterations in hang regression tests.
# Adding a delay can help avoid triggering KI-011 connection pool exhaustion.
# Set to 0 to disable delay (original behavior that triggers hang at ~15 iterations).
ITERATION_DELAY: float = float(os.environ.get("MCP_TEST_ITERATION_DELAY", "2.0"))

"""
Reusable test data constants for the stdio_tools suite.
"""

from __future__ import annotations

# Absolute path guaranteed not to be a real conda environment prefix.
# Used to trigger "environment not found" error responses without touching
# any real environment.
NONEXISTENT_ENV_PREFIX = "/tmp/nonexistent-conda-env-xyz123"

# Package name guaranteed not to exist in any conda channel.
NONEXISTENT_PKG = "this-package-does-not-exist-xyz123abc"

# Failure message template for KI-011 hang regression tests.
# Formatted with timeout, iteration, and total at assertion time.
HANG_FAIL_MSG = (
    "mcp-compose STDIO proxy did not forward the error response from "
    "environments_mcp_server within {timeout}s (iteration {iteration}/{total}). "
    "The internal HTTP session to port 4042 was likely abandoned. "
    "Matches the KI-011 hang pattern — the race condition in mcp-compose's "
    "internal Streamable HTTP pool is NOT gated on upstream transport. "
    "Observed on 2026-03-06 with STDIO transport, Python 3.13."
)

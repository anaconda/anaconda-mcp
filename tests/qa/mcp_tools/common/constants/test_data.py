"""
Reusable test data constants for the http_tools suite.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

# Ephemeral conda environment created and destroyed per test module.
ENV_NAME = "guard-api-test"

# Ephemeral conda environment used for removal operation tests (KI-003).
REMOVABLE_ENV_NAME = "guard-env-remove-test"

# Package name guaranteed not to exist in any conda channel.
NONEXISTENT_PKG = "nonexistent-package-xyz123"

# Small, real package available in conda defaults; used for happy-path install tests.
EXISTING_PKG = "pyyaml"

# Absolute path guaranteed not to be a real conda environment prefix.
# Used to trigger "environment not found" error responses from tools that
# accept a prefix argument, without creating or removing any real environment.
# Uses tempfile.gettempdir() for cross-platform compatibility (Windows vs Unix).
NONEXISTENT_ENV_PREFIX = str(Path(tempfile.gettempdir()) / "nonexistent-conda-env-xyz123")

# Failure message template for KI-011 hang-regression tests.
# Placeholders: {timeout} seconds, {iteration} current pass, {total} total passes.
KI011_HANG_FAIL_MSG = (
    "mcp-compose proxy did not forward the error response from "
    "environments_mcp_server within {timeout}s (iteration {iteration}/{total}). "
    "The backend HTTP session to the downstream server was likely abandoned "
    "(missing 5th POST + DELETE). Matches the KI-011 hang pattern. "
    "Observed on 2026-03-05 with Streamable HTTP transport, Python 3.13."
)

# Alias for unified hang tests (historical stdio_tools name).
HANG_FAIL_MSG = KI011_HANG_FAIL_MSG

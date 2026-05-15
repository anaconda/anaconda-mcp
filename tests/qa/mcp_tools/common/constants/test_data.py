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

# Environment name guaranteed not to exist.
NONEXISTENT_ENV_NAME = "nonexistent-env-xyz123"

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

# =============================================================================
# conda-meta-mcp test data
# =============================================================================

# Known import name that maps to a conda package.
KNOWN_IMPORT = "yaml"
KNOWN_IMPORT_PACKAGE = "pyyaml"

# PyPI to conda package mapping test data.
PYPI_PACKAGE = "PyYAML"
CONDA_PACKAGE = "pyyaml"

# Package search test data — ubiquitous packages always available.
SEARCH_PACKAGE = "numpy"
SEARCH_PACKAGE_WITH_VERSION = "numpy>=1.20"

# Repoquery test data.
REPOQUERY_SPEC = "python"
REPOQUERY_CHANNEL = "defaults"

# File path search pattern (common across conda envs).
FILE_PATH_PATTERN = "yaml/__init__.py"

# =============================================================================
# search-mcp test data
# =============================================================================

# Broad queries that always return results.
SEARCH_QUERY_PACKAGES = "numpy"
SEARCH_QUERY_DOCS = "conda"
SEARCH_QUERY_FORUM = "install"
SEARCH_QUERY_COLLECTIONS = "data"
SEARCH_QUERY_ENVIRONMENTS = "python"

# Empty query for error path tests.
EMPTY_QUERY = ""

# Unknown/nonexistent values for error path tests.
UNKNOWN_IMPORT = "nonexistent_module_xyz123"
NONEXISTENT_PACKAGE_SPEC = "nonexistent-package-xyz123"

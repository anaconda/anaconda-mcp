"""
Shared pytest configuration for the stdio_tools test suite.

Unlike http_tools/conftest.py, there is no HTTP server fixture here.
Each test file spawns its own mcp-compose subprocess over STDIO and manages
the full lifecycle (start, initialize, teardown) inside its own fixture.

Provides:
- CLI option: --server-conda-env  (conda env with anaconda-mcp installed)
- HTML report metadata injection
"""

from __future__ import annotations

import os

import pytest


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--server-conda-env",
        default=os.environ.get("MCP_SERVER_CONDA_ENV", "anaconda-mcp-rc-py313"),
        metavar="ENV",
        help=(
            "Conda environment with anaconda-mcp installed. "
            "Also reads MCP_SERVER_CONDA_ENV env var. "
            "(default: anaconda-mcp-rc-py313)"
        ),
    )
    parser.addoption(
        "--python-version",
        default=None,
        metavar="VERSION",
        help="Server Python version label for the HTML report (e.g. '3.13').",
    )


# ---------------------------------------------------------------------------
# HTML report metadata
# ---------------------------------------------------------------------------

def pytest_sessionstart(session: pytest.Session) -> None:
    config = session.config
    metadata: dict | None = getattr(config, "_metadata", None)
    if metadata is None:
        return

    metadata["Transport"] = "STDIO"
    metadata["Server conda env"] = config.getoption("--server-conda-env")

    py_ver = config.getoption("--python-version")
    metadata["Server Python"] = py_ver if py_ver else "(not set — use --python-version)"

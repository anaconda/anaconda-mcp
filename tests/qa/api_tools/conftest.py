"""
Shared pytest fixtures and configuration for the api_tools test suite.

Provides:
- CLI options: --server-url, --transport, --python-version,
                --start-server, --server-conda-env
- Session fixture: mcp_server  (starts / verifies the server)
- Session fixture: server_url  (the resolved MCP endpoint URL)
- HTML report metadata injection
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import httpx
import pytest

# ---------------------------------------------------------------------------
# Shared helpers (used both in conftest and tests)
# ---------------------------------------------------------------------------

_INIT_BODY = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "preflight", "version": "1.0"},
    },
}
_SSE_HEADERS = {"Accept": "application/json, text/event-stream"}

_SCRIPT_PATH = (
    Path(__file__).parent.parent / "_ai_docs" / "scripts" / "start-http-server.sh"
).resolve()


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--server-url",
        default=os.environ.get("MCP_SERVER_URL", "http://localhost:8888/mcp"),
        help=(
            "Full URL of the MCP server endpoint. "
            "Also reads MCP_SERVER_URL env var. "
            "(default: http://localhost:8888/mcp)"
        ),
    )
    parser.addoption(
        "--transport",
        default="http",
        choices=["http"],
        help="Transport type — for report labeling only (currently only 'http' is supported).",
    )
    parser.addoption(
        "--python-version",
        default=None,
        metavar="VERSION",
        help="Python version of the server environment — for report labeling (e.g. '3.13').",
    )
    parser.addoption(
        "--start-server",
        action="store_true",
        default=False,
        help=(
            "Auto-start the MCP server before the test session using "
            "tests/qa/_ai_docs/scripts/start-http-server.sh. "
            "Requires --server-conda-env to have anaconda-mcp installed."
        ),
    )
    parser.addoption(
        "--server-conda-env",
        default="anaconda-mcp-rc-py313",
        metavar="ENV",
        help=(
            "Conda environment with anaconda-mcp installed, used when "
            "--start-server is set. (default: anaconda-mcp-rc-py313)"
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    """
    Propagate --server-url → MCP_SERVER_URL so test modules that read the
    env var at import time pick up the correct URL before collection starts.
    """
    try:
        url = config.getoption("--server-url")
        if url:
            os.environ["MCP_SERVER_URL"] = url
    except ValueError:
        pass  # option not yet registered (e.g. during --help)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def server_url(request: pytest.FixtureRequest) -> str:
    """Resolved MCP server endpoint URL for this session."""
    return request.config.getoption("--server-url")


@pytest.fixture(scope="session", autouse=True)
def mcp_server(request: pytest.FixtureRequest, server_url: str):
    """
    Session-scoped fixture that either:

    - Auto-starts the MCP server via start-http-server.sh when --start-server
      is passed, then tears it down after all tests complete.
    - Verifies a pre-running server is reachable; skips the session if not.
    """
    server_proc: subprocess.Popen | None = None

    if request.config.getoption("--start-server"):
        conda_env = request.config.getoption("--server-conda-env")
        port = _port_from_url(server_url)

        if not _SCRIPT_PATH.exists():
            pytest.fail(
                f"Server start script not found: {_SCRIPT_PATH}\n"
                "Ensure tests/qa/_ai_docs/scripts/start-http-server.sh exists."
            )
        if not shutil.which("conda"):
            pytest.fail("conda not found in PATH; cannot auto-start the server.")

        server_proc = subprocess.Popen(
            ["conda", "run", "-n", conda_env, "--no-capture-output",
             "bash", str(_SCRIPT_PATH), port],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # own process group → clean SIGTERM
        )

        _wait_for_server(server_url, timeout=60, on_timeout=lambda: (
            server_proc.kill(),
            pytest.fail(
                f"MCP server at {server_url} did not become ready within 60 s.\n"
                f"Check that conda env '{conda_env}' has anaconda-mcp installed."
            ),
        ))

    else:
        _assert_server_reachable(server_url)

    yield

    if server_proc is not None:
        try:
            os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            server_proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server_proc.kill()


# ---------------------------------------------------------------------------
# HTML report metadata
# ---------------------------------------------------------------------------

def pytest_sessionstart(session: pytest.Session) -> None:
    """Inject test-run configuration into the HTML report."""
    config = session.config
    metadata: dict | None = getattr(config, "_metadata", None)
    if metadata is None:
        return

    metadata["Server URL"] = config.getoption("--server-url")
    metadata["Transport"] = config.getoption("--transport").upper()

    py_ver = config.getoption("--python-version")
    metadata["Server Python"] = py_ver if py_ver else "(not set — use --python-version)"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _port_from_url(url: str) -> str:
    """Extract the port string from a URL like http://localhost:8888/mcp."""
    try:
        return url.rstrip("/").rsplit(":", 1)[-1].split("/")[0]
    except (IndexError, ValueError):
        return "8888"


def _wait_for_server(url: str, *, timeout: float, on_timeout) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.post(url, json=_INIT_BODY, headers=_SSE_HEADERS, timeout=3)
            if r.status_code in (200, 202, 406):
                return
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(2)
    on_timeout()


def _assert_server_reachable(url: str) -> None:
    try:
        httpx.post(url, json=_INIT_BODY, headers=_SSE_HEADERS, timeout=5)
    except httpx.ConnectError:
        pytest.skip(
            f"MCP server not reachable at {url}.\n"
            "Start it first:  ./tests/qa/_ai_docs/scripts/start-http-server.sh 8888\n"
            "Or pass --start-server to start automatically."
        )

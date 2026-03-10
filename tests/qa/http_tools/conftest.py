"""
Shared pytest fixtures and configuration for the http_tools test suite.

Provides:
- CLI options: --server-url, --transport, --python-version,
                --start-server, --server-conda-env
- Session fixture: mcp_server  (starts / verifies the server)
- Session fixture: server_url  (the resolved MCP endpoint URL)
- Module fixture: session_id   (MCP initialize handshake; one per test file)
- Module fixture: conda_env    (ephemeral conda env; created once per file)
- HTML report metadata injection
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
import pytest

from common.constants.test_data import ENV_NAME
from common.utils.conda_utils import _conda_env_prefix
from common.utils.mcp_client import _initialize_session

logger = logging.getLogger(__name__)

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
        default=os.environ.get("MCP_SERVER_URL", "http://localhost:9888/mcp"),
        help=(
            "Full URL of the MCP server endpoint. "
            "Also reads MCP_SERVER_URL env var. "
            "Uses port 9888 by default to avoid conflict with IDE MCP servers. "
            "(default: http://localhost:9888/mcp)"
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
        default=os.environ.get("MCP_SERVER_CONDA_ENV", "anaconda-mcp-rc-py313"),
        metavar="ENV",
        help=(
            "Conda environment with anaconda-mcp installed, used when "
            "--start-server is set. "
            "Also reads MCP_SERVER_CONDA_ENV env var. "
            "(default: anaconda-mcp-rc-py313)"
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

        log_file = tempfile.NamedTemporaryFile(
            mode="w", suffix="-anaconda-mcp.log", delete=False
        )
        log_path = Path(log_file.name)

        logger.info("Starting MCP server (conda env: %s, port: %s)", conda_env, port)
        server_proc = subprocess.Popen(
            ["conda", "run", "-n", conda_env, "--no-capture-output",
             "bash", str(_SCRIPT_PATH), port],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # own process group → clean SIGTERM
        )

        def _on_timeout() -> None:
            server_proc.kill()
            log_file.flush()
            try:
                tail = log_path.read_text()[-3000:]
            except Exception:
                tail = "(could not read log)"
            logger.error("MCP server did not become ready within 60 s. Log tail:\n%s", tail)
            pytest.fail(
                f"MCP server at {server_url} did not become ready within 60 s.\n"
                f"Conda env: '{conda_env}'\n"
                f"Log ({log_path}):\n{tail}"
            )

        _wait_for_server(server_url, timeout=60, on_timeout=_on_timeout)
        logger.info("MCP server is ready at %s", server_url)

    else:
        _assert_server_reachable(server_url)

    yield

    if server_proc is not None:
        logger.info("Stopping MCP server (pid %s)", server_proc.pid)
        try:
            os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            server_proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        try:
            log_file.close()
            log_path.unlink(missing_ok=True)
        except Exception:
            pass


@pytest.fixture(scope="module")
def session_id(mcp_server, server_url: str) -> str | None:
    """
    Initialize an MCP session and return the session ID (may be None).

    Module-scoped so each test file gets its own MCP session, keeping
    test files isolated from each other.
    """
    return _initialize_session(server_url, client_name="api-tools-test")


@pytest.fixture
def fresh_session_id(mcp_server, server_url: str) -> str | None:
    """
    Function-scoped MCP session for tests that need per-test session isolation.

    Each test gets a fresh session so a hang triggered by one test (which
    permanently corrupts mcp-compose's internal connection pool) does not
    cascade into subsequent tests. Use instead of session_id in hang regression
    tests.
    """
    return _initialize_session(server_url, client_name="api-tools-hang-test")


@pytest.fixture(scope="module")
def conda_env():
    """
    Create the guard-api-test conda environment once for the module; remove it after.

    Module-scoped so the environment is shared across all tests in a file but
    never bleeds into other test files.
    """
    logger.info("Creating conda environment '%s'", ENV_NAME)
    subprocess.run(
        ["conda", "create", "-n", ENV_NAME, "python=3.11", "-y"],
        check=True,
    )
    prefix = _conda_env_prefix(ENV_NAME)
    logger.debug("Conda env '%s' prefix: %s", ENV_NAME, prefix)
    yield {"name": ENV_NAME, "prefix": prefix}
    logger.info("Removing conda environment '%s'", ENV_NAME)
    subprocess.run(
        ["conda", "remove", "-n", ENV_NAME, "--all", "-y"],
        check=False,
    )


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
    """Extract the port string from a URL like http://localhost:9888/mcp."""
    try:
        return url.rstrip("/").rsplit(":", 1)[-1].split("/")[0]
    except (IndexError, ValueError):
        return "9888"


def _wait_for_server(url: str, *, timeout: float, on_timeout) -> None:
    logger.info("Waiting for MCP server at %s (timeout=%ss)", url, timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.post(url, json=_INIT_BODY, headers=_SSE_HEADERS, timeout=3)
            logger.debug("Server probe: HTTP %s", r.status_code)
            if r.status_code in (200, 202, 406):
                return
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(2)
    on_timeout()


def _assert_server_reachable(url: str) -> None:
    logger.info("Checking MCP server reachability at %s", url)
    try:
        httpx.post(url, json=_INIT_BODY, headers=_SSE_HEADERS, timeout=5)
        logger.info("MCP server is reachable at %s", url)
    except httpx.ConnectError:
        logger.error("MCP server not reachable at %s", url)
        pytest.skip(
            f"MCP server not reachable at {url}.\n"
            "Start it first:  ./tests/qa/_ai_docs/scripts/start-http-server.sh\n"
            "Or pass --start-server to start automatically."
        )

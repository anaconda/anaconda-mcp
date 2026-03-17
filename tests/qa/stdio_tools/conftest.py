"""
Shared pytest configuration and fixtures for the stdio_tools test suite.

Provides:
- CLI option: --server-conda-env  (conda env with anaconda-mcp installed)
- CLI option: --python-version    (for HTML report labeling)
- Function fixture: stdio_server  (spawns mcp-compose over STDIO; one per test)
- HTML report metadata injection
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess

import pytest
from common.constants.config import DOWNSTREAM_PORT
from common.constants.test_data import ENV_NAME
from common.utils.stdio_client import _recv, _send, _write_stdio_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """
    Propagate --server-conda-env → MCP_SERVER_CONDA_ENV so test modules that
    read the env var at import time pick up the correct value before collection.
    """
    try:
        env = config.getoption("--server-conda-env")
        if env:
            os.environ["MCP_SERVER_CONDA_ENV"] = env
    except ValueError:
        pass  # option not yet registered (e.g. during --help)


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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stdio_server(request: pytest.FixtureRequest):
    """
    Spawn anaconda-mcp serve in STDIO mode and yield the ready subprocess.

    Function-scoped — each test gets a fresh mcp-compose process so a hang
    triggered by one test does not corrupt subsequent tests.

    Lifecycle: write STDIO config → spawn process → initialize handshake →
    yield → SIGTERM + cleanup.
    """
    conda_env = request.config.getoption("--server-conda-env")
    config_path = _write_stdio_config(DOWNSTREAM_PORT, conda_env)
    logger.info(
        "Starting mcp-compose STDIO server (env=%s, downstream_port=%d, config=%s)",
        conda_env,
        DOWNSTREAM_PORT,
        config_path,
    )

    proc = subprocess.Popen(
        [
            "conda",
            "run",
            "-n",
            conda_env,
            "--no-capture-output",
            "anaconda-mcp",
            "serve",
            "--config",
            str(config_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "stdio-hang-test", "version": "1.0"},
                },
            },
        )

        init_resp = _recv(proc, timeout=45)
        logger.info(
            "STDIO server ready — serverInfo: %s",
            init_resp.get("result", {}).get("serverInfo"),
        )

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    except Exception as exc:
        proc.kill()
        config_path.unlink(missing_ok=True)
        pytest.fail(f"STDIO server did not become ready: {exc}")

    yield proc

    logger.info("Tearing down STDIO server (pid=%d)", proc.pid)
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    config_path.unlink(missing_ok=True)
    logger.info("STDIO server stopped")


@pytest.fixture(scope="module")
def conda_env():
    """
    Create the guard-stdio-test conda environment once for the module; remove it after.

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


def _conda_env_prefix(name: str) -> str:
    """Return the absolute prefix path for a conda environment by name."""
    result = subprocess.run(
        ["conda", "info", "--envs", "--json"],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    for prefix in data.get("envs", []):
        if prefix.endswith(f"/{name}") or prefix.endswith(f"\\{name}"):
            return prefix
    raise ValueError(f"Conda environment '{name}' not found")


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

"""
Regression tests: GUARD-001-API

Covers two bugs triggered by GUARD-001 Step 1
("Install nonexistent-package-xyz123 in guard-test"):

  ERR-003a  conda_install_packages returns a false "environment not found"
            when the environment exists but is addressed by name.

  ERR-003b  conda_install_packages hangs indefinitely when addressed by
            prefix and the package does not exist (the call never returns).

Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.

See tests/qa/api_tools/README.md for setup and usage.
"""

from __future__ import annotations

import json
import os
import subprocess

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Reads MCP_SERVER_URL (set by conftest from --server-url) or falls back to
# MCP_PORT for backward-compat with the old env-var convention.
BASE_URL = os.environ.get(
    "MCP_SERVER_URL",
    f"http://localhost:{os.environ.get('MCP_PORT', '8888')}/mcp",
)

# Hang detection: a normal error response takes <30 s.
# The bug caused a hang lasting until SSE timeout (~5 min), so 60 s catches it.
TOOL_TIMEOUT = 60.0

ENV_NAME = "guard-api-test"
NONEXISTENT_PKG = "nonexistent-package-xyz123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tool_result(response_json: dict) -> dict:
    """Extract the parsed tool result dict from a tools/call response."""
    content = response_json.get("result", {}).get("content", [])
    text = next((c["text"] for c in content if c.get("type") == "text"), None)
    if text and text.strip().startswith("{"):
        return json.loads(text)
    return {}


def _conda_env_prefix(env_name: str) -> str:
    """Return the full prefix path for a named conda environment."""
    info = json.loads(
        subprocess.check_output(["conda", "info", "--json"], text=True)
    )
    matches = [p for p in info["envs"] if p.endswith(f"/{env_name}")]
    assert matches, f"Conda environment '{env_name}' not found"
    return matches[0]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def conda_env():
    """Create the guard-api-test environment once for the module; remove it after."""
    subprocess.run(
        ["conda", "create", "-n", ENV_NAME, "python=3.11", "-y"],
        check=True,
    )
    prefix = _conda_env_prefix(ENV_NAME)
    yield {"name": ENV_NAME, "prefix": prefix}
    subprocess.run(
        ["conda", "remove", "-n", ENV_NAME, "--all", "-y"],
        check=False,
    )


@pytest.fixture(scope="module")
def session_id(mcp_server):
    """Initialize an MCP session and return the session ID (may be None)."""
    response = httpx.post(
        BASE_URL,
        json={
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "guard-api-test", "version": "1.0"},
            },
        },
        headers={"Accept": "application/json, text/event-stream"},
        timeout=10,
    )
    sid = response.headers.get("mcp-session-id")

    # Send initialized notification (best-effort)
    headers = {"Accept": "application/json, text/event-stream"}
    if sid:
        headers["Mcp-Session-Id"] = sid
    try:
        httpx.post(
            BASE_URL,
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            headers=headers,
            timeout=5,
        )
    except Exception:
        pass

    return sid


def _parse_mcp_response(response: httpx.Response) -> dict:
    """
    Parse an MCP HTTP response that may be plain JSON or SSE-wrapped JSON.

    Streamable HTTP servers return responses as SSE events even on POST:
        event: message\r\ndata: {"jsonrpc":"2.0",...}\r\n\r\n

    Extract the JSON payload from the first `data:` line.
    """
    content_type = response.headers.get("content-type", "")
    text = response.text

    if "text/event-stream" in content_type or text.lstrip().startswith("event:"):
        for line in text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:"):].strip())
        raise ValueError(f"No data: line found in SSE response: {text!r}")

    return response.json()


def _call_tool(tool_name: str, arguments: dict, session_id: str | None) -> dict:
    """Call a tool and return the parsed JSON-RPC response. Raises on timeout."""
    headers = {"Accept": "application/json, text/event-stream"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    response = httpx.post(
        BASE_URL,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
        headers=headers,
        timeout=httpx.Timeout(connect=10, read=TOOL_TIMEOUT, write=10, pool=10),
    )
    response.raise_for_status()
    return _parse_mcp_response(response)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInstallNonexistentPackage:
    """
    Regression: conda_install_packages with a nonexistent package must return
    a proper error quickly — not hang and not misreport the environment.
    """

    def test_err_003a_by_name_no_false_env_not_found(self, conda_env, session_id):
        """
        ERR-003a: calling by environment name must NOT return 'environment not found'
        when the environment exists. The error must be about the package, not the env.

        Source:  install_packages.py catches conda.exceptions.ResolvePackageNotFound
                 and returns error_description = "Could not resolve the packages".
                 The bug causes EnvironmentLocationNotFound to be raised instead,
                 returning "The environment was not found." before ever reaching
                 the solver.
        """
        response = _call_tool(
            "conda_install_packages",
            {"environment": conda_env["name"], "packages": [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)
        error_desc = result.get("error_description", "").lower()

        # Negative: must not misreport the environment as missing
        assert "environment was not found" not in error_desc, (
            f"False 'environment not found' for existing env '{ENV_NAME}'. "
            f"Bug: EnvironmentLocationNotFound raised before package resolution. "
            f"Full error_description: {result.get('error_description')}"
        )

        # Positive: must report a package-resolution failure
        # install_packages.py → ResolvePackageNotFound → "Could not resolve the packages"
        assert "could not resolve the packages" in error_desc, (
            f"Expected 'Could not resolve the packages' (from ResolvePackageNotFound "
            f"in install_packages.py line 104), "
            f"got: {result.get('error_description')!r}"
        )

    def test_err_003a_by_name_returns_error(self, conda_env, session_id):
        """
        ERR-003a: calling by environment name must return is_error=true
        (package does not exist; no silent pip fallback).
        """
        response = _call_tool(
            "conda_install_packages",
            {"environment": conda_env["name"], "packages": [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)

        assert result.get("is_error") is True, (
            f"Expected is_error=true for nonexistent package '{NONEXISTENT_PKG}', "
            f"got: {result}"
        )

    def test_err_003b_by_prefix_does_not_hang(self, conda_env, session_id):
        """
        ERR-003b: calling by prefix must return within TOOL_TIMEOUT seconds.
        A ReadTimeout here means the server hung (regression of the reported bug).
        """
        try:
            response = _call_tool(
                "conda_install_packages",
                {"prefix": conda_env["prefix"], "packages": [NONEXISTENT_PKG]},
                session_id,
            )
        except httpx.ReadTimeout:
            pytest.fail(
                f"conda_install_packages hung for >{TOOL_TIMEOUT}s when called with "
                f"prefix='{conda_env['prefix']}' and a nonexistent package. "
                "Regression of the install-nonexistent-pkg hang bug."
            )

        result = _tool_result(response)
        assert result.get("is_error") is True, (
            f"Expected is_error=true for nonexistent package '{NONEXISTENT_PKG}', "
            f"got: {result}"
        )

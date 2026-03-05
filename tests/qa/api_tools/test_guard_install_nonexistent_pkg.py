"""
Regression tests: GUARD-001-API

Covers the confirmed defect in
environments_mcp_server/tools/environments/install_packages.py triggered by
GUARD-001 Step 1 ("Install nonexistent-package-xyz123 in guard-test").

── ERR-003a — false "environment not found" when called by name ─────────────────
anaconda_connector_conda creates a Context(search_path=()) (empty search path)
for each call. With an empty search path conda's context does not populate
envs_dirs, so context.target_prefix raises EnvironmentLocationNotFound when
resolving the environment name — before the solver is ever invoked.
install_packages.py:93 catches this and returns the wrong error.

Side-effect: the misleading "environment not found" causes the LLM to list
environments, find the prefix, and retry by prefix — producing extra tool calls.

Note: the handler at install_packages.py:100 (except ResolvePackageNotFound)
is unreachable dead code. The connector intercepts ResolvePackageNotFound and
re-raises it as PackageNotFoundError(CondaError) before it reaches this file.

── ERR-003b — indefinite hang when called by prefix ─────────────────────────────
Reproduced on Cursor / Streamable HTTP / Python 3.13.
Not observed on Claude Desktop / STDIO / Python 3.10.

Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
See tests/qa/api_tools/README.md for setup and usage.
"""

from __future__ import annotations

import logging
import threading
import time

import httpx
import pytest

from common.constants.config import BASE_URL, TOOL_TIMEOUT
from common.constants.mcp_tools import InstallPackagesArgs, ToolResultFields, Tools
from common.constants.test_data import ENV_NAME, NONEXISTENT_PKG
from common.utils.mcp_client import _call_tool, _tool_result
from common.utils.response_validators import _validate_package_resolution_error

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.slow
class TestInstallNonexistentPackage:
    """
    Regression: conda_install_packages with a nonexistent package must return
    a proper error quickly — not hang and not misreport the environment.
    """

    def test_err_003a_by_name_error_description(self, conda_env, session_id):
        """
        ERR-003a: calling by environment name must report a package-resolution
        failure — not 'environment not found' — when the environment exists.

        Source:  install_packages.py catches conda.exceptions.ResolvePackageNotFound
                 and returns error_description = "Could not resolve the packages".
                 The bug causes EnvironmentLocationNotFound to be raised instead,
                 returning "The environment was not found." before ever reaching
                 the solver.

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info("ERR-003a: installing nonexistent pkg by env name '%s'", ENV_NAME)
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.ENVIRONMENT: conda_env["name"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)
        _validate_package_resolution_error(result, conda_env["name"])

    def test_err_003a_by_name_returns_error(self, conda_env, session_id):
        """
        ERR-003a: calling by environment name must return is_error=true
        (package does not exist; no silent pip fallback).

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info("ERR-003a: verifying is_error flag for nonexistent pkg by env name")
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.ENVIRONMENT: conda_env["name"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)

        assert result.get(ToolResultFields.IS_ERROR) is True, (
            f"Expected is_error=true for nonexistent package '{NONEXISTENT_PKG}', "
            f"got: {result}"
        )

    def test_err_003b_by_prefix_error_description(self, conda_env, session_id):
        """
        ERR-003b (2a): calling by prefix must report 'Could not resolve the packages'
        for a nonexistent package — the same message as the by-name call after
        ERR-003a is fixed.

        Currently FAILS — dead code path in install_packages.py:

            The connector (transactions/env/base.py:202) catches
            conda.exceptions.ResolvePackageNotFound internally and re-raises it as
            PackageNotFoundError(CondaError). This wrapped exception bypasses the
            handler at install_packages.py:100 entirely:

                except conda_exceptions.ResolvePackageNotFound:   # line 100 — DEAD CODE
                    return "Could not resolve the packages"        # never reached

            and falls to the generic CondaError handler at line 112 instead,
            returning a connector-level message rather than the intended one.

            The handler at line 100 is unreachable for any call path (name or prefix).

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info("ERR-003b: verifying error description for nonexistent pkg by prefix")
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.PREFIX: conda_env["prefix"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)
        _validate_package_resolution_error(result, conda_env["name"])

    @pytest.mark.timeout(TOOL_TIMEOUT)
    def test_err_003b_by_prefix_does_not_hang(self, conda_env, session_id):
        """
        ERR-003b: calling by prefix must return within TOOL_TIMEOUT seconds.

        The timeout marker is the regression guard — if the server hangs, pytest
        kills the test and reports TIMEOUT instead of waiting until the SSE
        session expires (~5 min).

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info(
            "ERR-003b: installing nonexistent pkg by prefix '%s'", conda_env["prefix"]
        )
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.PREFIX: conda_env["prefix"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)
        assert result.get(ToolResultFields.IS_ERROR) is True, (
            f"Expected is_error=true for nonexistent package '{NONEXISTENT_PKG}', "
            f"got: {result}"
        )

    @pytest.mark.timeout(TOOL_TIMEOUT + 10)
    def test_err_003b_solve_blocks_concurrent_requests(self, conda_env, session_id):
        """
        ERR-003b (2b): solve_for_transaction() runs synchronously in the async event
        loop, blocking all concurrent requests while the conda solver is active.

        Mechanism: InstallTransaction.prepare() accesses self._status (a cached_property)
        synchronously before any await. _status accesses self.unlink_link_transaction,
        which calls solver.solve_for_transaction() — a blocking operation — directly
        on the event loop thread. asyncio.to_thread() is only used for the execute
        phase, which is never reached for a nonexistent package. On a cold repodata
        cache the solver fetches channel data over the network, blocking the event loop
        for the entire duration.

        Test strategy: send a prefix-based install (slow/blocking) and a tools/list
        (lightweight, < 500 ms normally) concurrently. If the event loop is blocked,
        tools/list cannot be processed until the solve completes, revealing the delay.

        CACHE NOTE: With warm repodata the solve takes < 100 ms and the block is not
        detectable by timing. Run with a cold cache (e.g. after `conda clean --all`)
        to reliably reproduce the delay.

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        FAST_REQUEST_THRESHOLD_S = 1.0

        light_latency: list[float] = []
        light_error: list[Exception] = []

        def run_light_request() -> None:
            time.sleep(0.3)  # let the install call reach the solver first
            headers = {"Accept": "application/json, text/event-stream"}
            if session_id:
                headers["Mcp-Session-Id"] = session_id
            t0 = time.monotonic()
            try:
                response = httpx.post(
                    BASE_URL,
                    json={"jsonrpc": "2.0", "id": 99, "method": "tools/list", "params": {}},
                    headers=headers,
                    timeout=TOOL_TIMEOUT,
                )
                response.raise_for_status()
            except Exception as exc:
                light_error.append(exc)
            finally:
                light_latency.append(time.monotonic() - t0)

        install_thread = threading.Thread(
            target=lambda: _call_tool(
                Tools.CONDA_INSTALL_PACKAGES,
                {InstallPackagesArgs.PREFIX: conda_env["prefix"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
                session_id,
            ),
            daemon=True,
        )
        light_thread = threading.Thread(target=run_light_request, daemon=True)

        logger.info("ERR-003b: starting concurrent install + tools/list")
        install_thread.start()
        light_thread.start()
        install_thread.join(timeout=TOOL_TIMEOUT)
        light_thread.join(timeout=TOOL_TIMEOUT)

        assert not light_error, f"Concurrent tools/list request failed: {light_error[0]}"
        assert light_latency, "Concurrent tools/list request did not complete"

        latency = light_latency[0]
        logger.info("ERR-003b: tools/list latency during concurrent solve: %.2fs", latency)
        assert latency < FAST_REQUEST_THRESHOLD_S, (
            f"ERR-003b: tools/list took {latency:.2f}s during concurrent prefix-based install "
            f"(expected < {FAST_REQUEST_THRESHOLD_S}s). "
            "The MCP server event loop is blocked: solve_for_transaction() runs "
            "synchronously on the event loop thread (not in asyncio.to_thread). "
            "Re-run with a cold repodata cache (conda clean --all) to reproduce reliably."
        )

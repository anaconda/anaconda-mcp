"""
Regression tests: KI-011 (happy-path variant) — mcp-compose proxy must forward
successful tool responses over STDIO transport without hanging.

Mirrors test_guard_happy_path_hang.py for the HTTP transport. The test process
communicates with mcp-compose over stdin/stdout (newline-delimited JSON-RPC).
mcp-compose's internal connection to environments_mcp_server is still Streamable
HTTP in STDIO mode — only the upstream transport differs.

Each test receives a fresh mcp-compose process via the function-scoped
stdio_server fixture (conftest.py). Tests that trigger the hang corrupt the
internal connection pool permanently; a fresh process per test prevents
cascading failures.

See tests/qa/_ai_docs/bug_details/proxy_hang/ for root-cause analysis and
reproduction scripts.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.config import TOOL_TIMEOUT, WARM_ITERATIONS
from common.constants.test_data import EXISTING_PKG
from common.utils.stdio_client import _call_no_hang, _is_error

pytestmark = pytest.mark.stdio_transport

logger = logging.getLogger(__name__)

# Calculate test timeouts including buffer for conda operations.
# First iteration may take longer (actual install), subsequent iterations are fast.
_BASE_TIMEOUT = int(TOOL_TIMEOUT * WARM_ITERATIONS) + 120  # +120s buffer for first install


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.slow
class TestHappyPathHangStdio:
    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_stdio_hang_004_repeated_install_does_not_hang(self, stdio_server, conda_env):
        """
        STDIO-HANG-004: conda_install_packages (success path) must return within
        TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls, over STDIO.
        Mirrors HTTP HANG-004.

        Installs EXISTING_PKG into a real environment. After the first
        iteration the package is already present so conda returns quickly, but
        the proxy must still complete the full round-trip for every call.

        Failure mode: proxy hangs on an inbound successful response, mirroring
        KI-011 but triggered by success rather than error.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "STDIO-HANG-004 [%d/%d] install_packages env=%s pkg=%s",
                i,
                WARM_ITERATIONS,
                conda_env["name"],
                EXISTING_PKG,
            )
            response, elapsed = _call_no_hang(
                stdio_server,
                "conda_install_packages",
                {
                    "environment": conda_env["name"],
                    "packages": [EXISTING_PKG],
                },
                f"STDIO-HANG-004: conda_install_packages (happy path) hung for > {TOOL_TIMEOUT}s "
                f"(iteration {i}/{WARM_ITERATIONS}). "
                "mcp-compose STDIO proxy did not forward the success response from "
                "environments_mcp_server. KI-011 happy-path variant.",
            )
            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-004 [%d/%d] done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                is_err,
            )
            assert not is_err, (
                f"STDIO-HANG-004 [{i}/{WARM_ITERATIONS}]: expected success for "
                f"install into '{conda_env['name']}', got error: {response}"
            )

    @pytest.mark.timeout(_BASE_TIMEOUT * 2)
    def test_stdio_hang_005_install_interleaved_with_list_does_not_hang(self, stdio_server, conda_env):
        """
        STDIO-HANG-005: session must stay functional across WARM_ITERATIONS cycles of
        (conda_install_packages → conda_list_environments), over STDIO.
        Mirrors HTTP HANG-005.

        The interleaving catches proxy state corruption that only surfaces when
        success and read-only calls alternate on the same session — the pattern
        that occurs naturally during a Claude Desktop workflow.

        Two failure modes:
          1. Install step hangs: proxy dropped the success response connection.
          2. List step hangs after a successful install: proxy corrupted its
             internal session state while handling the install response.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            # Install step
            logger.info(
                "STDIO-HANG-005 [%d/%d] install step: install_packages env=%s pkg=%s",
                i,
                WARM_ITERATIONS,
                conda_env["name"],
                EXISTING_PKG,
            )
            _, elapsed = _call_no_hang(
                stdio_server,
                "conda_install_packages",
                {
                    "environment": conda_env["name"],
                    "packages": [EXISTING_PKG],
                },
                f"STDIO-HANG-005 [{i}/{WARM_ITERATIONS}] install step: "
                f"conda_install_packages hung for > {TOOL_TIMEOUT}s. "
                "KI-011 happy-path variant.",
            )
            logger.info(
                "STDIO-HANG-005 [%d/%d] install step done in %.2fs",
                i,
                WARM_ITERATIONS,
                elapsed,
            )

            # Health step
            logger.info(
                "STDIO-HANG-005 [%d/%d] health step: list_environments",
                i,
                WARM_ITERATIONS,
            )
            response, elapsed = _call_no_hang(
                stdio_server,
                "conda_list_environments",
                {},
                f"STDIO-HANG-005 [{i}/{WARM_ITERATIONS}] health step: "
                "conda_list_environments hung after a successful install — "
                "proxy corrupted internal state. KI-011 happy-path variant.",
            )
            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-005 [%d/%d] health step done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                is_err,
            )
            assert not is_err, (
                f"STDIO-HANG-005 [{i}/{WARM_ITERATIONS}]: "
                f"conda_list_environments returned an error after a successful install: {response}"
            )

    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_stdio_hang_006_repeated_list_environments_does_not_hang(self, stdio_server):
        """
        STDIO-HANG-006: conda_list_environments (lightweight read-only) must return
        within TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls, over STDIO.
        Mirrors HTTP HANG-006.

        This test uses the lightest possible endpoint to establish baseline
        behavior. list_environments is fast (~0.1-0.5s) and read-only.

        If this test passes but STDIO-HANG-004/005 fail, the bug is timing-dependent
        and only triggers with slower operations.

        If this test also fails, the bug affects all operations regardless of
        execution time, making it much more likely to impact casual users.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "STDIO-HANG-006 [%d/%d] list_environments",
                i,
                WARM_ITERATIONS,
            )
            response, elapsed = _call_no_hang(
                stdio_server,
                "conda_list_environments",
                {},
                f"STDIO-HANG-006: conda_list_environments hung for > {TOOL_TIMEOUT}s "
                f"(iteration {i}/{WARM_ITERATIONS}). "
                "mcp-compose STDIO proxy failed on lightweight read-only operation. "
                "KI-011 affects ALL operations, not just slow ones.",
            )
            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-006 [%d/%d] done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                is_err,
            )
            assert not is_err, (
                f"STDIO-HANG-006 [{i}/{WARM_ITERATIONS}]: " f"conda_list_environments returned an error: {response}"
            )

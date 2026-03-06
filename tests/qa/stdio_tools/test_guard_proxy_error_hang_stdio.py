"""
Regression tests: KI-011 — mcp-compose proxy must forward tool error responses
over STDIO transport without hanging (mirrors test_guard_proxy_error_hang.py).

The test process communicates with mcp-compose over stdin/stdout (newline-
delimited JSON-RPC). mcp-compose's internal connection to environments_mcp_server
is still Streamable HTTP in STDIO mode — only the upstream transport differs.

Each test receives a fresh mcp-compose process via the function-scoped
stdio_server fixture (conftest.py). Tests that trigger the hang corrupt the
internal connection pool permanently; a fresh process per test prevents
cascading failures.

No httpx or MCP SDK required — stdlib only (subprocess, threading, json).

See tests/qa/_ai_docs/hang_issue/ for root-cause analysis and transport
comparison.
"""

from __future__ import annotations

import logging

import pytest

from common.constants.config import DOWNSTREAM_PORT, TOOL_TIMEOUT, WARM_ITERATIONS
from common.constants.test_data import HANG_FAIL_MSG, NONEXISTENT_ENV_PREFIX, NONEXISTENT_PKG
from common.utils.stdio_client import _call_no_hang, _is_error

pytestmark = pytest.mark.stdio_transport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.slow
class TestProxyErrorHangStdio:

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS)
    def test_stdio_hang_001_remove_nonexistent_env_does_not_hang(self, stdio_server):
        """
        STDIO-HANG-001: conda_remove_environment must return isError=true within
        TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls, over STDIO.
        Mirrors HTTP HANG-001.

        Reproduced: 2026-03-06, macOS, STDIO transport, Python 3.13,
        environments-mcp-server 1.0.0rc1.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "STDIO-HANG-001 [%d/%d] remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            response, elapsed = _call_no_hang(
                stdio_server,
                "conda_remove_environment",
                {"prefix": NONEXISTENT_ENV_PREFIX},
                f"STDIO-HANG-001: conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                + HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-001 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, elapsed, is_err,
            )
            assert is_err, (
                f"STDIO-HANG-001 [{i}/{WARM_ITERATIONS}]: expected isError=true "
                f"for non-existent prefix '{NONEXISTENT_ENV_PREFIX}', got: {response}"
            )

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS)
    def test_stdio_hang_002_install_into_nonexistent_env_does_not_hang(self, stdio_server):
        """
        STDIO-HANG-002: conda_install_packages must return isError=true within
        TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls, over STDIO.
        Mirrors HTTP HANG-002. Exercises a different code path than HANG-001.

        Reproduced: 2026-03-06, macOS, STDIO transport, Python 3.13,
        environments-mcp-server 1.0.0rc1.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "STDIO-HANG-002 [%d/%d] install_packages prefix=%s pkg=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX, NONEXISTENT_PKG,
            )
            response, elapsed = _call_no_hang(
                stdio_server,
                "conda_install_packages",
                {"prefix": NONEXISTENT_ENV_PREFIX, "packages": [NONEXISTENT_PKG]},
                f"STDIO-HANG-002: conda_install_packages hung for > {TOOL_TIMEOUT}s. "
                + HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-002 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, elapsed, is_err,
            )
            assert is_err, (
                f"STDIO-HANG-002 [{i}/{WARM_ITERATIONS}]: expected isError=true "
                f"for non-existent prefix '{NONEXISTENT_ENV_PREFIX}', got: {response}"
            )

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS * 3)
    def test_stdio_hang_003_server_survives_error_response(self, stdio_server):
        """
        STDIO-HANG-003: server must stay functional across repeated error+health
        cycles, over STDIO. Mirrors HTTP HANG-003.

        Phase 1 — WARM_ITERATIONS × list_environments to build session state.
        Phase 2 — WARM_ITERATIONS × (remove_nonexistent_env → list_environments).

        Two failure modes:
          1. Warm-up hangs: pool already stuck from an error earlier in the
             same test (stdio_server is function-scoped, so no cross-test leak).
          2. Health step hangs: proxy corrupted state while forwarding the error,
             causing the immediately following healthy call to hang.

        Run in isolation to test mode 2 independently:
          python -m pytest tests/qa/stdio_tools/test_guard_proxy_error_hang_stdio.py \
              -k test_stdio_hang_003 -v

        Reproduced: 2026-03-06, macOS, STDIO transport, Python 3.13,
        environments-mcp-server 1.0.0rc1.
        """
        logger.info(
            "STDIO-HANG-003 warm-up: %d × conda_list_environments",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info("STDIO-HANG-003 warm-up [%d/%d] list_environments", i, WARM_ITERATIONS)
            _, elapsed = _call_no_hang(
                stdio_server,
                "conda_list_environments",
                {},
                f"STDIO-HANG-003 warm-up [{i}/{WARM_ITERATIONS}]: "
                f"conda_list_environments hung — internal pool stuck on port "
                f"{DOWNSTREAM_PORT}. Run in isolation against a fresh server. KI-011.",
            )
            logger.info(
                "STDIO-HANG-003 warm-up [%d/%d] done in %.2fs",
                i, WARM_ITERATIONS, elapsed,
            )

        logger.info(
            "STDIO-HANG-003: warm-up done — starting %d × error+health iterations",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "STDIO-HANG-003 [%d/%d] error step: remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            _, elapsed = _call_no_hang(
                stdio_server,
                "conda_remove_environment",
                {"prefix": NONEXISTENT_ENV_PREFIX},
                f"STDIO-HANG-003 iteration {i}/{WARM_ITERATIONS} (error step): "
                f"conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                + HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            logger.info(
                "STDIO-HANG-003 [%d/%d] error step done in %.2fs",
                i, WARM_ITERATIONS, elapsed,
            )

            logger.info(
                "STDIO-HANG-003 [%d/%d] health step: list_environments",
                i, WARM_ITERATIONS,
            )
            response, elapsed = _call_no_hang(
                stdio_server,
                "conda_list_environments",
                {},
                f"STDIO-HANG-003 [{i}/{WARM_ITERATIONS}] health step: "
                "server hung after an error response — proxy corrupted "
                "internal state. Server restart required. KI-011.",
            )
            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-003 [%d/%d] health step done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, elapsed, is_err,
            )
            assert not is_err, (
                f"STDIO-HANG-003 iteration {i}/{WARM_ITERATIONS}: "
                f"conda_list_environments returned an error after the server "
                f"survived the previous error: {response}"
            )

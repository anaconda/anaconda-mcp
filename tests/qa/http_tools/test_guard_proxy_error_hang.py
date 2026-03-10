"""
Regression tests: KI-011 — mcp-compose proxy must forward tool error responses
to HTTP clients without hanging or corrupting the internal connection pool.

Each test calls an error-triggering tool WARM_ITERATIONS times to exercise
accumulated session state (the production hang occurred after ~47 min of use).
A SIGALRM-based timeout in _call_tool catches the hang where mcp-compose streams
SSE keepalives indefinitely instead of forwarding the result.

See tests/qa/_ai_docs/hang_issue/ for root-cause analysis, protocol flow
diagrams, and fix plan.
"""

from __future__ import annotations

import logging
import time

import pytest

from common.constants.config import ITERATION_DELAY, TOOL_TIMEOUT, WARM_ITERATIONS
from common.constants.mcp_tools import (
    InstallPackagesArgs,
    RemoveEnvironmentArgs,
    ToolResultFields,
    Tools,
)
from common.constants.test_data import (
    KI011_HANG_FAIL_MSG,
    NONEXISTENT_ENV_PREFIX,
    NONEXISTENT_PKG,
)
from common.utils.mcp_client import _call_no_hang, _tool_result
from common.utils.response_validators import _validate_is_error

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.http_transport

# Calculate test timeouts including iteration delays
# Each test needs: (TOOL_TIMEOUT + ITERATION_DELAY) * WARM_ITERATIONS
_BASE_TIMEOUT = int((TOOL_TIMEOUT + ITERATION_DELAY) * WARM_ITERATIONS) + 60  # +60s buffer


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.slow
class TestProxyErrorHangHttp:

    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_hang_001_remove_nonexistent_env_does_not_hang(self, fresh_session_id):
        """
        HANG-001: conda_remove_environment must return isError=true within
        TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-001 [%d/%d] remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            response, elapsed = _call_no_hang(
                Tools.CONDA_REMOVE_ENVIRONMENT,
                {RemoveEnvironmentArgs.PREFIX: NONEXISTENT_ENV_PREFIX},
                fresh_session_id,
                f"HANG-001: conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                + KI011_HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            result = _tool_result(response)
            logger.info(
                "HANG-001 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, elapsed, result.get(ToolResultFields.IS_ERROR),
            )
            _validate_is_error(
                result,
                f"HANG-001 [{i}/{WARM_ITERATIONS}] for non-existent prefix '{NONEXISTENT_ENV_PREFIX}'",
            )
            # Delay between iterations to avoid KI-011 connection pool exhaustion
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_hang_002_install_into_nonexistent_env_does_not_hang(self, fresh_session_id):
        """
        HANG-002: conda_install_packages must return isError=true within
        TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls.
        Exercises a different code path in environments_mcp_server than HANG-001.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-002 [%d/%d] install_packages prefix=%s pkg=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX, NONEXISTENT_PKG,
            )
            response, elapsed = _call_no_hang(
                Tools.CONDA_INSTALL_PACKAGES,
                {
                    InstallPackagesArgs.PREFIX: NONEXISTENT_ENV_PREFIX,
                    InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG],
                },
                fresh_session_id,
                f"HANG-002: conda_install_packages hung for > {TOOL_TIMEOUT}s. "
                + KI011_HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            result = _tool_result(response)
            logger.info(
                "HANG-002 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, elapsed, result.get(ToolResultFields.IS_ERROR),
            )
            _validate_is_error(
                result,
                f"HANG-002 [{i}/{WARM_ITERATIONS}] for non-existent prefix '{NONEXISTENT_ENV_PREFIX}'",
            )
            # Delay between iterations to avoid KI-011 connection pool exhaustion
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

    @pytest.mark.timeout(_BASE_TIMEOUT * 3)
    def test_hang_003_session_survives_error_response(self, fresh_session_id):
        """
        HANG-003: the session must stay functional across repeated error+health
        cycles.

        Phase 1 — WARM_ITERATIONS × list_environments to build up session state.
        Phase 2 — WARM_ITERATIONS × (remove_nonexistent_env → list_environments).

        Two failure modes:
          1. Warm-up hangs on iteration 1: process-level pool corruption carried
             over from HANG-002 in the same run. Restart the server and rerun
             HANG-003 in isolation to confirm.
          2. Health step hangs in Phase 2: the proxy corrupted its state while
             forwarding the error, so the immediately following healthy call hangs.

        Run in isolation against a fresh server to test mode 2 independently:
          python -m pytest tests/qa/http_tools/test_guard_proxy_error_hang.py \
              -k test_hang_003 -v
        """
        logger.info(
            "HANG-003 warm-up: %d × conda_list_environments",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info("HANG-003 warm-up [%d/%d] list_environments", i, WARM_ITERATIONS)
            _, elapsed = _call_no_hang(
                Tools.CONDA_LIST_ENVIRONMENTS,
                {},
                fresh_session_id,
                f"HANG-003 warm-up [{i}/{WARM_ITERATIONS}]: "
                f"conda_list_environments hung — mcp-compose internal pool is stuck. "
                f"If HANG-002 also failed in this run, restart the server and rerun "
                f"HANG-003 in isolation. KI-011.",
            )
            logger.info(
                "HANG-003 warm-up [%d/%d] done in %.2fs",
                i, WARM_ITERATIONS, elapsed,
            )
            # Delay between iterations to avoid KI-011 connection pool exhaustion
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

        logger.info(
            "HANG-003: warm-up done — starting %d × error+health iterations",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-003 [%d/%d] error step: remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            _, elapsed = _call_no_hang(
                Tools.CONDA_REMOVE_ENVIRONMENT,
                {RemoveEnvironmentArgs.PREFIX: NONEXISTENT_ENV_PREFIX},
                fresh_session_id,
                f"HANG-003 iteration {i}/{WARM_ITERATIONS} (error step): "
                f"conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                + KI011_HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            logger.info(
                "HANG-003 [%d/%d] error step done in %.2fs",
                i, WARM_ITERATIONS, elapsed,
            )

            logger.info("HANG-003 [%d/%d] health step: list_environments", i, WARM_ITERATIONS)
            response, elapsed = _call_no_hang(
                Tools.CONDA_LIST_ENVIRONMENTS,
                {},
                fresh_session_id,
                f"HANG-003 [{i}/{WARM_ITERATIONS}] health step: "
                "session hung after an error response — proxy corrupted "
                "internal state. Server restart required. KI-011.",
            )
            result = _tool_result(response)
            logger.info(
                "HANG-003 [%d/%d] health step done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, elapsed, result.get(ToolResultFields.IS_ERROR),
            )
            assert not result.get(ToolResultFields.IS_ERROR), (
                f"HANG-003 iteration {i}/{WARM_ITERATIONS}: "
                f"conda_list_environments returned an error after the session "
                f"survived the previous error: {result}"
            )
            # Delay between iterations to avoid KI-011 connection pool exhaustion
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

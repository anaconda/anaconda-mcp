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

import httpx
import pytest

from common.constants.config import BASE_URL, TOOL_TIMEOUT
from common.constants.mcp_tools import (
    InstallPackagesArgs,
    RemoveEnvironmentArgs,
    ToolResultFields,
    Tools,
)
from common.constants.test_data import NONEXISTENT_ENV_PREFIX, NONEXISTENT_PKG
from common.utils.mcp_client import _call_tool, _initialize_session, _tool_result
from common.utils.response_validators import _validate_is_error

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.http_transport


@pytest.fixture
def session_id(mcp_server) -> str | None:
    """
    Function-scoped MCP session for hang tests — overrides the module-scoped
    fixture from conftest.py.

    Each test opens a fresh session so a hang triggered by one test (which
    permanently corrupts mcp-compose's internal connection pool) does not
    cascade into subsequent tests.
    """
    return _initialize_session(BASE_URL, client_name="api-tools-hang-test")


# 20 iterations to accumulate session state (the production hang occurred after
# ~47 min of use). If the race fires on any iteration, ReadTimeout is raised
# immediately and the test fails with the iteration number and a KI-011 reference.
WARM_ITERATIONS = 20

_HANG_FAIL_MSG = (
    "mcp-compose proxy did not forward the error response from "
    "environments_mcp_server within {timeout}s (iteration {iteration}/{total}). "
    "The backend HTTP session to port 4041 was likely abandoned "
    "(missing 5th POST + DELETE). Matches the KI-011 hang pattern. "
    "Observed on 2026-03-05 with Streamable HTTP transport, Python 3.13."
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.slow
class TestProxyErrorHangHttp:

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS)
    def test_hang_001_remove_nonexistent_env_does_not_hang(self, session_id):
        """
        HANG-001: conda_remove_environment must return isError=true within
        TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-001 [%d/%d] remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            t0 = time.monotonic()
            try:
                response = _call_tool(
                    Tools.CONDA_REMOVE_ENVIRONMENT,
                    {RemoveEnvironmentArgs.PREFIX: NONEXISTENT_ENV_PREFIX},
                    session_id,
                )
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-001: conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )

            result = _tool_result(response)
            logger.info(
                "HANG-001 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, time.monotonic() - t0,
                result.get(ToolResultFields.IS_ERROR),
            )
            _validate_is_error(
                result,
                f"HANG-001 [{i}/{WARM_ITERATIONS}] for non-existent prefix '{NONEXISTENT_ENV_PREFIX}'",
            )

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS)
    def test_hang_002_install_into_nonexistent_env_does_not_hang(self, session_id):
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
            t0 = time.monotonic()
            try:
                response = _call_tool(
                    Tools.CONDA_INSTALL_PACKAGES,
                    {
                        InstallPackagesArgs.PREFIX: NONEXISTENT_ENV_PREFIX,
                        InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG],
                    },
                    session_id,
                )
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-002: conda_install_packages hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )

            result = _tool_result(response)
            logger.info(
                "HANG-002 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, time.monotonic() - t0,
                result.get(ToolResultFields.IS_ERROR),
            )
            _validate_is_error(
                result,
                f"HANG-002 [{i}/{WARM_ITERATIONS}] for non-existent prefix '{NONEXISTENT_ENV_PREFIX}'",
            )

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS * 3)
    def test_hang_003_session_survives_error_response(self, session_id):
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
          python -m pytest tests/qa/api_tools/test_guard_proxy_error_hang.py \
              -k test_hang_003 -v
        """
        logger.info(
            "HANG-003 warm-up: %d × conda_list_environments",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info("HANG-003 warm-up [%d/%d] list_environments", i, WARM_ITERATIONS)
            t0 = time.monotonic()
            try:
                _call_tool(Tools.CONDA_LIST_ENVIRONMENTS, {}, session_id)
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-003 warm-up [{i}/{WARM_ITERATIONS}]: "
                    f"conda_list_environments hung — mcp-compose internal pool is stuck. "
                    f"If HANG-002 also failed in this run, restart the server and rerun "
                    f"HANG-003 in isolation. KI-011."
                )
            logger.info(
                "HANG-003 warm-up [%d/%d] done in %.2fs",
                i, WARM_ITERATIONS, time.monotonic() - t0,
            )

        logger.info(
            "HANG-003: warm-up done — starting %d × error+health iterations",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-003 [%d/%d] error step: remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            t0 = time.monotonic()
            try:
                _call_tool(
                    Tools.CONDA_REMOVE_ENVIRONMENT,
                    {RemoveEnvironmentArgs.PREFIX: NONEXISTENT_ENV_PREFIX},
                    session_id,
                )
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-003 iteration {i}/{WARM_ITERATIONS} (error step): "
                    f"conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )
            logger.info(
                "HANG-003 [%d/%d] error step done in %.2fs",
                i, WARM_ITERATIONS, time.monotonic() - t0,
            )

            logger.info("HANG-003 [%d/%d] health step: list_environments", i, WARM_ITERATIONS)
            t0 = time.monotonic()
            try:
                response = _call_tool(Tools.CONDA_LIST_ENVIRONMENTS, {}, session_id)
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-003 [{i}/{WARM_ITERATIONS}] health step: "
                    "session hung after an error response — proxy corrupted "
                    "internal state. Server restart required. KI-011."
                )

            result = _tool_result(response)
            logger.info(
                "HANG-003 [%d/%d] health step done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, time.monotonic() - t0,
                result.get(ToolResultFields.IS_ERROR),
            )
            assert not result.get(ToolResultFields.IS_ERROR), (
                f"HANG-003 iteration {i}/{WARM_ITERATIONS}: "
                f"conda_list_environments returned an error after the session "
                f"survived the previous error: {result}"
            )

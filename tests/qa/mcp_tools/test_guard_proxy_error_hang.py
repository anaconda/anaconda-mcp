"""
Regression tests: KI-011 — mcp-compose must forward tool error responses without
hanging (HTTP or STDIO client edge, per --mcp-profile).

Uses call_no_hang_unified: HTTP uses fresh_session_id + httpx timeouts; STDIO uses
a fresh subprocess per test (stdio_server).
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
from common.constants.test_data import KI011_HANG_FAIL_MSG, NONEXISTENT_ENV_PREFIX, NONEXISTENT_PKG
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import _validate_is_error

logger = logging.getLogger(__name__)

_BASE_TIMEOUT = int((TOOL_TIMEOUT + ITERATION_DELAY) * WARM_ITERATIONS) + 60


@pytest.mark.regression
@pytest.mark.slow
class TestProxyErrorHang:
    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_hang_001_remove_nonexistent_env_does_not_hang(self, call_no_hang_unified):
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-001 [%d/%d] remove_environment prefix=%s",
                i,
                WARM_ITERATIONS,
                NONEXISTENT_ENV_PREFIX,
            )
            response, elapsed = call_no_hang_unified(
                Tools.CONDA_REMOVE_ENVIRONMENT,
                {RemoveEnvironmentArgs.PREFIX: NONEXISTENT_ENV_PREFIX},
                f"HANG-001: conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                + KI011_HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            result = _tool_result(response)
            logger.info(
                "HANG-001 [%d/%d] done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                result.get(ToolResultFields.IS_ERROR),
            )
            _validate_is_error(
                result,
                f"HANG-001 [{i}/{WARM_ITERATIONS}] for non-existent prefix '{NONEXISTENT_ENV_PREFIX}'",
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_hang_002_install_into_nonexistent_env_does_not_hang(self, call_no_hang_unified):
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-002 [%d/%d] install_packages prefix=%s pkg=%s",
                i,
                WARM_ITERATIONS,
                NONEXISTENT_ENV_PREFIX,
                NONEXISTENT_PKG,
            )
            response, elapsed = call_no_hang_unified(
                Tools.CONDA_INSTALL_PACKAGES,
                {
                    InstallPackagesArgs.PREFIX: NONEXISTENT_ENV_PREFIX,
                    InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG],
                },
                f"HANG-002: conda_install_packages hung for > {TOOL_TIMEOUT}s. "
                + KI011_HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            result = _tool_result(response)
            logger.info(
                "HANG-002 [%d/%d] done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                result.get(ToolResultFields.IS_ERROR),
            )
            _validate_is_error(
                result,
                f"HANG-002 [{i}/{WARM_ITERATIONS}] for non-existent prefix '{NONEXISTENT_ENV_PREFIX}'",
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

    @pytest.mark.timeout(_BASE_TIMEOUT * 3)
    def test_hang_003_session_survives_error_response(self, call_no_hang_unified):
        logger.info(
            "HANG-003 warm-up: %d × conda_list_environments",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info("HANG-003 warm-up [%d/%d] list_environments", i, WARM_ITERATIONS)
            _, elapsed = call_no_hang_unified(
                Tools.CONDA_LIST_ENVIRONMENTS,
                {},
                f"HANG-003 warm-up [{i}/{WARM_ITERATIONS}]: "
                f"conda_list_environments hung — mcp-compose internal pool is stuck. "
                f"If HANG-002 also failed in this run, restart the server and rerun "
                f"HANG-003 in isolation. KI-011.",
            )
            logger.info(
                "HANG-003 warm-up [%d/%d] done in %.2fs",
                i,
                WARM_ITERATIONS,
                elapsed,
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

        logger.info(
            "HANG-003: warm-up done — starting %d × error+health iterations",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-003 [%d/%d] error step: remove_environment prefix=%s",
                i,
                WARM_ITERATIONS,
                NONEXISTENT_ENV_PREFIX,
            )
            _, elapsed = call_no_hang_unified(
                Tools.CONDA_REMOVE_ENVIRONMENT,
                {RemoveEnvironmentArgs.PREFIX: NONEXISTENT_ENV_PREFIX},
                f"HANG-003 iteration {i}/{WARM_ITERATIONS} (error step): "
                f"conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                + KI011_HANG_FAIL_MSG.format(timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS),
            )
            logger.info(
                "HANG-003 [%d/%d] error step done in %.2fs",
                i,
                WARM_ITERATIONS,
                elapsed,
            )

            logger.info("HANG-003 [%d/%d] health step: list_environments", i, WARM_ITERATIONS)
            response, elapsed = call_no_hang_unified(
                Tools.CONDA_LIST_ENVIRONMENTS,
                {},
                f"HANG-003 [{i}/{WARM_ITERATIONS}] health step: "
                "session hung after an error response — proxy corrupted "
                "internal state. Server restart required. KI-011.",
            )
            result = _tool_result(response)
            logger.info(
                "HANG-003 [%d/%d] health step done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                result.get(ToolResultFields.IS_ERROR),
            )
            assert not result.get(ToolResultFields.IS_ERROR), (
                f"HANG-003 iteration {i}/{WARM_ITERATIONS}: "
                f"conda_list_environments returned an error after the session "
                f"survived the previous error: {result}"
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

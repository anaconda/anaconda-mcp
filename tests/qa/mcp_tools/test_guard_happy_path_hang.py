"""
Regression tests: KI-011 (happy-path variant) — mcp-compose must forward successful
tool responses without hanging (profile-selected via --mcp-profile).

Marked ``hang_stress``: many repeated calls; omit from quick runs with
``--skip-hang-stress`` or ``MCP_QA_SKIP_HANG_STRESS=1`` (see README).
"""

from __future__ import annotations

import logging
import time

import pytest
from common.constants.config import ITERATION_DELAY, TOOL_TIMEOUT, WARM_ITERATIONS
from common.constants.mcp_tools import InstallPackagesArgs, ToolResultFields, Tools
from common.constants.test_data import EXISTING_PKG
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import (
    _validate_install_has_message,
    _validate_install_success,
)

logger = logging.getLogger(__name__)

_BASE_TIMEOUT = int((TOOL_TIMEOUT + ITERATION_DELAY) * WARM_ITERATIONS) + 60


@pytest.mark.hang_stress
@pytest.mark.regression
@pytest.mark.slow
class TestHappyPathHang:
    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_hang_004_repeated_install_does_not_hang(self, conda_env, call_no_hang_unified):
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-004 [%d/%d] install_packages env=%s pkg=%s",
                i,
                WARM_ITERATIONS,
                conda_env["name"],
                EXISTING_PKG,
            )
            response, elapsed = call_no_hang_unified(
                Tools.CONDA_INSTALL_PACKAGES,
                {
                    InstallPackagesArgs.ENVIRONMENT: conda_env["name"],
                    InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
                },
                f"HANG-004: conda_install_packages (happy path) hung for > {TOOL_TIMEOUT}s "
                f"(iteration {i}/{WARM_ITERATIONS}). "
                "mcp-compose proxy did not forward the success response from "
                "environments_mcp_server. KI-011 happy-path variant.",
            )
            result = _tool_result(response)
            logger.info(
                "HANG-004 [%d/%d] done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                result.get(ToolResultFields.IS_ERROR),
            )
            _validate_install_success(
                result,
                context=f"HANG-004 [{i}/{WARM_ITERATIONS}] env={conda_env['name']!r} pkg={EXISTING_PKG!r}",
            )
            _validate_install_has_message(
                result,
                context=f"HANG-004 [{i}/{WARM_ITERATIONS}] env={conda_env['name']!r} pkg={EXISTING_PKG!r}",
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

    @pytest.mark.timeout(_BASE_TIMEOUT * 2)
    def test_hang_005_install_interleaved_with_list_does_not_hang(self, conda_env, call_no_hang_unified):
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-005 [%d/%d] install step: install_packages env=%s pkg=%s",
                i,
                WARM_ITERATIONS,
                conda_env["name"],
                EXISTING_PKG,
            )
            _, elapsed = call_no_hang_unified(
                Tools.CONDA_INSTALL_PACKAGES,
                {
                    InstallPackagesArgs.ENVIRONMENT: conda_env["name"],
                    InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
                },
                f"HANG-005 [{i}/{WARM_ITERATIONS}] install step: "
                f"conda_install_packages hung for > {TOOL_TIMEOUT}s. "
                "KI-011 happy-path variant.",
            )
            logger.info(
                "HANG-005 [%d/%d] install step done in %.2fs",
                i,
                WARM_ITERATIONS,
                elapsed,
            )

            logger.info("HANG-005 [%d/%d] health step: list_environments", i, WARM_ITERATIONS)
            response, elapsed = call_no_hang_unified(
                Tools.CONDA_LIST_ENVIRONMENTS,
                {},
                f"HANG-005 [{i}/{WARM_ITERATIONS}] health step: "
                "conda_list_environments hung after a successful install — "
                "proxy corrupted internal state. KI-011 happy-path variant.",
            )
            result = _tool_result(response)
            logger.info(
                "HANG-005 [%d/%d] health step done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                result.get(ToolResultFields.IS_ERROR),
            )
            assert not result.get(ToolResultFields.IS_ERROR), (
                f"HANG-005 [{i}/{WARM_ITERATIONS}]: "
                f"conda_list_environments returned an error after a successful install: {result}"
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_hang_006_repeated_list_environments_does_not_hang(self, call_no_hang_unified):
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-006 [%d/%d] list_environments",
                i,
                WARM_ITERATIONS,
            )
            response, elapsed = call_no_hang_unified(
                Tools.CONDA_LIST_ENVIRONMENTS,
                {},
                f"HANG-006: conda_list_environments hung for > {TOOL_TIMEOUT}s "
                f"(iteration {i}/{WARM_ITERATIONS}). "
                "mcp-compose proxy failed on lightweight read-only operation. "
                "KI-011 affects ALL operations, not just slow ones.",
            )
            result = _tool_result(response)
            logger.info(
                "HANG-006 [%d/%d] done in %.2fs — is_error=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                result.get(ToolResultFields.IS_ERROR),
            )
            assert not result.get(ToolResultFields.IS_ERROR), (
                f"HANG-006 [{i}/{WARM_ITERATIONS}]: conda_list_environments returned an error: {result}"
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

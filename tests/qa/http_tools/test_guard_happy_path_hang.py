"""
Regression tests: KI-011 (happy-path variant) — mcp-compose proxy must forward
successful tool responses to HTTP clients without hanging.

The production hang was observed not only on error responses but also during
extended Claude Desktop sessions that triggered repeated happy-path package
installs.  These tests exercise the success path of conda_install_packages
to confirm the proxy stays alive across many successful round-trips.

Each test calls conda_install_packages with a real, existing package
WARM_ITERATIONS times.  A ReadTimeout from _call_no_hang signals a hang
identical in mechanism to KI-011 (missing 5th POST + DELETE) but triggered
by a success response instead of an error one.

See tests/qa/_ai_docs/hang_issue/ for root-cause analysis, protocol flow
diagrams, and fix plan.
"""

from __future__ import annotations

import logging
import time

import pytest
from common.constants.config import ITERATION_DELAY, TOOL_TIMEOUT, WARM_ITERATIONS
from common.constants.mcp_tools import InstallPackagesArgs, ToolResultFields, Tools
from common.constants.test_data import EXISTING_PKG
from common.utils.mcp_client import _call_no_hang, _tool_result
from common.utils.response_validators import (
    _validate_install_has_message,
    _validate_install_success,
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.http_transport

# Calculate test timeouts including iteration delays.
# Each test needs: (TOOL_TIMEOUT + ITERATION_DELAY) * WARM_ITERATIONS
# The first iteration may take longer than TOOL_TIMEOUT because conda must
# actually solve and download pyyaml; subsequent iterations are fast (already
# installed).  TOOL_TIMEOUT=60s comfortably covers even a cold first install.
_BASE_TIMEOUT = int((TOOL_TIMEOUT + ITERATION_DELAY) * WARM_ITERATIONS) + 60  # +60s buffer


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.slow
class TestHappyPathHangHttp:
    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_hang_004_repeated_install_does_not_hang(self, conda_env, fresh_session_id):
        """
        HANG-004: conda_install_packages (success path) must return within
        TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls.

        Installs EXISTING_PKG into a real environment.  After the first
        iteration the package is already present so conda returns quickly, but
        the proxy must still complete the full HTTP round-trip for every call.

        Failure mode: proxy hangs on an inbound successful response (missing
        5th POST + DELETE after a 200-OK tool result), mirroring KI-011 but
        triggered by success rather than error.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-004 [%d/%d] install_packages env=%s pkg=%s",
                i,
                WARM_ITERATIONS,
                conda_env["name"],
                EXISTING_PKG,
            )
            response, elapsed = _call_no_hang(
                Tools.CONDA_INSTALL_PACKAGES,
                {
                    InstallPackagesArgs.ENVIRONMENT: conda_env["name"],
                    InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
                },
                fresh_session_id,
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
    def test_hang_005_install_interleaved_with_list_does_not_hang(self, conda_env, fresh_session_id):
        """
        HANG-005: session must stay functional across WARM_ITERATIONS cycles of
        (conda_install_packages → conda_list_environments).

        Mirrors HANG-003 but replaces the error step with a happy-path install.
        The interleaving catches proxy state corruption that only surfaces when
        success and read-only calls alternate on the same session — the pattern
        that occurs naturally during a Claude Desktop workflow.

        Two failure modes:
          1. Install step hangs: proxy dropped the success response connection.
          2. List step hangs after a successful install: proxy corrupted its
             internal session state while handling the install response.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-005 [%d/%d] install step: install_packages env=%s pkg=%s",
                i,
                WARM_ITERATIONS,
                conda_env["name"],
                EXISTING_PKG,
            )
            _, elapsed = _call_no_hang(
                Tools.CONDA_INSTALL_PACKAGES,
                {
                    InstallPackagesArgs.ENVIRONMENT: conda_env["name"],
                    InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
                },
                fresh_session_id,
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
            response, elapsed = _call_no_hang(
                Tools.CONDA_LIST_ENVIRONMENTS,
                {},
                fresh_session_id,
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
    def test_hang_006_repeated_list_environments_does_not_hang(self, fresh_session_id):
        """
        HANG-006: conda_list_environments (lightweight read-only) must return within
        TOOL_TIMEOUT on each of WARM_ITERATIONS repeated calls.

        This test uses the lightest possible endpoint to establish baseline
        behavior. list_environments is fast (~0.1-0.5s) and read-only.

        If this test passes but HANG-004/005 fail, the bug is timing-dependent
        and only triggers with slower operations.

        If this test also fails, the bug affects all operations regardless of
        execution time, making it much more likely to impact casual users.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-006 [%d/%d] list_environments",
                i,
                WARM_ITERATIONS,
            )
            response, elapsed = _call_no_hang(
                Tools.CONDA_LIST_ENVIRONMENTS,
                {},
                fresh_session_id,
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
                f"HANG-006 [{i}/{WARM_ITERATIONS}]: " f"conda_list_environments returned an error: {result}"
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

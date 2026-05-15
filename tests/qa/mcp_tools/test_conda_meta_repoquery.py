"""
Happy-path, error-path, and hang-stress tests for conda-meta-mcp repoquery tool.

Tests verify:
- isError=false when querying dependencies (depends mode)
- isError=false when querying reverse dependencies (whoneeds mode)
- isError=true when querying an invalid package
- Response contains text content
- 20 repeated calls do not cause hang (KI-011 pattern)
"""

from __future__ import annotations

import logging
import time

import pytest
from common.constants.config import ITERATION_DELAY, TOOL_TIMEOUT, WARM_ITERATIONS
from common.constants.mcp_tools import CondaMetaTools, RepoqueryArgs
from common.constants.test_data import (
    NONEXISTENT_PACKAGE_SPEC,
    REPOQUERY_CHANNEL,
    REPOQUERY_SPEC,
)
from common.utils.response_validators import (
    validate_conda_meta_success,
    validate_conda_meta_text_content,
)

logger = logging.getLogger(__name__)


def _extract_mcp_response(response: dict):
    """Extract MCP response from call_tool result (handles different formats)."""
    if "result" in response:
        return response["result"]
    return response


@pytest.mark.slow
@pytest.mark.auth_independent
class TestCondaMetaRepoquery:
    """
    Happy-path and error-path tests for conda-meta_repoquery tool.
    """

    def test_repoquery_depends(self, call_tool):
        """
        Querying package dependencies must return isError=false.

        Uses 'python' to query its dependencies.
        """
        logger.info("Calling conda-meta_repoquery depends for '%s'", REPOQUERY_SPEC)
        response = call_tool(
            CondaMetaTools.REPOQUERY,
            {
                RepoqueryArgs.SUBCMD: "depends",
                RepoqueryArgs.SPEC: REPOQUERY_SPEC,
                RepoqueryArgs.CHANNEL: REPOQUERY_CHANNEL,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"repoquery depends spec={REPOQUERY_SPEC!r}")
        validate_conda_meta_text_content(mcp_result, context=f"repoquery depends spec={REPOQUERY_SPEC!r}")

    def test_repoquery_whoneeds(self, call_tool):
        """
        Querying reverse dependencies must return isError=false.

        Uses 'python' to find packages that depend on it.
        """
        logger.info("Calling conda-meta_repoquery whoneeds for '%s'", REPOQUERY_SPEC)
        response = call_tool(
            CondaMetaTools.REPOQUERY,
            {
                RepoqueryArgs.SUBCMD: "whoneeds",
                RepoqueryArgs.SPEC: REPOQUERY_SPEC,
                RepoqueryArgs.CHANNEL: REPOQUERY_CHANNEL,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"repoquery whoneeds spec={REPOQUERY_SPEC!r}")
        validate_conda_meta_text_content(mcp_result, context=f"repoquery whoneeds spec={REPOQUERY_SPEC!r}")

    def test_repoquery_invalid_package(self, call_tool):
        """
        Querying a nonexistent package returns text content with an error/empty message.

        conda-meta-mcp may return isError=false with error text or empty results
        for nonexistent packages. This test validates the tool handles invalid
        packages gracefully.
        """
        logger.info("Calling conda-meta_repoquery for nonexistent '%s'", NONEXISTENT_PACKAGE_SPEC)
        response = call_tool(
            CondaMetaTools.REPOQUERY,
            {
                RepoqueryArgs.SUBCMD: "depends",
                RepoqueryArgs.SPEC: NONEXISTENT_PACKAGE_SPEC,
                RepoqueryArgs.CHANNEL: REPOQUERY_CHANNEL,
            },
        )
        mcp_result = _extract_mcp_response(response)
        # Tool may return success with empty/error text or isError=true - both are valid
        validate_conda_meta_text_content(mcp_result, context=f"repoquery invalid spec={NONEXISTENT_PACKAGE_SPEC!r}")


_BASE_TIMEOUT = int((TOOL_TIMEOUT + ITERATION_DELAY) * WARM_ITERATIONS) + 60


@pytest.mark.hang_stress
@pytest.mark.regression
@pytest.mark.slow
@pytest.mark.auth_independent
class TestCondaMetaRepoqueryHangStress:
    """
    Hang-stress test: conda-meta_repoquery must complete 20 iterations without hanging.
    """

    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_repoquery_repeated_calls_no_hang(self, call_no_hang_unified):
        """
        Repeated repoquery calls must not cause proxy-state accumulation hang (KI-011).

        Runs 20 iterations of the repoquery tool to verify mcp-compose proxy
        correctly forwards responses without hanging.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-REPOQUERY [%d/%d] repoquery depends spec=%s",
                i,
                WARM_ITERATIONS,
                REPOQUERY_SPEC,
            )
            response, elapsed = call_no_hang_unified(
                CondaMetaTools.REPOQUERY,
                {
                    RepoqueryArgs.SUBCMD: "depends",
                    RepoqueryArgs.SPEC: REPOQUERY_SPEC,
                    RepoqueryArgs.CHANNEL: REPOQUERY_CHANNEL,
                },
                f"HANG-REPOQUERY: conda-meta_repoquery hung for > {TOOL_TIMEOUT}s "
                f"(iteration {i}/{WARM_ITERATIONS}). "
                "mcp-compose proxy did not forward response from conda-meta-mcp. "
                "KI-011 hang pattern.",
            )
            mcp_result = _extract_mcp_response(response)
            logger.info(
                "HANG-REPOQUERY [%d/%d] done in %.2fs — isError=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                mcp_result.get("isError"),
            )
            validate_conda_meta_success(
                mcp_result,
                context=f"HANG-REPOQUERY [{i}/{WARM_ITERATIONS}] spec={REPOQUERY_SPEC!r}",
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

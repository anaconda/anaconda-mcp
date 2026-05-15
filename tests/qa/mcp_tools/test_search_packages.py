"""
Happy-path, error-path, and hang-stress tests for search-mcp search_packages tool.

Tests verify:
- isError=false when searching for packages
- isError=false when searching with channel filter
- isError=true when searching with empty query
- Response contains content
- 20 repeated calls do not cause hang (KI-011 pattern)
"""

from __future__ import annotations

import logging
import time

import pytest
from common.constants.config import ITERATION_DELAY, TOOL_TIMEOUT, WARM_ITERATIONS
from common.constants.mcp_tools import SearchPackagesArgs, SearchTools
from common.constants.test_data import EMPTY_QUERY, SEARCH_QUERY_PACKAGES
from common.utils.response_validators import (
    validate_search_error,
    validate_search_has_content,
    validate_search_success,
)

logger = logging.getLogger(__name__)


def _extract_mcp_response(response: dict):
    """Extract MCP response from call_tool result (handles different formats)."""
    if "result" in response:
        return response["result"]
    return response


@pytest.mark.slow
class TestSearchPackages:
    """
    Happy-path and error-path tests for search_search_packages tool.
    """

    def test_search_packages_basic(self, call_tool):
        """
        Searching for packages must return isError=false.

        Uses 'numpy' which is a ubiquitous package.
        """
        logger.info("Calling search_search_packages for '%s'", SEARCH_QUERY_PACKAGES)
        response = call_tool(
            SearchTools.SEARCH_PACKAGES,
            {
                SearchPackagesArgs.QUERY: SEARCH_QUERY_PACKAGES,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_success(mcp_result, context=f"search_packages query={SEARCH_QUERY_PACKAGES!r}")
        validate_search_has_content(mcp_result, context=f"search_packages query={SEARCH_QUERY_PACKAGES!r}")

    def test_search_packages_with_channel_filter(self, call_tool):
        """
        Searching with channel filter must return isError=false.

        Uses 'numpy' with conda-forge channel filter.
        """
        logger.info("Calling search_search_packages for '%s' with channel filter", SEARCH_QUERY_PACKAGES)
        response = call_tool(
            SearchTools.SEARCH_PACKAGES,
            {
                SearchPackagesArgs.QUERY: SEARCH_QUERY_PACKAGES,
                SearchPackagesArgs.CHANNELS: ["conda-forge"],
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_success(mcp_result, context="search_packages query=numpy channel=conda-forge")
        validate_search_has_content(mcp_result, context="search_packages query=numpy channel=conda-forge")

    def test_search_packages_empty_query(self, call_tool):
        """
        Searching with an empty query must return isError=true.

        Validates error handling for invalid input.
        """
        logger.info("Calling search_search_packages with empty query")
        response = call_tool(
            SearchTools.SEARCH_PACKAGES,
            {
                SearchPackagesArgs.QUERY: EMPTY_QUERY,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_error(mcp_result, context="search_packages empty query")


_BASE_TIMEOUT = int((TOOL_TIMEOUT + ITERATION_DELAY) * WARM_ITERATIONS) + 60


@pytest.mark.hang_stress
@pytest.mark.regression
@pytest.mark.slow
class TestSearchPackagesHangStress:
    """
    Hang-stress test: search_search_packages must complete 20 iterations without hanging.
    """

    @pytest.mark.timeout(_BASE_TIMEOUT)
    def test_search_packages_repeated_calls_no_hang(self, call_no_hang_unified):
        """
        Repeated search_packages calls must not cause proxy-state accumulation hang (KI-011).

        Runs 20 iterations of the search_packages tool to verify mcp-compose proxy
        correctly forwards responses without hanging.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-SEARCH [%d/%d] search_packages query=%s",
                i,
                WARM_ITERATIONS,
                SEARCH_QUERY_PACKAGES,
            )
            response, elapsed = call_no_hang_unified(
                SearchTools.SEARCH_PACKAGES,
                {
                    SearchPackagesArgs.QUERY: SEARCH_QUERY_PACKAGES,
                },
                f"HANG-SEARCH: search_search_packages hung for > {TOOL_TIMEOUT}s "
                f"(iteration {i}/{WARM_ITERATIONS}). "
                "mcp-compose proxy did not forward response from search-mcp. "
                "KI-011 hang pattern.",
            )
            mcp_result = _extract_mcp_response(response)
            logger.info(
                "HANG-SEARCH [%d/%d] done in %.2fs — isError=%s",
                i,
                WARM_ITERATIONS,
                elapsed,
                mcp_result.get("isError"),
            )
            validate_search_success(
                mcp_result,
                context=f"HANG-SEARCH [{i}/{WARM_ITERATIONS}] query={SEARCH_QUERY_PACKAGES!r}",
            )
            if ITERATION_DELAY > 0 and i < WARM_ITERATIONS:
                time.sleep(ITERATION_DELAY)

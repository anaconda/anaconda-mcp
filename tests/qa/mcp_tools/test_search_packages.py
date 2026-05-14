"""
Happy-path and error-path tests for search-mcp search_packages tool.

Tests verify:
- isError=false when searching for packages
- isError=false when searching with channel filter
- isError=true when searching with empty query
- Response contains content
"""

from __future__ import annotations

import logging

import pytest
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

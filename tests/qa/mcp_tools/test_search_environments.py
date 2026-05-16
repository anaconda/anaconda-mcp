"""
Happy-path tests for search-mcp search_environments tool.

Tests verify:
- isError=false when searching environments
- isError=false when searching with platform filter
- Response contains content

Note: This tool requires authentication. Server won't start without auth.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import SearchEnvironmentsArgs, SearchTools
from common.constants.test_data import SEARCH_QUERY_ENVIRONMENTS
from common.utils.response_validators import (
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
@pytest.mark.auth_required
class TestSearchEnvironments:
    """
    Happy-path tests for search_search_environments tool.
    """

    def test_search_environments_basic(self, call_tool):
        """
        Searching environments must return isError=false.

        Uses 'python' which is a common environment search term.
        """
        logger.info("Calling search_search_environments for '%s'", SEARCH_QUERY_ENVIRONMENTS)
        response = call_tool(
            SearchTools.SEARCH_ENVIRONMENTS,
            {
                SearchEnvironmentsArgs.QUERY: SEARCH_QUERY_ENVIRONMENTS,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_success(mcp_result, context=f"search_environments query={SEARCH_QUERY_ENVIRONMENTS!r}")
        validate_search_has_content(mcp_result, context=f"search_environments query={SEARCH_QUERY_ENVIRONMENTS!r}")

    def test_search_environments_with_platform_filter(self, call_tool):
        """
        Searching environments with platform filter must return isError=false.

        Uses 'python' with linux-64 platform filter.
        """
        logger.info("Calling search_search_environments for '%s' with platform filter", SEARCH_QUERY_ENVIRONMENTS)
        response = call_tool(
            SearchTools.SEARCH_ENVIRONMENTS,
            {
                SearchEnvironmentsArgs.QUERY: SEARCH_QUERY_ENVIRONMENTS,
                SearchEnvironmentsArgs.PLATFORMS: "linux-64",  # string, not list
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_success(mcp_result, context="search_environments query=python platform=linux-64")
        validate_search_has_content(mcp_result, context="search_environments query=python platform=linux-64")

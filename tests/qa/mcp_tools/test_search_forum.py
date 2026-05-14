"""
Happy-path and error-path tests for search-mcp search_forum tool.

Tests verify:
- isError=false when searching forum
- isError=true when searching with empty query
- Response contains content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import SearchForumArgs, SearchTools
from common.constants.test_data import EMPTY_QUERY, SEARCH_QUERY_FORUM
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
class TestSearchForum:
    """
    Happy-path and error-path tests for search_search_forum tool.
    """

    def test_search_forum_basic(self, call_tool):
        """
        Searching forum must return isError=false.

        Uses 'install' which is a common forum topic.
        """
        logger.info("Calling search_search_forum for '%s'", SEARCH_QUERY_FORUM)
        response = call_tool(
            SearchTools.SEARCH_FORUM,
            {
                SearchForumArgs.QUERY: SEARCH_QUERY_FORUM,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_success(mcp_result, context=f"search_forum query={SEARCH_QUERY_FORUM!r}")
        validate_search_has_content(mcp_result, context=f"search_forum query={SEARCH_QUERY_FORUM!r}")

    def test_search_forum_empty_query(self, call_tool):
        """
        Searching forum with an empty query must return isError=true.

        Validates error handling for invalid input.
        """
        logger.info("Calling search_search_forum with empty query")
        response = call_tool(
            SearchTools.SEARCH_FORUM,
            {
                SearchForumArgs.QUERY: EMPTY_QUERY,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_error(mcp_result, context="search_forum empty query")

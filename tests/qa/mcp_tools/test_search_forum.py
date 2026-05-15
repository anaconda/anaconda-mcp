"""
Happy-path and error-path tests for search-mcp search_forum tool.

Tests verify:
- isError=false when searching forum
- isError=true when searching with empty query
- Response contains content

Note: This tool is auth-enhanced - works both ways but returns public-only when logged out.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import SearchForumArgs, SearchTools
from common.constants.test_data import EMPTY_QUERY, SEARCH_QUERY_FORUM
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
@pytest.mark.auth_enhanced
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
        Searching forum with an empty query returns text content with an error message.

        search-mcp returns isError=false with a validation message in text content
        rather than setting isError=true. This test validates graceful handling.
        """
        logger.info("Calling search_search_forum with empty query")
        response = call_tool(
            SearchTools.SEARCH_FORUM,
            {
                SearchForumArgs.QUERY: EMPTY_QUERY,
            },
        )
        mcp_result = _extract_mcp_response(response)
        # Tool returns success with error message in text (not isError=true)
        validate_search_has_content(mcp_result, context="search_forum empty query")
        # Verify the response indicates invalid input
        content = mcp_result.get("content", [])
        text_items = [c.get("text", "") for c in content if c.get("type") == "text"]
        all_text = " ".join(text_items).lower()
        assert "non-empty" in all_text or "invalid" in all_text or "empty" in all_text, (
            f"Expected validation error message for empty query, got: {text_items!r}"
        )

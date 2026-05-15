"""
Happy-path and error-path tests for search-mcp search_documentation tool.

Tests verify:
- isError=false when searching documentation
- isError=true when searching with empty query
- Response contains content

Note: This tool is auth-enhanced - works both ways but returns public-only when logged out.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import SearchDocumentationArgs, SearchTools
from common.constants.test_data import EMPTY_QUERY, SEARCH_QUERY_DOCS
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
class TestSearchDocumentation:
    """
    Happy-path and error-path tests for search_search_documentation tool.
    """

    def test_search_documentation_basic(self, call_tool):
        """
        Searching documentation must return isError=false.

        Uses 'conda' which has extensive documentation.
        """
        logger.info("Calling search_search_documentation for '%s'", SEARCH_QUERY_DOCS)
        response = call_tool(
            SearchTools.SEARCH_DOCUMENTATION,
            {
                SearchDocumentationArgs.QUERY: SEARCH_QUERY_DOCS,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_success(mcp_result, context=f"search_documentation query={SEARCH_QUERY_DOCS!r}")
        validate_search_has_content(mcp_result, context=f"search_documentation query={SEARCH_QUERY_DOCS!r}")

    def test_search_documentation_empty_query(self, call_tool):
        """
        Searching documentation with an empty query returns text content with an error message.

        search-mcp returns isError=false with a validation message in text content
        rather than setting isError=true. This test validates graceful handling.
        """
        logger.info("Calling search_search_documentation with empty query")
        response = call_tool(
            SearchTools.SEARCH_DOCUMENTATION,
            {
                SearchDocumentationArgs.QUERY: EMPTY_QUERY,
            },
        )
        mcp_result = _extract_mcp_response(response)
        # Tool returns success with error message in text (not isError=true)
        validate_search_has_content(mcp_result, context="search_documentation empty query")
        # Verify the response indicates invalid input
        content = mcp_result.get("content", [])
        text_items = [c.get("text", "") for c in content if c.get("type") == "text"]
        all_text = " ".join(text_items).lower()
        assert "non-empty" in all_text or "invalid" in all_text or "empty" in all_text, (
            f"Expected validation error message for empty query, got: {text_items!r}"
        )

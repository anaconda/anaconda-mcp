"""
Happy-path and error-path tests for search-mcp search_documentation tool.

Tests verify:
- isError=false when searching documentation
- isError=true when searching with empty query
- Response contains content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import SearchDocumentationArgs, SearchTools
from common.constants.test_data import EMPTY_QUERY, SEARCH_QUERY_DOCS
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
        Searching documentation with an empty query must return isError=true.

        Validates error handling for invalid input.
        """
        logger.info("Calling search_search_documentation with empty query")
        response = call_tool(
            SearchTools.SEARCH_DOCUMENTATION,
            {
                SearchDocumentationArgs.QUERY: EMPTY_QUERY,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_error(mcp_result, context="search_documentation empty query")

"""
Tests for search-mcp search_collections_and_files tool.

Tests verify:
- When authenticated: isError=false and response contains content
- When unauthenticated: graceful auth error response

This tool requires authentication to return results.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import SearchCollectionsFilesArgs, SearchTools
from common.constants.test_data import SEARCH_QUERY_COLLECTIONS
from common.utils.auth_service import AuthState
from common.utils.response_validators import (
    validate_auth_error_response,
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
class TestSearchCollectionsFiles:
    """
    Tests for search_search_collections_and_files tool.

    Tests run in both authenticated and unauthenticated modes with
    different expectations for each.
    """

    def test_search_collections_files_basic(self, call_tool, auth_state: AuthState):
        """
        Search collections and files behavior depends on auth state.

        - Authenticated: returns isError=false with results
        - Unauthenticated: returns graceful auth error
        """
        logger.info(
            "Calling search_search_collections_and_files for '%s' (auth=%s)",
            SEARCH_QUERY_COLLECTIONS,
            auth_state.logged_in,
        )
        response = call_tool(
            SearchTools.SEARCH_COLLECTIONS_AND_FILES,
            {
                SearchCollectionsFilesArgs.QUERY: SEARCH_QUERY_COLLECTIONS,
            },
        )
        mcp_result = _extract_mcp_response(response)

        if auth_state.logged_in:
            validate_search_success(mcp_result, context=f"search_collections query={SEARCH_QUERY_COLLECTIONS!r}")
            validate_search_has_content(mcp_result, context=f"search_collections query={SEARCH_QUERY_COLLECTIONS!r}")
        else:
            validate_auth_error_response(mcp_result, context=f"search_collections query={SEARCH_QUERY_COLLECTIONS!r}")

"""
Happy-path test for search-mcp search_collections_and_files tool.

Tests verify:
- isError=false when searching collections and files
- Response contains content

Note: This tool requires authentication. Tests skip when not logged in.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import SearchCollectionsFilesArgs, SearchTools
from common.constants.test_data import SEARCH_QUERY_COLLECTIONS
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
class TestSearchCollectionsFiles:
    """
    Happy-path tests for search_search_collections_and_files tool.
    """

    def test_search_collections_files_basic(self, call_tool, require_auth):
        """
        Searching collections and files must return isError=false.

        Uses 'data' which is a broad search term.
        """

        logger.info("Calling search_search_collections_and_files for '%s'", SEARCH_QUERY_COLLECTIONS)
        response = call_tool(
            SearchTools.SEARCH_COLLECTIONS_AND_FILES,
            {
                SearchCollectionsFilesArgs.QUERY: SEARCH_QUERY_COLLECTIONS,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_search_success(mcp_result, context=f"search_collections query={SEARCH_QUERY_COLLECTIONS!r}")
        validate_search_has_content(mcp_result, context=f"search_collections query={SEARCH_QUERY_COLLECTIONS!r}")

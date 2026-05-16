"""
Tests for search-mcp search_environments tool.

Tests verify:
- When authenticated: isError=false and response contains content
- When unauthenticated: graceful auth error response

This tool requires authentication to return results.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import SearchEnvironmentsArgs, SearchTools
from common.constants.test_data import SEARCH_QUERY_ENVIRONMENTS
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
class TestSearchEnvironments:
    """
    Tests for search_search_environments tool.

    Tests run in both authenticated and unauthenticated modes with
    different expectations for each.
    """

    def test_search_environments_basic(self, call_tool, auth_state: AuthState):
        """
        Search environments behavior depends on auth state.

        - Authenticated: returns isError=false with results
        - Unauthenticated: returns graceful auth error
        """
        logger.info(
            "Calling search_search_environments for '%s' (auth=%s)",
            SEARCH_QUERY_ENVIRONMENTS,
            auth_state.logged_in,
        )
        response = call_tool(
            SearchTools.SEARCH_ENVIRONMENTS,
            {
                SearchEnvironmentsArgs.QUERY: SEARCH_QUERY_ENVIRONMENTS,
            },
        )
        mcp_result = _extract_mcp_response(response)

        if auth_state.logged_in:
            validate_search_success(mcp_result, context=f"search_environments query={SEARCH_QUERY_ENVIRONMENTS!r}")
            validate_search_has_content(mcp_result, context=f"search_environments query={SEARCH_QUERY_ENVIRONMENTS!r}")
        else:
            validate_auth_error_response(mcp_result, context=f"search_environments query={SEARCH_QUERY_ENVIRONMENTS!r}")

    def test_search_environments_with_platform_filter(self, call_tool, auth_state: AuthState):
        """
        Search environments with platform filter behavior depends on auth state.

        - Authenticated: returns isError=false with results
        - Unauthenticated: returns graceful auth error
        """
        logger.info(
            "Calling search_search_environments for '%s' with platform filter (auth=%s)",
            SEARCH_QUERY_ENVIRONMENTS,
            auth_state.logged_in,
        )
        response = call_tool(
            SearchTools.SEARCH_ENVIRONMENTS,
            {
                SearchEnvironmentsArgs.QUERY: SEARCH_QUERY_ENVIRONMENTS,
                SearchEnvironmentsArgs.PLATFORMS: "linux-64",  # string, not list
            },
        )
        mcp_result = _extract_mcp_response(response)

        if auth_state.logged_in:
            validate_search_success(mcp_result, context="search_environments query=python platform=linux-64")
            validate_search_has_content(mcp_result, context="search_environments query=python platform=linux-64")
        else:
            validate_auth_error_response(mcp_result, context="search_environments query=python platform=linux-64")

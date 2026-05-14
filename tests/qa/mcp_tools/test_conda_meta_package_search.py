"""
Happy-path and error-path tests for conda-meta-mcp package_search tool.

Tests verify:
- isError=false when searching for an existing package
- isError=false when searching with version spec
- isError=true when searching for a nonexistent package
- Response contains text content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CondaMetaTools, PackageSearchArgs
from common.constants.test_data import (
    NONEXISTENT_PACKAGE_SPEC,
    SEARCH_PACKAGE,
    SEARCH_PACKAGE_WITH_VERSION,
)
from common.utils.response_validators import (
    validate_conda_meta_error,
    validate_conda_meta_success,
    validate_conda_meta_text_content,
)

logger = logging.getLogger(__name__)


def _extract_mcp_response(response: dict):
    """Extract MCP response from call_tool result (handles different formats)."""
    if "result" in response:
        return response["result"]
    return response


@pytest.mark.slow
class TestCondaMetaPackageSearch:
    """
    Happy-path and error-path tests for conda-meta_package_search tool.
    """

    def test_package_search_basic(self, call_tool):
        """
        Searching for an existing package must return isError=false.

        Uses 'numpy' which is ubiquitous in conda channels.
        """
        logger.info("Calling conda-meta_package_search for '%s'", SEARCH_PACKAGE)
        response = call_tool(
            CondaMetaTools.PACKAGE_SEARCH,
            {
                PackageSearchArgs.PACKAGE_REF_OR_MATCH_SPEC: SEARCH_PACKAGE,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"package_search spec={SEARCH_PACKAGE!r}")
        validate_conda_meta_text_content(mcp_result, context=f"package_search spec={SEARCH_PACKAGE!r}")

    def test_package_search_with_version(self, call_tool):
        """
        Searching with a version spec must return isError=false.

        Uses 'numpy>=1.20' to test version constraint handling.
        """
        logger.info("Calling conda-meta_package_search for '%s'", SEARCH_PACKAGE_WITH_VERSION)
        response = call_tool(
            CondaMetaTools.PACKAGE_SEARCH,
            {
                PackageSearchArgs.PACKAGE_REF_OR_MATCH_SPEC: SEARCH_PACKAGE_WITH_VERSION,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"package_search spec={SEARCH_PACKAGE_WITH_VERSION!r}")
        validate_conda_meta_text_content(mcp_result, context=f"package_search spec={SEARCH_PACKAGE_WITH_VERSION!r}")

    def test_package_search_nonexistent(self, call_tool):
        """
        Searching for a nonexistent package must return isError=true.

        Uses a guaranteed-nonexistent package name.
        """
        logger.info("Calling conda-meta_package_search for nonexistent '%s'", NONEXISTENT_PACKAGE_SPEC)
        response = call_tool(
            CondaMetaTools.PACKAGE_SEARCH,
            {
                PackageSearchArgs.PACKAGE_REF_OR_MATCH_SPEC: NONEXISTENT_PACKAGE_SPEC,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_error(mcp_result, context=f"package_search nonexistent spec={NONEXISTENT_PACKAGE_SPEC!r}")

"""
Happy-path test for conda-meta-mcp package_insights tool.

Tests verify:
- isError=false when getting insights for a package URL
- Response contains text content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CondaMetaTools, PackageInsightsArgs
from common.utils.response_validators import (
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
class TestCondaMetaPackageInsights:
    """
    Happy-path: conda-meta_package_insights tool must succeed.
    """

    def test_package_insights_with_url(self, call_tool):
        """
        Getting package insights with a URL must return isError=false.

        Uses a well-known package URL from anaconda.org.
        """
        url = "https://anaconda.org/conda-forge/numpy"
        logger.info("Calling conda-meta_package_insights for URL '%s'", url)
        response = call_tool(
            CondaMetaTools.PACKAGE_INSIGHTS,
            {
                PackageInsightsArgs.URL: url,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"package_insights url={url!r}")
        validate_conda_meta_text_content(mcp_result, context=f"package_insights url={url!r}")

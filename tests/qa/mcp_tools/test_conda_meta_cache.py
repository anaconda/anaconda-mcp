"""
Happy-path test for conda-meta-mcp cache_maintenance tool.

Tests verify:
- isError=false when calling cache_maintenance
- Response contains text content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CondaMetaTools
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
class TestCondaMetaCacheMaintenance:
    """
    Happy-path: conda-meta_cache_maintenance tool must succeed.
    """

    def test_cache_maintenance_returns_success(self, call_tool):
        """
        Calling cache_maintenance tool must return isError=false.

        The cache_maintenance tool performs cache cleanup operations.
        """
        logger.info("Calling conda-meta_cache_maintenance tool")
        response = call_tool(
            CondaMetaTools.CACHE_MAINTENANCE,
            {},
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context="cache_maintenance tool")
        validate_conda_meta_text_content(mcp_result, context="cache_maintenance tool")

"""
Happy-path test for conda-meta-mcp info tool.

Tests verify:
- isError=false when calling info
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
@pytest.mark.auth_independent
class TestCondaMetaInfo:
    """
    Happy-path: conda-meta_info tool must succeed and return conda system info.
    """

    def test_info_returns_success(self, call_tool):
        """
        Calling info tool must return isError=false.

        The info tool returns conda system information without any arguments.
        """
        logger.info("Calling conda-meta_info tool")
        response = call_tool(
            CondaMetaTools.INFO,
            {},
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context="info tool")
        validate_conda_meta_text_content(mcp_result, context="info tool")

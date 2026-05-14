"""
Happy-path test for conda-meta-mcp file_path_search tool.

Tests verify:
- isError=false when searching for a file path pattern
- Response contains text content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CondaMetaTools, FilePathSearchArgs
from common.constants.test_data import FILE_PATH_PATTERN
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
class TestCondaMetaFilePathSearch:
    """
    Happy-path: conda-meta_file_path_search tool must succeed.
    """

    def test_file_path_search_returns_success(self, call_tool):
        """
        Searching for a file path pattern must return isError=false.

        Uses a common file path pattern that should exist in conda environments.
        """
        logger.info("Calling conda-meta_file_path_search for pattern '%s'", FILE_PATH_PATTERN)
        response = call_tool(
            CondaMetaTools.FILE_PATH_SEARCH,
            {
                FilePathSearchArgs.PATH: FILE_PATH_PATTERN,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"file_path_search path={FILE_PATH_PATTERN!r}")
        validate_conda_meta_text_content(mcp_result, context=f"file_path_search path={FILE_PATH_PATTERN!r}")

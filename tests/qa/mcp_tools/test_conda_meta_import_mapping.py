"""
Happy-path and error-path tests for conda-meta-mcp import_mapping tool.

Tests verify:
- isError=false when mapping a known import name
- isError=true when mapping an unknown import name
- Response contains text content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CondaMetaTools, ImportMappingArgs
from common.constants.test_data import KNOWN_IMPORT, UNKNOWN_IMPORT
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
class TestCondaMetaImportMapping:
    """
    Happy-path and error-path tests for conda-meta_import_mapping tool.
    """

    def test_import_mapping_known_import(self, call_tool):
        """
        Mapping a known import name must return isError=false.

        Uses 'yaml' which maps to 'pyyaml'.
        """
        logger.info("Calling conda-meta_import_mapping for '%s'", KNOWN_IMPORT)
        response = call_tool(
            CondaMetaTools.IMPORT_MAPPING,
            {
                ImportMappingArgs.IMPORT_NAME: KNOWN_IMPORT,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"import_mapping import_name={KNOWN_IMPORT!r}")
        validate_conda_meta_text_content(mcp_result, context=f"import_mapping import_name={KNOWN_IMPORT!r}")

    def test_import_mapping_unknown_import(self, call_tool):
        """
        Mapping an unknown import name must return isError=true.

        Uses a nonexistent module name to verify error handling.
        """
        logger.info("Calling conda-meta_import_mapping for unknown '%s'", UNKNOWN_IMPORT)
        response = call_tool(
            CondaMetaTools.IMPORT_MAPPING,
            {
                ImportMappingArgs.IMPORT_NAME: UNKNOWN_IMPORT,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_error(mcp_result, context=f"import_mapping unknown import_name={UNKNOWN_IMPORT!r}")

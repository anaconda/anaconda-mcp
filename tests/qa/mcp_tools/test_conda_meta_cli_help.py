"""
Happy-path tests for conda-meta-mcp cli_help tool.

Tests verify:
- isError=false when calling cli_help with a tool argument
- isError=false when calling cli_help with grep filter
- Response contains text content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CliHelpArgs, CondaMetaTools
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
class TestCondaMetaCliHelp:
    """
    Happy-path: conda-meta_cli_help tool must succeed and return help text.
    """

    def test_cli_help_basic(self, call_tool):
        """
        Calling cli_help with a tool name must return isError=false.

        Tests the basic help lookup for the conda tool.
        """
        logger.info("Calling conda-meta_cli_help for 'conda'")
        response = call_tool(
            CondaMetaTools.CLI_HELP,
            {
                CliHelpArgs.TOOL: "conda",
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context="cli_help tool=conda")
        validate_conda_meta_text_content(mcp_result, context="cli_help tool=conda")

    def test_cli_help_with_grep(self, call_tool):
        """
        Calling cli_help with grep filter must return isError=false.

        Tests filtering help text with a grep pattern.
        """
        logger.info("Calling conda-meta_cli_help with grep filter")
        response = call_tool(
            CondaMetaTools.CLI_HELP,
            {
                CliHelpArgs.TOOL: "conda",
                CliHelpArgs.GREP: "install",
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context="cli_help tool=conda grep=install")
        validate_conda_meta_text_content(mcp_result, context="cli_help tool=conda grep=install")

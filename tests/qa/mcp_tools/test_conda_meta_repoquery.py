"""
Happy-path and error-path tests for conda-meta-mcp repoquery tool.

Tests verify:
- isError=false when querying dependencies (depends mode)
- isError=false when querying reverse dependencies (whoneeds mode)
- isError=true when querying an invalid package
- Response contains text content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CondaMetaTools, RepoqueryArgs
from common.constants.test_data import (
    NONEXISTENT_PACKAGE_SPEC,
    REPOQUERY_CHANNEL,
    REPOQUERY_SPEC,
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
class TestCondaMetaRepoquery:
    """
    Happy-path and error-path tests for conda-meta_repoquery tool.
    """

    def test_repoquery_depends(self, call_tool):
        """
        Querying package dependencies must return isError=false.

        Uses 'python' to query its dependencies.
        """
        logger.info("Calling conda-meta_repoquery depends for '%s'", REPOQUERY_SPEC)
        response = call_tool(
            CondaMetaTools.REPOQUERY,
            {
                RepoqueryArgs.SUBCMD: "depends",
                RepoqueryArgs.SPEC: REPOQUERY_SPEC,
                RepoqueryArgs.CHANNEL: REPOQUERY_CHANNEL,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"repoquery depends spec={REPOQUERY_SPEC!r}")
        validate_conda_meta_text_content(mcp_result, context=f"repoquery depends spec={REPOQUERY_SPEC!r}")

    def test_repoquery_whoneeds(self, call_tool):
        """
        Querying reverse dependencies must return isError=false.

        Uses 'python' to find packages that depend on it.
        """
        logger.info("Calling conda-meta_repoquery whoneeds for '%s'", REPOQUERY_SPEC)
        response = call_tool(
            CondaMetaTools.REPOQUERY,
            {
                RepoqueryArgs.SUBCMD: "whoneeds",
                RepoqueryArgs.SPEC: REPOQUERY_SPEC,
                RepoqueryArgs.CHANNEL: REPOQUERY_CHANNEL,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"repoquery whoneeds spec={REPOQUERY_SPEC!r}")
        validate_conda_meta_text_content(mcp_result, context=f"repoquery whoneeds spec={REPOQUERY_SPEC!r}")

    def test_repoquery_invalid_package(self, call_tool):
        """
        Querying a nonexistent package must return isError=true.

        Uses a guaranteed-nonexistent package name.
        """
        logger.info("Calling conda-meta_repoquery for nonexistent '%s'", NONEXISTENT_PACKAGE_SPEC)
        response = call_tool(
            CondaMetaTools.REPOQUERY,
            {
                RepoqueryArgs.SUBCMD: "depends",
                RepoqueryArgs.SPEC: NONEXISTENT_PACKAGE_SPEC,
                RepoqueryArgs.CHANNEL: REPOQUERY_CHANNEL,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_error(mcp_result, context=f"repoquery invalid spec={NONEXISTENT_PACKAGE_SPEC!r}")

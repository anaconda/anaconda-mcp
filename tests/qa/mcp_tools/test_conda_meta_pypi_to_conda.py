"""
Happy-path test for conda-meta-mcp pypi_to_conda tool.

Tests verify:
- isError=false when mapping a PyPI package name to conda
- Response contains text content
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CondaMetaTools, PypiToCondaArgs
from common.constants.test_data import FILE_PATH_CHANNEL, PYPI_PACKAGE
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
class TestCondaMetaPypiToConda:
    """
    Happy-path: conda-meta_pypi_to_conda tool must succeed.
    """

    def test_pypi_to_conda_mapping(self, call_tool):
        """
        Mapping a PyPI package name to conda must return isError=false.

        Uses 'PyYAML' which maps to 'pyyaml'.
        """
        logger.info("Calling conda-meta_pypi_to_conda for '%s'", PYPI_PACKAGE)
        response = call_tool(
            CondaMetaTools.PYPI_TO_CONDA,
            {
                PypiToCondaArgs.PYPI_NAME: PYPI_PACKAGE,
                PypiToCondaArgs.CHANNEL: FILE_PATH_CHANNEL,
            },
        )
        mcp_result = _extract_mcp_response(response)
        validate_conda_meta_success(mcp_result, context=f"pypi_to_conda pypi_name={PYPI_PACKAGE!r}")
        validate_conda_meta_text_content(mcp_result, context=f"pypi_to_conda pypi_name={PYPI_PACKAGE!r}")

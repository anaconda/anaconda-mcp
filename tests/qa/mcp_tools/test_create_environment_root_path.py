"""
Regression tests for KI-016 / DESK-1384.

Passing environment_root_path to conda_create_environment must not raise
a Pydantic frozen_instance error.

See tests/qa/_ai_docs/KNOWN_ISSUES.md (KI-016) and
    tests/qa/_ai_docs/bug_ki016/KI-016-bug-report.md for full details.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CreateEnvironmentArgs, Tools
from common.constants.test_data import NONEXISTENT_ENV_PREFIX
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import (
    _validate_no_pydantic_validation_error,
)

logger = logging.getLogger(__name__)

_ENV_NAME = "ki016-regression-test"


@pytest.mark.regression
class TestCreateEnvironmentWithRootPath:
    """KI-016: conda_create_environment with environment_root_path must never return a frozen_instance error."""

    def test_ki016_no_frozen_instance_error(self, call_tool, cleanup_conda_env):
        """No Pydantic frozen_instance error when environment_root_path is provided (KI-016)."""
        cleanup_conda_env(_ENV_NAME)
        logger.info(
            "KI-016: create_environment with environment_root_path='%s'",
            NONEXISTENT_ENV_PREFIX,
        )
        response = call_tool(
            Tools.CONDA_CREATE_ENVIRONMENT,
            {
                CreateEnvironmentArgs.ENVIRONMENT_NAME: _ENV_NAME,
                CreateEnvironmentArgs.PACKAGES: ["python=3.11"],
                CreateEnvironmentArgs.ENVIRONMENT_ROOT_PATH: NONEXISTENT_ENV_PREFIX,
            },
        )
        result = _tool_result(response)
        _validate_no_pydantic_validation_error(
            result,
            response=response,
            context=f"environment_root_path={NONEXISTENT_ENV_PREFIX!r}",
        )
        logger.info("KI-016: result: %s", result)

    def test_ki016_response_is_parseable_with_root_path(self, call_tool, cleanup_conda_env):
        """
        Response must be a parseable tool result, not a raw JSON-RPC error body (KI-016).

        On the buggy version the frozen_instance error propagates past fastmcp's
        dispatcher, causing _tool_result() to return {}.  A conda-level error or
        a success result are both acceptable; an empty dict is not.
        """
        cleanup_conda_env(_ENV_NAME)
        logger.info(
            "KI-016: create_environment with environment_root_path='%s'",
            NONEXISTENT_ENV_PREFIX,
        )
        response = call_tool(
            Tools.CONDA_CREATE_ENVIRONMENT,
            {
                CreateEnvironmentArgs.ENVIRONMENT_NAME: _ENV_NAME,
                CreateEnvironmentArgs.PACKAGES: ["python=3.11"],
                CreateEnvironmentArgs.ENVIRONMENT_ROOT_PATH: NONEXISTENT_ENV_PREFIX,
            },
        )
        result = _tool_result(response)
        logger.info("KI-016: result=%s", result)

        _validate_no_pydantic_validation_error(
            result,
            response=response,
            context=f"environment_root_path={NONEXISTENT_ENV_PREFIX!r}",
        )
        assert result != {}, (
            f"KI-016: _tool_result() returned {{}} — server returned a JSON-RPC error "
            f"body instead of a tool result. Raw MCP response: {response!r}"
        )

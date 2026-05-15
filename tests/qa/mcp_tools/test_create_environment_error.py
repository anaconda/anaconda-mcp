"""
Error-path test for conda_create_environment tool.

Tests verify:
- is_error=true when creating an environment with a duplicate name (FR-004)
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CreateEnvironmentArgs, Tools
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import validate_create_error

logger = logging.getLogger(__name__)


@pytest.mark.slow
@pytest.mark.auth_independent
class TestCreateEnvironmentError:
    """
    Error-path: conda_create_environment must return an error when attempting
    to create an environment with a name that already exists.
    """

    def test_create_duplicate_environment_returns_error(self, conda_env, call_tool):
        """
        Creating an environment with an existing name must return is_error=true.

        Uses the shared conda_env fixture which already exists, then attempts
        to create another environment with the same name.
        """
        logger.info("Attempting to create duplicate env '%s'", conda_env["name"])
        response = call_tool(
            Tools.CONDA_CREATE_ENVIRONMENT,
            {
                CreateEnvironmentArgs.ENVIRONMENT_NAME: conda_env["name"],
            },
        )
        result = _tool_result(response)
        validate_create_error(result, context=f"duplicate env_name={conda_env['name']!r}")

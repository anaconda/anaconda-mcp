"""
Happy-path and error-path tests for conda_list_environment_packages tool.

Tests verify:
- is_error=false when listing packages by environment name
- is_error=false when listing packages by prefix
- is_error=true when listing packages for nonexistent environment
- Response contains package list
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import ListEnvironmentPackagesArgs, Tools
from common.constants.test_data import NONEXISTENT_ENV_NAME
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import (
    validate_error_response,
    validate_list_packages_success,
)

logger = logging.getLogger(__name__)


@pytest.mark.slow
@pytest.mark.auth_independent
class TestListEnvironmentPackages:
    """
    Happy-path: conda_list_environment_packages must succeed and return
    a package list — addressed both by name and by prefix.
    """

    def test_list_packages_by_name(self, conda_env, call_tool):
        """
        Listing packages by environment name must return is_error=false.

        Verifies the basic success path with a real environment addressed by name.
        """
        logger.info("Listing packages in env '%s' by name", conda_env["name"])
        response = call_tool(
            Tools.CONDA_LIST_ENVIRONMENT_PACKAGES,
            {
                ListEnvironmentPackagesArgs.ENVIRONMENT: conda_env["name"],
            },
        )
        result = _tool_result(response)
        validate_list_packages_success(result, context=f"env_name={conda_env['name']!r}")

    def test_list_packages_by_prefix(self, conda_env, call_tool):
        """
        Listing packages by prefix must return is_error=false.

        Validates the prefix-based lookup path separately from the name-based path.
        """
        logger.info(
            "Listing packages in env '%s' by prefix '%s'",
            conda_env["name"],
            conda_env["prefix"],
        )
        response = call_tool(
            Tools.CONDA_LIST_ENVIRONMENT_PACKAGES,
            {
                ListEnvironmentPackagesArgs.PREFIX: conda_env["prefix"],
            },
        )
        result = _tool_result(response)
        validate_list_packages_success(result, context=f"prefix={conda_env['prefix']!r}")


@pytest.mark.slow
@pytest.mark.auth_independent
class TestListEnvironmentPackagesErrors:
    """
    Error-path: conda_list_environment_packages must return is_error=true for invalid inputs.
    """

    def test_list_packages_nonexistent_env(self, call_tool):
        """
        Listing packages for a nonexistent environment must return is_error=true.

        Validates error handling for invalid environment lookup.
        """
        logger.info("Listing packages in nonexistent env '%s'", NONEXISTENT_ENV_NAME)
        response = call_tool(
            Tools.CONDA_LIST_ENVIRONMENT_PACKAGES,
            {
                ListEnvironmentPackagesArgs.ENVIRONMENT: NONEXISTENT_ENV_NAME,
            },
        )
        result = _tool_result(response)
        validate_error_response(result, context=f"nonexistent env={NONEXISTENT_ENV_NAME!r}")

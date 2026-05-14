"""
Happy-path test for conda_remove_environment tool.

Tests verify:
- is_error=false when removing an environment by name

Note: This test creates a fresh environment, then removes it to verify the remove path.
Uses a dedicated environment name to avoid conflicts with the shared conda_env fixture.
"""

from __future__ import annotations

import logging
import uuid

import pytest
from common.constants.mcp_tools import (
    CreateEnvironmentArgs,
    RemoveEnvironmentArgs,
    Tools,
)
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import validate_remove_success

logger = logging.getLogger(__name__)


@pytest.mark.slow
class TestRemoveEnvironment:
    """
    Happy-path: conda_remove_environment must succeed when removing a real environment.
    """

    def test_remove_environment_by_name(self, call_tool):
        """
        Removing an environment by name must return is_error=false.

        Creates a temporary environment, then removes it to verify the remove path works.
        """
        env_name = f"qa-remove-test-{uuid.uuid4().hex[:8]}"
        logger.info("Creating temporary env '%s' for removal test", env_name)

        create_response = call_tool(
            Tools.CONDA_CREATE_ENVIRONMENT,
            {
                CreateEnvironmentArgs.ENVIRONMENT_NAME: env_name,
            },
        )
        create_result = _tool_result(create_response)
        assert not create_result.get("is_error"), f"Failed to create env: {create_result}"

        logger.info("Removing env '%s' by name", env_name)
        response = call_tool(
            Tools.CONDA_REMOVE_ENVIRONMENT,
            {
                RemoveEnvironmentArgs.ENVIRONMENT_NAME: env_name,
            },
        )
        result = _tool_result(response)
        validate_remove_success(result, context=f"env_name={env_name!r}")

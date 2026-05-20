"""
Idempotent behavior test for conda_create_environment tool.

Tests verify:
- Creating an environment that already exists is idempotent (returns success with 'No changes needed!')
- Requalified per AIC-3337: this is expected conda behavior, not an error
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import CreateEnvironmentArgs, Tools
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import validate_create_success

logger = logging.getLogger(__name__)


@pytest.mark.slow
@pytest.mark.auth_independent
class TestCreateEnvironmentIdempotent:
    """
    Idempotent behavior: conda_create_environment returns success when the
    environment already exists (no-op with 'No changes needed!' message).
    """

    def test_create_duplicate_environment_is_idempotent(self, conda_env, call_tool):
        """
        Creating an environment with an existing name must return is_error=false.

        Uses the shared conda_env fixture which already exists, then attempts
        to create another environment with the same name. Conda's behavior is
        idempotent - it returns success with 'No changes needed!' message.
        """
        logger.info("Attempting to create duplicate env '%s' (expect idempotent success)", conda_env["name"])
        response = call_tool(
            Tools.CONDA_CREATE_ENVIRONMENT,
            {
                CreateEnvironmentArgs.ENVIRONMENT_NAME: conda_env["name"],
            },
        )
        result = _tool_result(response)
        validate_create_success(result, context=f"idempotent create env_name={conda_env['name']!r}")
        # Verify the idempotent message
        tool_result = result.get("tool_result", {})
        message = tool_result.get("message", "")
        assert "no changes needed" in message.lower(), (
            f"Expected 'No changes needed!' message for idempotent create, got: {message!r}"
        )

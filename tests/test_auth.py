import logging
from unittest import mock

import pytest
from click.testing import CliRunner

from anaconda_mcp.auth import AuthenticationError
from anaconda_mcp.cli import cli

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_get_auth_token(mocked_token):
    with mock.patch("anaconda_mcp.auth.get_auth_token") as m:
        m.return_value = mocked_token
        yield m


@pytest.fixture
def mock_serve_command():
    with mock.patch("anaconda_mcp.cli._serve") as m:
        m.return_value = 0
        yield m


@pytest.fixture
def mock_base_client():
    with mock.patch("anaconda_mcp.auth.BaseClient") as m:
        m.return_value.account = {"user": {"created_at": "2020-01-01T00:00:00Z"}}
        yield m


@pytest.fixture
def mock_snake_eyes():
    with mock.patch("anaconda_mcp.auth.SnakeEyes") as m:
        yield m


async def test_cli_gates_on_token_not_found(mock_token_info_load):
    mock_token_info_load.return_value = None

    runner = CliRunner()
    result = runner.invoke(cli, ["clients"])

    assert result.exit_code == 1


async def test_auth_enforcement_hook_raises_authentication_error_on_missing_token():
    # Given - no token available
    from anaconda_mcp.auth import make_auth_enforcement_hook

    hook_fn = make_auth_enforcement_hook(lambda: None)

    async def original_call_tool(self, name, arguments, context=None, convert_result=False):
        return "success"

    enforced_call = hook_fn(original_call_tool)

    # When/Then - should raise AuthenticationError
    with pytest.raises(AuthenticationError, match="Not authenticated"):
        await enforced_call(None, "test_tool", {})


async def test_auth_enforcement_hook_raises_authentication_error_on_invalid_token():
    # Given - invalid token
    from anaconda_mcp.auth import make_auth_enforcement_hook

    hook_fn = make_auth_enforcement_hook(lambda: "invalid-token")

    async def original_call_tool(self, name, arguments, context=None, convert_result=False):
        return "success"

    enforced_call = hook_fn(original_call_tool)

    # When - mock validate_auth_token to return False
    with mock.patch("anaconda_mcp.auth.validate_auth_token", return_value=False):
        # Then - should raise AuthenticationError
        with pytest.raises(AuthenticationError, match="Authentication token is invalid or expired"):
            await enforced_call(None, "test_tool", {})


async def test_auth_enforcement_hook_passes_with_valid_token():
    # Given - valid token
    from anaconda_mcp.auth import make_auth_enforcement_hook

    hook_fn = make_auth_enforcement_hook(lambda: "valid-token")

    async def original_call_tool(self, name, arguments, context=None, convert_result=False):
        return "success"

    enforced_call = hook_fn(original_call_tool)

    # When - mock validate_auth_token to return True
    with mock.patch("anaconda_mcp.auth.validate_auth_token", return_value=True):
        # Then - should call the original tool and return success
        result = await enforced_call(None, "test_tool", {})
        assert result == "success"


async def test_serve_exits_immediately_without_token():
    # Given - no token available
    runner = CliRunner()

    # When - invoke serve with no token (override the autouse fixture)
    with mock.patch("anaconda_mcp.cli.get_auth_token", return_value=None):
        with mock.patch("anaconda_mcp.cli.Path.exists", return_value=True):
            result = runner.invoke(cli, ["serve"])

    # Then - should exit with code 1
    assert result.exit_code == 1

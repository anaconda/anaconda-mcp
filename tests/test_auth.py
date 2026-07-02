import logging
from unittest import mock

import pytest
from click.testing import CliRunner

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


async def test_serve_exits_immediately_without_token():
    # Given - no token available
    runner = CliRunner()

    # When - invoke serve with no token (override the autouse fixture)
    with mock.patch("anaconda_mcp.cli.get_auth_token", return_value=None):
        with mock.patch("anaconda_mcp.cli.Path.exists", return_value=True):
            result = runner.invoke(cli, ["serve"])

    # Then - should exit with code 1
    assert result.exit_code == 1

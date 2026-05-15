from unittest import mock

import pytest

MOCKED_TOKEN = "mocked_token"


@pytest.fixture
def mocked_token():
    return MOCKED_TOKEN


@pytest.fixture(autouse=True)
def mock_token_info_load():
    """Patch get_auth_token in cli.py so CLI commands don't require real auth."""
    with mock.patch("anaconda_mcp.cli.get_auth_token", return_value=MOCKED_TOKEN) as m:
        with mock.patch("anaconda_mcp.cli.validate_auth_token", return_value=True):
            yield m

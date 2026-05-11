from unittest import mock

import pytest

MOCKED_TOKEN = "mocked_token"


@pytest.fixture
def mocked_token():
    return MOCKED_TOKEN


@pytest.fixture(autouse=True)
def mock_token_info_load():
    """Patch TokenInfo.load() in cli.py so CLI commands don't require real auth."""
    with mock.patch("anaconda_mcp.cli.TokenInfo.load") as m:
        yield m

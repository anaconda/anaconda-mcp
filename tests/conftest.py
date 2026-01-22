from unittest import mock

import pytest

MOCKED_TOKEN = "mocked_token"

@pytest.fixture
def mocked_token():
    return MOCKED_TOKEN


@pytest.fixture
def mock_get_auth_token(mocked_token):
    with mock.patch("anaconda_mcp.telemetry.get_auth_token") as m:
        m.return_value = mocked_token
        yield m

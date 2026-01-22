from unittest import mock

import pytest


@pytest.fixture
def mocked_token():
    return "mocked_token"


@pytest.fixture
def mock_get_auth_token(mocked_token):
    with mock.patch("anaconda_mcp.telemetry.get_auth_token") as m:
        m.return_value = mocked_token
        yield m

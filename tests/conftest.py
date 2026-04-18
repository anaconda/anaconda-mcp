import pytest

MOCKED_TOKEN = "mocked_token"


@pytest.fixture
def mocked_token():
    return MOCKED_TOKEN

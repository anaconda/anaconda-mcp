import pytest

MOCKED_TOKEN = "mocked_token"


@pytest.fixture
def mocked_token():
    return MOCKED_TOKEN


@pytest.fixture(autouse=True)
def _bypass_terms_gate(monkeypatch):
    monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", True)

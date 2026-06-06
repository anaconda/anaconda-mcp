from unittest import mock

import pytest

from anaconda_mcp.terms import CURRENT_TOS_VERSION

MOCKED_TOKEN = "mocked_token"


@pytest.fixture
def mocked_token():
    return MOCKED_TOKEN


@pytest.fixture(autouse=True)
def _bypass_terms_gate(monkeypatch):
    monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", True)
    monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms_version", CURRENT_TOS_VERSION)


@pytest.fixture(autouse=True)
def mock_token_info_load():
    """Patch get_auth_token in cli.py + telemetry.py so CLI commands and
    emit_event() don't require real auth."""
    with (
        mock.patch("anaconda_mcp.cli.get_auth_token", return_value=MOCKED_TOKEN) as m,
        mock.patch("anaconda_mcp.cli.validate_auth_token", return_value=True),
        mock.patch("anaconda_mcp.telemetry.get_auth_token", return_value=MOCKED_TOKEN),
    ):
        yield m

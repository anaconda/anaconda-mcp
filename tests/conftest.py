import signal as _signal
from unittest import mock

import anaconda_cli_base.lifecycle as _lifecycle
import pytest

import anaconda_mcp._shutdown as _mcp_shutdown
from anaconda_mcp.terms import CURRENT_TOS_VERSION

MOCKED_TOKEN = "mocked_token"


def _reset_shutdown_globals() -> None:
    _mcp_shutdown._handlers_installed = False
    _lifecycle._handlers_installed = False
    _lifecycle._triggered = False
    _lifecycle._hooks = []


@pytest.fixture(autouse=True)
def _isolate_shutdown_state():
    """Reset process-wide signal/shutdown module globals around every test.

    serve()/install_shutdown_handlers() flip install-once guards in cli-base
    lifecycle and mcp _shutdown. Without this reset those mutations leak across
    tests (e.g. a re-patched bridge wraps a leaked bridge, firing
    trigger_shutdown twice).
    """
    orig_sigterm = _signal.getsignal(_signal.SIGTERM)
    orig_sigint = _signal.getsignal(_signal.SIGINT)
    _reset_shutdown_globals()
    yield
    _signal.signal(_signal.SIGTERM, orig_sigterm)
    _signal.signal(_signal.SIGINT, orig_sigint)
    _reset_shutdown_globals()


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

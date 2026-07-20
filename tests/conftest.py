import base64
import json
import signal as _signal
from unittest import mock

import anaconda_cli_base.lifecycle as _lifecycle
import pytest

import anaconda_mcp._shutdown as _mcp_shutdown
import anaconda_mcp.auth as _mcp_auth
import anaconda_mcp.mcp_state as _mcp_state
import anaconda_mcp.telemetry as _mcp_telemetry
from anaconda_mcp.terms import CURRENT_TOS_VERSION

MOCKED_TOKEN = "mocked_token"

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
_payload = base64.urlsafe_b64encode(json.dumps({"sub": TEST_USER_ID}).encode()).rstrip(b"=").decode()
VALID_TEST_JWT = f"h.{_payload}.s"

BASE_DIMENSION_KEYS = frozenset(
    {
        "schema_version",
        "install_id",
        "distribution_surface",
        "python_version",
        "package_version",
        "user_environment",
    }
)


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
    _mcp_auth._reset_user_id_cache()
    with (
        mock.patch("anaconda_mcp.cli.get_auth_token", return_value=MOCKED_TOKEN) as m,
        mock.patch("anaconda_mcp.cli.validate_auth_token", return_value=True),
        mock.patch("anaconda_mcp.telemetry.get_auth_token", return_value=MOCKED_TOKEN),
        mock.patch("anaconda_mcp.auth.get_auth_token", return_value=VALID_TEST_JWT),
    ):
        yield m
    _mcp_auth._reset_user_id_cache()


@pytest.fixture(autouse=True)
def _isolate_mcp_state(tmp_path, monkeypatch):
    """Redirect MCP state to a temp file and reset telemetry caches for every test.

    emit_event() -> _base_dimensions() -> get_or_create_install_id() reads/writes the
    state file unless _STATE_PATH is patched, so any event-emitting test would otherwise
    mutate the real ~/.anaconda/mcp_state.json (and leave the module-level install_id memo
    populated across tests). _base_dimensions() is itself cached per process, so its result
    is cleared too — otherwise a test that monkeypatches a dimension resolver would see a
    dict cached by an earlier test. Tests that need their own state path (test_mcp_state.py,
    test_install_state.py) re-patch _STATE_PATH after this fixture; last-applied wins, so
    they compose cleanly.
    """
    _mcp_telemetry._base_dimensions.cache_clear()
    _mcp_state._reset_install_id_cache()
    monkeypatch.setattr(_mcp_state, "_STATE_PATH", tmp_path / "mcp_state.json")
    yield
    _mcp_telemetry._base_dimensions.cache_clear()
    _mcp_state._reset_install_id_cache()


@pytest.fixture(autouse=True)
def _isolate_distribution_surface(monkeypatch):
    """Clear the surface env var and the detector's memoized cache around every test.

    Without this, a host/CI-exported ANACONDA_MCP_DISTRIBUTION_SURFACE would leak
    into every test (short-circuiting the resolver), and a cached
    _detect_distribution_surface() result from an earlier test would leak into a
    later one that expects fresh auto-detection.
    """
    monkeypatch.delenv("ANACONDA_MCP_DISTRIBUTION_SURFACE", raising=False)
    _mcp_telemetry._detect_distribution_surface.cache_clear()
    yield
    _mcp_telemetry._detect_distribution_surface.cache_clear()

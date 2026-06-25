"""Task 2: PlatformMiddleware unit tests (auth + TOS + telemetry). Hermetic — no network."""

import contextlib
import types

import pytest

from anaconda_mcp import composition
from anaconda_mcp.auth import AuthenticationError
from anaconda_mcp.composition import PlatformMiddleware


@pytest.fixture(autouse=True)
def _stub_otel(monkeypatch):
    """Stub the OTel span context manager so tests don't touch telemetry infra."""

    @contextlib.contextmanager
    def _dummy(*args, **kwargs):
        yield types.SimpleNamespace(add_exception=lambda exc: None)

    monkeypatch.setattr(composition, "_otel_traced", _dummy)


def _ctx(name: str = "conda_list_environments"):
    return types.SimpleNamespace(message=types.SimpleNamespace(name=name), fastmcp_context=None)


def _recording_call_next(store):
    async def call_next(ctx):
        store.append(ctx)
        return "RESULT"

    return call_next


async def test_auth_missing_token_raises_and_skips_call(monkeypatch):
    monkeypatch.setattr(composition, "get_auth_token", lambda: None)
    calls: list = []
    mw = PlatformMiddleware()
    with pytest.raises(AuthenticationError):
        await mw.on_call_tool(_ctx(), _recording_call_next(calls))
    assert calls == []  # call_next never invoked when unauthenticated


async def test_invalid_token_raises_and_skips_call(monkeypatch):
    monkeypatch.setattr(composition, "get_auth_token", lambda: "tok")
    monkeypatch.setattr(composition, "validate_auth_token", lambda t: False)
    calls: list = []
    mw = PlatformMiddleware()
    with pytest.raises(AuthenticationError):
        await mw.on_call_tool(_ctx(), _recording_call_next(calls))
    assert calls == []


async def test_terms_not_accepted_raises_and_skips_call(monkeypatch):
    monkeypatch.setattr(composition, "get_auth_token", lambda: "tok")
    monkeypatch.setattr(composition, "validate_auth_token", lambda t: True)

    class _TermsRejected(Exception):
        pass

    def _reject() -> None:
        raise _TermsRejected("must accept terms")

    monkeypatch.setattr(composition, "verify_terms_accepted", _reject)
    calls: list = []
    mw = PlatformMiddleware()
    with pytest.raises(_TermsRejected):
        await mw.on_call_tool(_ctx(), _recording_call_next(calls))
    assert calls == []


async def test_happy_path_calls_next_and_emits_event(monkeypatch):
    monkeypatch.setattr(composition, "get_auth_token", lambda: "tok")
    monkeypatch.setattr(composition, "validate_auth_token", lambda t: True)
    monkeypatch.setattr(composition, "verify_terms_accepted", lambda: None)
    monkeypatch.setattr(composition.settings, "send_metrics", True)
    events: list = []
    monkeypatch.setattr(composition, "emit_event", lambda metric, params: events.append((metric, params)))
    monkeypatch.setattr(composition, "_emit_tool_metrics", lambda *a, **k: None)

    calls: list = []
    mw = PlatformMiddleware()
    result = await mw.on_call_tool(_ctx("conda_create_environment"), _recording_call_next(calls))

    assert result == "RESULT"
    assert len(calls) == 1  # call_next invoked exactly once
    assert len(events) == 1
    _metric, params = events[0]
    assert params["tool_name"] == "conda_create_environment"
    assert params["is_error"] is False


async def test_error_in_call_next_emits_is_error_and_reraises(monkeypatch):
    monkeypatch.setattr(composition, "get_auth_token", lambda: "tok")
    monkeypatch.setattr(composition, "validate_auth_token", lambda t: True)
    monkeypatch.setattr(composition, "verify_terms_accepted", lambda: None)
    monkeypatch.setattr(composition.settings, "send_metrics", True)
    events: list = []
    monkeypatch.setattr(composition, "emit_event", lambda metric, params: events.append((metric, params)))
    monkeypatch.setattr(composition, "_emit_tool_metrics", lambda *a, **k: None)

    async def boom(ctx):
        raise ValueError("tool blew up")

    mw = PlatformMiddleware()
    with pytest.raises(ValueError):
        await mw.on_call_tool(_ctx(), boom)
    assert len(events) == 1
    _metric, params = events[0]
    assert params["is_error"] is True
    assert "ValueError" in params["error_description"]

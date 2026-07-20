"""Task 2: PlatformMiddleware unit tests (auth + TOS + telemetry). Hermetic — no network."""

import contextlib
import types
from unittest import mock

import pytest

from anaconda_mcp import composition
from anaconda_mcp.auth import AuthenticationError
from anaconda_mcp.composition import PlatformMiddleware
from conftest import BASE_DIMENSION_KEYS, TEST_USER_ID


@pytest.fixture(autouse=True)
def _stub_otel(monkeypatch):
    """Stub the OTel span context manager so tests don't touch telemetry infra."""

    @contextlib.contextmanager
    def _dummy(*args, **kwargs):
        yield types.SimpleNamespace(add_exception=lambda exc: None)

    monkeypatch.setattr(composition, "_otel_traced", _dummy)


@pytest.fixture
def captured_events(monkeypatch):
    """Authenticate, accept terms, enable metrics, and capture emitted telemetry events."""
    monkeypatch.setattr(composition, "get_auth_token", lambda: "tok")
    monkeypatch.setattr(composition, "validate_auth_token", lambda t: True)
    monkeypatch.setattr(composition, "verify_terms_accepted", lambda: None)
    monkeypatch.setattr(composition.settings, "send_metrics", True)
    events: list = []
    monkeypatch.setattr(composition, "emit_event", lambda metric, params: events.append((metric, params)))
    monkeypatch.setattr(composition, "_emit_tool_metrics", lambda *a, **k: None)
    return events


def _ctx(name: str = "conda_list_environments"):
    return types.SimpleNamespace(message=types.SimpleNamespace(name=name), fastmcp_context=None)


def _recording_call_next(store):
    async def call_next(ctx):
        store.append(ctx)
        return "RESULT"

    return call_next


class _TermsRejected(Exception):
    pass


def _reject_terms() -> None:
    raise _TermsRejected("must accept terms")


def _cfg_no_token(mp):
    mp.setattr(composition, "get_auth_token", lambda: None)


def _cfg_invalid_token(mp):
    mp.setattr(composition, "get_auth_token", lambda: "tok")
    mp.setattr(composition, "validate_auth_token", lambda t: False)


def _cfg_terms_rejected(mp):
    mp.setattr(composition, "get_auth_token", lambda: "tok")
    mp.setattr(composition, "validate_auth_token", lambda t: True)
    mp.setattr(composition, "verify_terms_accepted", _reject_terms)


@pytest.mark.parametrize(
    "configure, expected_exc",
    [
        pytest.param(_cfg_no_token, AuthenticationError, id="missing-token"),
        pytest.param(_cfg_invalid_token, AuthenticationError, id="invalid-token"),
        pytest.param(_cfg_terms_rejected, _TermsRejected, id="terms-not-accepted"),
    ],
)
async def test_preflight_rejection_raises_and_skips_call(monkeypatch, configure, expected_exc):
    """Auth/TOS preflight failures raise before call_next runs — tool never executes."""
    configure(monkeypatch)
    calls: list = []
    mw = PlatformMiddleware()
    with pytest.raises(expected_exc):
        await mw.on_call_tool(_ctx(), _recording_call_next(calls))
    assert calls == []


async def test_happy_path_calls_next_and_emits_event(captured_events):
    calls: list = []
    mw = PlatformMiddleware()
    result = await mw.on_call_tool(_ctx("conda_create_environment"), _recording_call_next(calls))

    assert result == "RESULT"
    assert len(calls) == 1
    assert len(captured_events) == 1
    _metric, params = captured_events[0]
    assert params["tool_name"] == "conda_create_environment"
    assert params["is_error"] is False


async def test_error_path_emits_is_error_and_redacts_message(captured_events):
    async def boom(ctx):
        raise ValueError("failed command https://x/t/SECRETTOKEN/ch")

    mw = PlatformMiddleware()
    with pytest.raises(ValueError):
        await mw.on_call_tool(_ctx(), boom)

    assert len(captured_events) == 1
    _metric, params = captured_events[0]
    assert params["is_error"] is True
    assert params["error_description"] == "ValueError"
    assert "SECRETTOKEN" not in params["error_description"]


async def test_telemetry_failure_does_not_mask_tool_result(captured_events, monkeypatch):
    def _boom_emit(*args, **kwargs):
        raise RuntimeError("telemetry backend down")

    monkeypatch.setattr(composition, "emit_event", _boom_emit)
    mw = PlatformMiddleware()
    result = await mw.on_call_tool(_ctx(), _recording_call_next([]))
    assert result == "RESULT"


async def test_otel_span_attributes_include_user_id(captured_events):
    """Todo 5: on_call_tool opens the OTel span with user.id (no status field).

    The autouse conftest fixture patches ``anaconda_mcp.auth.get_auth_token`` to
    return ``VALID_TEST_JWT`` (sub=TEST_USER_ID), so ``resolve_user_id()`` --
    called through ``_otel_user_attrs()`` -- resolves deterministically to
    ``TEST_USER_ID``.
    """
    captured_kwargs: dict = {}

    @contextlib.contextmanager
    def _capturing(*args, **kwargs):
        captured_kwargs.update(kwargs)
        yield types.SimpleNamespace(add_exception=lambda exc: None)

    with mock.patch.object(composition, "_otel_traced", _capturing):
        mw = PlatformMiddleware()
        result = await mw.on_call_tool(_ctx("conda_list_environments"), _recording_call_next([]))

    assert result == "RESULT"
    attrs = captured_kwargs["attributes"]
    assert attrs["tool"] == "conda_list_environments"
    assert attrs["user.id"] == TEST_USER_ID
    assert "user.id.status" not in attrs


async def test_otel_span_backstop_when_resolve_user_id_raises(captured_events):
    """Backstop: if resolve_user_id raises, the span still opens and the tool call
    completes. ``user.id`` is OMITTED from the attributes (schema-conforming: no
    sentinel, no status field). ``_otel_user_attrs`` catches the exception and
    returns ``{}``, which the ``**`` merge folds into a no-op.
    """
    captured_kwargs: dict = {}

    @contextlib.contextmanager
    def _capturing(*args, **kwargs):
        captured_kwargs.update(kwargs)
        yield types.SimpleNamespace(add_exception=lambda exc: None)

    with (
        mock.patch.object(composition, "_otel_traced", _capturing),
        mock.patch(
            "anaconda_mcp.telemetry.resolve_user_id",
            side_effect=RuntimeError("boom"),
        ),
    ):
        mw = PlatformMiddleware()
        result = await mw.on_call_tool(_ctx("conda_list_environments"), _recording_call_next([]))

    assert result == "RESULT"
    attrs = captured_kwargs["attributes"]
    assert attrs["tool"] == "conda_list_environments"
    assert "user.id" not in attrs
    assert "user.id.status" not in attrs


async def test_platform_middleware_span_asymmetry_no_base_dimensions(captured_events):
    """SPAN half of the accepted signal-type asymmetry (see the comment above
    _base_dimensions() in telemetry.py): the _otel_traced span opened by
    on_call_tool carries ONLY {tool, user.id} (per _otel_user_attrs), never any
    of the 6 _base_dimensions() keys that OTel events carry via emit_event().
    """
    captured_kwargs: dict = {}

    @contextlib.contextmanager
    def _capturing(*args, **kwargs):
        captured_kwargs.update(kwargs)
        yield types.SimpleNamespace(add_exception=lambda exc: None)

    with mock.patch.object(composition, "_otel_traced", _capturing):
        mw = PlatformMiddleware()
        result = await mw.on_call_tool(_ctx("conda_list_environments"), _recording_call_next([]))

    assert result == "RESULT"
    attrs = captured_kwargs["attributes"]
    assert attrs == {"tool": "conda_list_environments", "user.id": TEST_USER_ID}
    for key in BASE_DIMENSION_KEYS:
        assert key not in attrs

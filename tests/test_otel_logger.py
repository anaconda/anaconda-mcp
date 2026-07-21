"""Tests for emit_event() and the application OTel handler attachment."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from anaconda_mcp.telemetry import (
    MetricData,
    _UserContextLogFilter,
    emit_event,
)
from conftest import BASE_DIMENSION_KEYS, TEST_USER_ID

MOCKED_TOKEN = "mocked_token"


def test_shutdown_telemetry_is_callable():
    """Guard the cli-base public shutdown API mcp depends on — fails loudly with ImportError if renamed."""
    from anaconda_cli_base.telemetry import shutdown_telemetry

    shutdown_telemetry()


def test_emit_event_calls_snake_eyes():
    with patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
        emit_event("anaconda_mcp_start_server", {"x": 1})

    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    metric_data = args[0]
    assert isinstance(metric_data, MetricData)
    assert metric_data.event == "anaconda_mcp_start_server"
    assert metric_data.event_params == {"x": 1}
    assert kwargs["bearer_token"] == MOCKED_TOKEN
    assert kwargs["blocking"] is False


def test_emit_event_calls_log_event():
    with patch("anaconda_mcp.telemetry.log_event") as mock_log_event:
        emit_event("anaconda_mcp_start_server", {"x": 1})

    mock_log_event.assert_called_once()
    args, kwargs = mock_log_event.call_args
    assert args[0] == "anaconda_mcp_start_server"
    assert kwargs["event_name"] == "anaconda_mcp_start_server"
    assert kwargs["plugin_name"] == "mcp"
    attributes = kwargs["attributes"]
    assert attributes["x"] == 1
    assert attributes["user.id"] == TEST_USER_ID
    assert "user.id.status" not in attributes


def test_emit_event_log_event_includes_base_dimensions():
    """Every OTel log_event call carries the 6 _base_dimensions() keys plus user.id."""
    with patch("anaconda_mcp.telemetry.log_event") as mock_log_event:
        emit_event("some_event", {})

    attributes = mock_log_event.call_args.kwargs["attributes"]
    for key in BASE_DIMENSION_KEYS:
        assert key in attributes
    assert attributes["user.id"] == TEST_USER_ID


def test_emit_event_snake_eyes_payload_excludes_base_dimensions():
    """Base dimensions are OTel-only; snake-eyes event_params stays byte-identical to the caller's input."""
    with patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
        emit_event("some_event", {"x": 1})

    metric_data = mock_send.call_args[0][0]
    assert metric_data.event_params == {"x": 1}


def test_emit_event_base_dimensions_win_over_event_param_collision():
    """Base dimensions are authoritative: a caller-supplied event param with
    the same name as a base dimension is overridden, not the other way around
    (closes a footgun where a future caller forwarding untrusted keys could
    bypass a trusted dimension's value on the OTel path)."""
    with patch("anaconda_mcp.telemetry.log_event") as mock_log_event:
        emit_event("some_event", {"user.environment": "caller-supplied-value"})

    attributes = mock_log_event.call_args.kwargs["attributes"]
    assert attributes["user.environment"] != "caller-supplied-value"


def test_emit_event_filters_pii_for_otel_only():
    with (
        patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send,
        patch("anaconda_mcp.telemetry.log_event") as mock_log_event,
    ):
        emit_event(
            "anaconda_mcp_contact_consent",
            {"contact": True, "email": "a@b", "uuid": "1"},
        )

    mock_send.assert_called_once()
    metric_data = mock_send.call_args[0][0]
    assert metric_data.event_params == {
        "contact": True,
        "email": "a@b",
        "uuid": "1",
    }

    mock_log_event.assert_called_once()
    attributes = mock_log_event.call_args.kwargs["attributes"]
    assert attributes["contact"] is True
    assert "email" not in attributes
    assert "uuid" not in attributes
    assert attributes["user.id"] == TEST_USER_ID
    assert "user.id.status" not in attributes


def test_emit_event_pii_stripped_but_user_id_present():
    """PII filter removes email but user.id survives (merged AFTER the filter)."""
    with patch("anaconda_mcp.telemetry.log_event") as mock_log_event:
        emit_event("x", {"email": "a@b"})

    mock_log_event.assert_called_once()
    attributes = mock_log_event.call_args.kwargs["attributes"]
    assert "email" not in attributes
    assert attributes["user.id"] == TEST_USER_ID
    assert "user.id.status" not in attributes


def test_emit_event_blocking_passes_through():
    with patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
        emit_event("x", {}, blocking=True)

    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["blocking"] is True


def test_emit_event_send_metrics_disabled_skips_both(monkeypatch):
    monkeypatch.setattr("anaconda_mcp.telemetry.settings.send_metrics", False)
    with (
        patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send,
        patch("anaconda_mcp.telemetry.log_event") as mock_log_event,
    ):
        emit_event("x", {})

    mock_send.assert_not_called()
    mock_log_event.assert_not_called()


@pytest.mark.parametrize(
    ("failing", "asserted"),
    [
        ("anaconda_mcp.telemetry.log_event", "anaconda_mcp.telemetry.SnakeEyes.send"),
        ("anaconda_mcp.telemetry.SnakeEyes.send", "anaconda_mcp.telemetry.log_event"),
    ],
    ids=["otel_failure_isolated_from_snake_eyes", "snake_eyes_failure_isolated_from_otel"],
)
def test_emit_event_sink_failure_isolation(failing: str, asserted: str):
    """One sink raising must not prevent the other from firing."""
    with (
        patch(failing, side_effect=RuntimeError("boom")),
        patch(asserted) as mock_other,
    ):
        emit_event("x", {})

    mock_other.assert_called_once()


def test_application_logger_has_otel_handler_after_cli_init():
    from anaconda_mcp.cli import _attach_application_otel_handler

    _attach_application_otel_handler.cache_clear()

    pkg_logger = logging.getLogger("anaconda_mcp")
    before_count = len(pkg_logger.handlers)
    try:
        _attach_application_otel_handler()
        after_count = len(pkg_logger.handlers)
        assert after_count == before_count + 1
        assert isinstance(pkg_logger.handlers[-1], logging.Handler)
        assert any(isinstance(f, _UserContextLogFilter) for f in pkg_logger.handlers[-1].filters)
    finally:
        # Roll back the handler we just attached so other tests aren't affected.
        if len(pkg_logger.handlers) > before_count:
            pkg_logger.removeHandler(pkg_logger.handlers[-1])
        _attach_application_otel_handler.cache_clear()


def _make_record() -> logging.LogRecord:
    return logging.getLogger("anaconda_mcp").makeRecord("anaconda_mcp", logging.WARNING, "f", 1, "msg", (), None)


def test_user_context_log_filter_stamps_user_id_when_authed():
    """Authed: filter returns True and sets record.__dict__["user.id"] with NO status key."""
    record = _make_record()

    result = _UserContextLogFilter().filter(record)

    assert result is True
    assert record.__dict__["user.id"] == TEST_USER_ID
    assert "user.id.status" not in record.__dict__


def test_user_context_log_filter_omits_user_id_when_anonymous():
    """Anonymous: filter returns True and does NOT set user.id on the record (schema-conforming omission)."""
    import anaconda_mcp.auth

    anaconda_mcp.auth._reset_user_id_cache()
    record = _make_record()

    with patch("anaconda_mcp.auth.get_auth_token", return_value=None):
        result = _UserContextLogFilter().filter(record)

    assert result is True
    assert "user.id" not in record.__dict__
    assert "user.id.status" not in record.__dict__


def test_user_context_log_filter_backstops_on_resolve_user_id_failure():
    """If resolve_user_id raises, filter still returns True and stamps nothing (empty merge)."""
    record = _make_record()

    with patch("anaconda_mcp.telemetry.resolve_user_id", side_effect=RuntimeError("boom")):
        result = _UserContextLogFilter().filter(record)

    assert result is True
    assert "user.id" not in record.__dict__
    assert "user.id.status" not in record.__dict__


def test_user_context_log_filter_asymmetry_no_base_dimensions():
    """LOG half of the accepted signal-type asymmetry (see the comment above
    _base_dimensions() in telemetry.py): _UserContextLogFilter.filter() gains ONLY
    user.id on the record, never any of the 6 _base_dimensions() keys that OTel
    events carry via emit_event(). Authenticated by default via the autouse
    conftest fixture (mirrors test_user_context_log_filter_stamps_user_id_when_authed).
    """
    record = _make_record()
    before_keys = set(record.__dict__.keys())

    result = _UserContextLogFilter().filter(record)

    assert result is True
    assert record.__dict__["user.id"] == TEST_USER_ID
    assert set(record.__dict__.keys()) - before_keys == {"user.id"}
    for key in BASE_DIMENSION_KEYS:
        assert key not in record.__dict__

"""Tests for emit_event() and the application OTel handler attachment."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from anaconda_mcp.telemetry import MetricData, emit_event

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
    assert kwargs["attributes"] == {"x": 1}


def test_emit_event_filters_pii_for_otel_only():
    with (
        patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send,
        patch("anaconda_mcp.telemetry.log_event") as mock_log_event,
    ):
        emit_event(
            "anaconda_mcp_contact_consent",
            {"contact": True, "email": "a@b", "uuid": "1", "aau_client_id": "anon-xyz"},
        )

    mock_send.assert_called_once()
    metric_data = mock_send.call_args[0][0]
    assert metric_data.event_params == {
        "contact": True,
        "email": "a@b",
        "uuid": "1",
        "aau_client_id": "anon-xyz",
    }

    mock_log_event.assert_called_once()
    assert mock_log_event.call_args.kwargs["attributes"] == {"contact": True}


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
    finally:
        # Roll back the handler we just attached so other tests aren't affected.
        if len(pkg_logger.handlers) > before_count:
            pkg_logger.removeHandler(pkg_logger.handlers[-1])
        _attach_application_otel_handler.cache_clear()

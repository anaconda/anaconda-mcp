from unittest import mock

import httpx
import pytest

from anaconda_mcp.telemetry import MetricData, MetricNames, SnakeEyes, _emit_tool_metrics, _otel_user_attrs
from conftest import TEST_USER_ID


@pytest.fixture
def mocked_response():
    return httpx.Response(status_code=200)


@pytest.fixture
def mock_make_request(mocked_response):
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes._make_request") as m:
        m.return_value = mocked_response
        yield m


def test_snake_eyes_send_metric(mock_make_request):
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    was_sent = SnakeEyes()._send(metric, bearer_token="fake-token")
    assert was_sent is True
    assert mock_make_request.call_count == 1
    assert mock_make_request.call_args[0][0] == "api/snake-eyes/record"


def test_snake_eyes_send_anonymous_metric_when_no_auth_token(mock_make_request):
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    was_sent = SnakeEyes()._send(metric)
    assert was_sent is True
    assert mock_make_request.call_count == 1
    assert mock_make_request.call_args[0][0] == "api/snake-eyes/note"


def test_snake_eyes_send_metrics_off_suppresses(mock_make_request):
    with mock.patch("anaconda_mcp.telemetry.settings") as mock_settings:
        mock_settings.send_metrics = False
        metric = MetricData(
            event=MetricNames.START_SERVER.value,
            event_params={},
        )
        was_sent = SnakeEyes()._send(metric)
        assert was_sent is False
        assert mock_make_request.call_count == 0


def test_snake_eyes_send_returns_false_on_non_2xx(mock_make_request):
    mock_make_request.return_value = httpx.Response(status_code=500)
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    was_sent = SnakeEyes()._send(metric)
    assert was_sent is False


def test_snake_eyes_send_handles_timeout():
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes._make_request") as m:
        m.side_effect = httpx.TimeoutException("timed out")
        metric = MetricData(
            event=MetricNames.START_SERVER.value,
            event_params={},
        )
        was_sent = SnakeEyes()._send(metric)
        assert was_sent is False


def test_snake_eyes_send_handles_network_error():
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes._make_request") as m:
        m.side_effect = httpx.NetworkError("connection refused")
        metric = MetricData(
            event=MetricNames.START_SERVER.value,
            event_params={},
        )
        was_sent = SnakeEyes()._send(metric)
        assert was_sent is False


def test_snake_eyes_send_fires_on_background_thread(mock_make_request):
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    with mock.patch("anaconda_mcp.telemetry.threading.Thread") as mock_thread:
        mock_instance = mock.MagicMock()
        mock_thread.return_value = mock_instance

        SnakeEyes().send(metric, bearer_token="fake-token")

        mock_thread.assert_called_once()
        assert mock_thread.call_args[1]["daemon"] is True
        mock_instance.start.assert_called_once()


def test_snake_eyes_send_blocking_calls_directly(mock_make_request):
    metric = MetricData(
        event=MetricNames.START_SERVER.value,
        event_params={},
    )
    SnakeEyes().send(metric, bearer_token="fake-token", blocking=True)

    assert mock_make_request.call_count == 1
    assert mock_make_request.call_args[0][0] == "api/snake-eyes/record"


def test_otel_user_attrs_authenticated():
    assert _otel_user_attrs() == {"user.id": TEST_USER_ID, "user.id.status": "authenticated"}


def test_otel_user_attrs_no_token():
    with mock.patch("anaconda_mcp.auth.get_auth_token", return_value=None):
        assert _otel_user_attrs() == {"user.id": "<anonymous-user>", "user.id.status": "no-local-token"}


def test_otel_user_attrs_backstop_on_exception():
    with mock.patch("anaconda_mcp.telemetry.resolve_user_id", side_effect=RuntimeError("boom")):
        assert _otel_user_attrs() == {"user.id": "<anonymous-user>", "user.id.status": "bad-token"}


def test_emit_tool_metrics_injects_user_id_on_both_metrics():
    with (
        mock.patch("anaconda_mcp.telemetry._otel_count") as mock_count,
        mock.patch("anaconda_mcp.telemetry._otel_histogram") as mock_hist,
    ):
        _emit_tool_metrics("mytool", 12.5, is_error=False)

    assert mock_count.call_count == 1
    assert mock_hist.call_count == 1

    count_attrs = mock_count.call_args.kwargs["attributes"]
    hist_attrs = mock_hist.call_args.kwargs["attributes"]

    for attrs in (count_attrs, hist_attrs):
        assert attrs["user.id"] == TEST_USER_ID
        assert "user.id.status" in attrs
        assert attrs["tool"] == "mytool"


def test_emit_tool_metrics_injects_anonymous_user_id_on_error_when_no_token():
    with (
        mock.patch("anaconda_mcp.auth.get_auth_token", return_value=None),
        mock.patch("anaconda_mcp.telemetry._otel_count") as mock_count,
        mock.patch("anaconda_mcp.telemetry._otel_histogram") as mock_hist,
    ):
        _emit_tool_metrics("mytool", 5.0, is_error=True)

    assert mock_count.call_count == 1
    assert mock_hist.call_count == 1

    count_attrs = mock_count.call_args.kwargs["attributes"]
    hist_attrs = mock_hist.call_args.kwargs["attributes"]

    for attrs in (count_attrs, hist_attrs):
        assert attrs["user.id"] == "<anonymous-user>"
        assert attrs["user.id.status"] == "no-local-token"
        assert attrs["is_error"] is True

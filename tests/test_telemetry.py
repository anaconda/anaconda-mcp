from unittest import mock

import httpx
import pytest

from anaconda_mcp.telemetry import MetricData, MetricNames, SnakeEyes


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

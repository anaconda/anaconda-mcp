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


async def test_snake_eyes_send_metric(mock_get_auth_token, mock_make_request):
    metric = MetricData(
        event=MetricNames.EVENT_CREATE_PROJECT.value,
        event_params={},
    )
    metric_sender = SnakeEyes()
    was_sent = await metric_sender.send(metric)
    assert was_sent is True


async def test_snake_eyes_send_anonymous_metric_when_no_auth_token(mock_make_request):
    with mock.patch("anaconda_mcp.telemetry.get_auth_token", return_value=None):
        metric = MetricData(
            event=MetricNames.EVENT_CREATE_PROJECT.value,
            event_params={},
        )
        metric_sender = SnakeEyes()
        was_sent = await metric_sender.send(metric)
        assert was_sent is True
        assert mock_make_request.call_count == 1
        assert mock_make_request.call_args[0][0] == "api/snake-eyes/note"


async def test_snake_eyes_send_metrics_off_suppresses_anonymous(mock_make_request):
    with mock.patch("anaconda_mcp.telemetry.get_auth_token", return_value=None):
        with mock.patch("anaconda_mcp.telemetry.settings") as mock_settings:
            mock_settings.SEND_METRICS = False
            metric = MetricData(
                event=MetricNames.EVENT_CREATE_PROJECT.value,
                event_params={},
            )
            metric_sender = SnakeEyes()
            was_sent = await metric_sender.send(metric)
            assert was_sent is False
            assert mock_make_request.call_count == 0

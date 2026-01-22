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


@pytest.mark.parametrize("mocked_token", [None])
async def test_snake_eyes_send_metric_should_return_false_if_auth_token_is_none(
    mocked_token, mock_get_auth_token, mock_make_request
):
    metric = MetricData(
        event=MetricNames.EVENT_CREATE_PROJECT.value,
        event_params={},
    )
    metric_sender = SnakeEyes()
    was_sent = await metric_sender.send(metric)
    assert was_sent is False

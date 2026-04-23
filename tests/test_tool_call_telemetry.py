from unittest import mock

import httpx
import pytest
from mcp.server.fastmcp.tools import ToolManager as FastMCPToolManager

from anaconda_mcp.telemetry import MetricData, MetricNames, install_tool_call_tracking

_REAL_CALL_TOOL = FastMCPToolManager.call_tool


@pytest.fixture(autouse=True)
def restore_call_tool():
    FastMCPToolManager.call_tool = _REAL_CALL_TOOL
    yield
    FastMCPToolManager.call_tool = _REAL_CALL_TOOL


@pytest.fixture
def mocked_response():
    return httpx.Response(status_code=200)


@pytest.fixture
def mock_make_request(mocked_response):
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes._make_request") as m:
        m.return_value = mocked_response
        yield m


def test_tool_call_metric_name_exists():
    assert MetricNames.TOOL_CALL.value == "anaconda_mcp_tool_call"


def test_install_tool_call_tracking_replaces_call_tool():
    original = FastMCPToolManager.call_tool
    install_tool_call_tracking(bearer_token_fn=lambda: None)
    assert FastMCPToolManager.call_tool is not original


def test_install_tool_call_tracking_sends_metric_on_success(mock_make_request):
    install_tool_call_tracking(bearer_token_fn=lambda: "fake-token")

    tool_manager = FastMCPToolManager()
    mock_tool = mock.AsyncMock(return_value="result")
    tool_manager._tools["my_tool"] = mock.MagicMock(run=mock_tool)

    with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
        import asyncio

        asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "my_tool", {}))

    mock_send.assert_called_once()
    call_args = mock_send.call_args
    metric: MetricData = call_args[0][0]
    assert metric.event == MetricNames.TOOL_CALL.value
    assert metric.event_params["tool_name"] == "my_tool"
    assert metric.event_params["success"] is True


def test_install_tool_call_tracking_sends_metric_on_failure(mock_make_request):
    install_tool_call_tracking(bearer_token_fn=lambda: "fake-token")

    tool_manager = FastMCPToolManager()
    mock_tool = mock.AsyncMock(side_effect=RuntimeError("boom"))
    tool_manager._tools["failing_tool"] = mock.MagicMock(run=mock_tool)

    with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
        import asyncio

        with pytest.raises(RuntimeError):
            asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "failing_tool", {}))

    mock_send.assert_called_once()
    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event == MetricNames.TOOL_CALL.value
    assert metric.event_params["tool_name"] == "failing_tool"
    assert metric.event_params["success"] is False


def test_install_tool_call_tracking_passes_bearer_token(mock_make_request):
    install_tool_call_tracking(bearer_token_fn=lambda: "my-secret-token")

    tool_manager = FastMCPToolManager()
    tool_manager._tools["a_tool"] = mock.MagicMock(run=mock.AsyncMock(return_value="ok"))

    with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
        import asyncio

        asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "a_tool", {}))

    bearer = mock_send.call_args[1]["bearer_token"]
    assert bearer == "my-secret-token"


def test_install_tool_call_tracking_anonymous_when_no_token(mock_make_request):
    install_tool_call_tracking(bearer_token_fn=lambda: None)

    tool_manager = FastMCPToolManager()
    tool_manager._tools["anon_tool"] = mock.MagicMock(run=mock.AsyncMock(return_value="ok"))

    with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
        import asyncio

        asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "anon_tool", {}))

    bearer = mock_send.call_args[1]["bearer_token"]
    assert bearer is None


def test_install_tool_call_tracking_still_calls_original():
    results = []

    async def fake_original(self, name, arguments, context=None, convert_result=False):
        results.append(name)
        return "original-result"

    with mock.patch.object(FastMCPToolManager, "call_tool", fake_original):
        install_tool_call_tracking(bearer_token_fn=lambda: None)
        tool_manager = FastMCPToolManager()

        with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send"):
            import asyncio

            ret = asyncio.get_event_loop().run_until_complete(
                FastMCPToolManager.call_tool(tool_manager, "some_tool", {})
            )

    assert ret == "original-result"
    assert results == ["some_tool"]


def test_install_tool_call_tracking_suppressed_when_metrics_off(mock_make_request):
    with mock.patch("anaconda_mcp.telemetry.settings") as mock_settings:
        mock_settings.SEND_METRICS = False
        install_tool_call_tracking(bearer_token_fn=lambda: "token")

        tool_manager = FastMCPToolManager()
        tool_manager._tools["quiet_tool"] = mock.MagicMock(run=mock.AsyncMock(return_value="ok"))

        with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
            import asyncio

            asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "quiet_tool", {}))

        mock_send.assert_not_called()


def test_install_tool_call_tracking_fires_on_background_thread(mock_make_request):
    install_tool_call_tracking(bearer_token_fn=lambda: "token")

    tool_manager = FastMCPToolManager()
    tool_manager._tools["bg_tool"] = mock.MagicMock(run=mock.AsyncMock(return_value="ok"))

    with mock.patch("anaconda_mcp.telemetry.threading.Thread") as mock_thread:
        mock_instance = mock.MagicMock()
        mock_thread.return_value = mock_instance

        import asyncio

        asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "bg_tool", {}))

        mock_thread.assert_called_once()
        assert mock_thread.call_args[1]["daemon"] is True
        mock_instance.start.assert_called_once()


def test_install_tool_call_tracking_records_duration(mock_make_request):
    install_tool_call_tracking(bearer_token_fn=lambda: None)

    tool_manager = FastMCPToolManager()
    tool_manager._tools["slow_tool"] = mock.MagicMock(run=mock.AsyncMock(return_value="ok"))

    with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
        import asyncio

        asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "slow_tool", {}))

    metric: MetricData = mock_send.call_args[0][0]
    assert "duration_ms" in metric.event_params
    assert isinstance(metric.event_params["duration_ms"], int)
    assert metric.event_params["duration_ms"] >= 0

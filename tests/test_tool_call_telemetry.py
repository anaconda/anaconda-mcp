import asyncio
from unittest import mock

import pytest
from mcp.server.fastmcp.tools import ToolManager as FastMCPToolManager

from anaconda_mcp.telemetry import MetricData, MetricNames, _get_client_info, patch_tool_call_tracking

_REAL_CALL_TOOL = FastMCPToolManager.call_tool


@pytest.fixture(autouse=True)
def restore_call_tool():
    """Restore the real call_tool after each test so monkey-patching doesn't leak between tests."""
    FastMCPToolManager.call_tool = _REAL_CALL_TOOL
    yield
    FastMCPToolManager.call_tool = _REAL_CALL_TOOL


@pytest.fixture
def mock_send():
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as m:
        yield m


def _make_tool_manager(tool_name: str, *, side_effect=None, return_value="result"):
    tool_manager = FastMCPToolManager()
    run = mock.AsyncMock(side_effect=side_effect) if side_effect else mock.AsyncMock(return_value=return_value)
    tool_manager._tools[tool_name] = mock.MagicMock(run=run)
    return tool_manager


def _make_context(name="claude-desktop", version="1.2.3"):
    client_info = mock.MagicMock()
    client_info.name = name
    client_info.version = version
    client_params = mock.MagicMock()
    client_params.clientInfo = client_info
    session = mock.MagicMock()
    session.client_params = client_params
    ctx = mock.MagicMock()
    ctx.session = session
    return ctx


def test_patch_tool_call_tracking_replaces_call_tool():
    original = FastMCPToolManager.call_tool
    patch_tool_call_tracking(bearer_token_fn=lambda: None)
    assert FastMCPToolManager.call_tool is not original


def test_patch_tool_call_tracking_sends_metric_on_success(mock_send):
    patch_tool_call_tracking(bearer_token_fn=lambda: "fake-token")
    tool_manager = _make_tool_manager("my_tool")

    asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "my_tool", {"arg1": "val1"}))

    mock_send.assert_called_once()
    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event == MetricNames.TOOL_CALL.value
    assert metric.event_params["tool_name"] == "my_tool"
    assert metric.event_params["tool_inputs"] == {"arg1": "val1"}
    assert metric.event_params["is_error"] is False
    assert metric.event_params["error_description"] == ""
    assert metric.event_params["client_name"] == "unknown"
    assert metric.event_params["client_version"] == "unknown"
    assert isinstance(metric.event_params["duration_ms"], float)


def test_patch_tool_call_tracking_sends_metric_on_failure(mock_send):
    patch_tool_call_tracking(bearer_token_fn=lambda: "fake-token")
    tool_manager = _make_tool_manager("failing_tool", side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "failing_tool", {}))

    mock_send.assert_called_once()
    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event_params["tool_name"] == "failing_tool"
    assert metric.event_params["is_error"] is True
    assert metric.event_params["error_description"] == "RuntimeError: boom"


def test_patch_tool_call_tracking_passes_bearer_token(mock_send):
    patch_tool_call_tracking(bearer_token_fn=lambda: "my-secret-token")
    tool_manager = _make_tool_manager("a_tool")

    asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "a_tool", {}))

    assert mock_send.call_args[1]["bearer_token"] == "my-secret-token"


def test_patch_tool_call_tracking_anonymous_when_no_token(mock_send):
    patch_tool_call_tracking(bearer_token_fn=lambda: None)
    tool_manager = _make_tool_manager("anon_tool")

    asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "anon_tool", {}))

    assert mock_send.call_args[1]["bearer_token"] is None


def test_patch_tool_call_tracking_still_calls_original():
    results = []

    async def fake_original(self, name, arguments, context=None, convert_result=False):
        results.append(name)
        return "original-result"

    with mock.patch.object(FastMCPToolManager, "call_tool", fake_original):
        patch_tool_call_tracking(bearer_token_fn=lambda: None)
        tool_manager = FastMCPToolManager()

        with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send"):
            ret = asyncio.get_event_loop().run_until_complete(
                FastMCPToolManager.call_tool(tool_manager, "some_tool", {})
            )

    assert ret == "original-result"
    assert results == ["some_tool"]


def test_patch_tool_call_tracking_suppressed_when_metrics_off():
    with mock.patch("anaconda_mcp.telemetry.settings") as mock_settings:
        mock_settings.SEND_METRICS = False
        patch_tool_call_tracking(bearer_token_fn=lambda: "token")
        tool_manager = _make_tool_manager("quiet_tool")

        with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
            asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "quiet_tool", {}))

        mock_send.assert_not_called()


def test_patch_tool_call_tracking_fires_on_background_thread():
    patch_tool_call_tracking(bearer_token_fn=lambda: "token")
    tool_manager = _make_tool_manager("bg_tool")

    with mock.patch("anaconda_mcp.telemetry.threading.Thread") as mock_thread:
        mock_instance = mock.MagicMock()
        mock_thread.return_value = mock_instance

        asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "bg_tool", {}))

        mock_thread.assert_called_once()
        assert mock_thread.call_args[1]["daemon"] is True
        mock_instance.start.assert_called_once()


def test_patch_tool_call_tracking_includes_client_info_in_metric(mock_send):
    patch_tool_call_tracking(bearer_token_fn=lambda: None)
    tool_manager = _make_tool_manager("my_tool")
    ctx = _make_context(name="cursor", version="0.48.0")

    asyncio.get_event_loop().run_until_complete(FastMCPToolManager.call_tool(tool_manager, "my_tool", {}, context=ctx))

    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event_params["client_name"] == "cursor"
    assert metric.event_params["client_version"] == "0.48.0"


@pytest.mark.parametrize(
    "ctx,expected",
    [
        (_make_context(name="claude-desktop", version="1.2.3"), ("claude-desktop", "1.2.3")),
        (None, ("unknown", "unknown")),
        (object(), ("unknown", "unknown")),
    ],
)
def test_get_client_info(ctx, expected):
    assert _get_client_info(ctx) == expected


def test_get_client_info_returns_unknown_when_client_params_is_none():
    ctx = mock.MagicMock()
    ctx.session.client_params = None
    assert _get_client_info(ctx) == ("unknown", "unknown")

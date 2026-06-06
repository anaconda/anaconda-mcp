from unittest import mock

import pytest
from mcp.server.fastmcp.tools import ToolManager as FastMCPToolManager

from anaconda_mcp.telemetry import (
    MetricData,
    MetricNames,
    _get_client_info,
    make_tracked_call_tool,
    patch_tool_call_tracking,
)


@pytest.fixture
def mock_send():
    with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as m:
        yield m


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


@pytest.mark.asyncio
async def test_tracked_sends_metric_on_success(mock_send):
    original = mock.AsyncMock(return_value="result")
    tracked = make_tracked_call_tool(original)

    result = await tracked(mock.MagicMock(), "my_tool", {"arg1": "val1"})

    assert result == "result"
    mock_send.assert_called_once()
    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event == MetricNames.TOOL_COMPLETED.value
    assert metric.event_params["tool_name"] == "my_tool"
    assert metric.event_params["is_error"] is False
    assert metric.event_params["error_description"] == ""
    assert metric.event_params["client_name"] == "unknown"
    assert metric.event_params["client_version"] == "unknown"
    assert isinstance(metric.event_params["duration_ms"], float)


@pytest.mark.asyncio
async def test_tracked_sends_metric_on_failure(mock_send):
    original = mock.AsyncMock(side_effect=RuntimeError("boom"))
    tracked = make_tracked_call_tool(original)

    with pytest.raises(RuntimeError):
        await tracked(mock.MagicMock(), "failing_tool", {})

    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event_params["tool_name"] == "failing_tool"
    assert metric.event_params["is_error"] is True
    assert metric.event_params["error_description"] == "RuntimeError: boom"


@pytest.mark.asyncio
async def test_tracked_passes_bearer_token(mock_send, monkeypatch):
    monkeypatch.setattr("anaconda_mcp.telemetry.get_auth_token", lambda: "my-secret-token")
    original = mock.AsyncMock(return_value="ok")
    tracked = make_tracked_call_tool(original)

    await tracked(mock.MagicMock(), "a_tool", {})

    assert mock_send.call_args[1]["bearer_token"] == "my-secret-token"


@pytest.mark.asyncio
async def test_tracked_anonymous_when_no_token(mock_send, monkeypatch):
    monkeypatch.setattr("anaconda_mcp.telemetry.get_auth_token", lambda: None)
    original = mock.AsyncMock(return_value="ok")
    tracked = make_tracked_call_tool(original)

    await tracked(mock.MagicMock(), "anon_tool", {})

    assert mock_send.call_args[1]["bearer_token"] is None


@pytest.mark.asyncio
async def test_tracked_calls_original():
    original = mock.AsyncMock(return_value="original-result")
    tracked = make_tracked_call_tool(original)
    fake_self = mock.MagicMock()

    with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send"):
        result = await tracked(fake_self, "some_tool", {"x": 1})

    assert result == "original-result"
    original.assert_awaited_once_with(fake_self, "some_tool", {"x": 1}, context=None, convert_result=False)


@pytest.mark.asyncio
async def test_tracked_suppressed_when_metrics_off():
    original = mock.AsyncMock(return_value="ok")
    tracked = make_tracked_call_tool(original)

    with mock.patch("anaconda_mcp.telemetry.settings") as mock_settings:
        mock_settings.send_metrics = False
        with mock.patch("anaconda_mcp.telemetry.SnakeEyes.send") as mock_send:
            await tracked(mock.MagicMock(), "quiet_tool", {})

    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_tracked_arguments_none_becomes_empty_dict(mock_send):
    original = mock.AsyncMock(return_value="ok")
    tracked = make_tracked_call_tool(original)

    await tracked(mock.MagicMock(), "my_tool", None)

    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event_params["tool_name"] == "my_tool"


@pytest.mark.asyncio
async def test_tracked_includes_client_info(mock_send):
    original = mock.AsyncMock(return_value="ok")
    tracked = make_tracked_call_tool(original)
    ctx = _make_context(name="cursor", version="0.48.0")

    await tracked(mock.MagicMock(), "my_tool", {}, context=ctx)

    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event_params["client_name"] == "cursor"
    assert metric.event_params["client_version"] == "0.48.0"


def test_patch_replaces_call_tool():
    with mock.patch.object(FastMCPToolManager, "call_tool", FastMCPToolManager.call_tool):
        original = FastMCPToolManager.call_tool
        patch_tool_call_tracking()
        assert FastMCPToolManager.call_tool is not original


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


@pytest.mark.asyncio
async def test_tracked_accumulates_tool_call_history(mock_send):
    original = mock.AsyncMock(return_value="result")
    tracked = make_tracked_call_tool(original)
    fake_self = mock.MagicMock()

    await tracked(fake_self, "tool_a", {})
    await tracked(fake_self, "tool_b", {})
    await tracked(fake_self, "tool_c", {})

    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event_params["tool_call_history"] == "tool_a,tool_b,tool_c"


@pytest.mark.asyncio
async def test_tracked_tool_call_history_evicts_oldest(mock_send):
    original = mock.AsyncMock(return_value="result")
    tracked = make_tracked_call_tool(original, max_tool_call_history=2)
    fake_self = mock.MagicMock()

    await tracked(fake_self, "first", {})
    await tracked(fake_self, "second", {})
    await tracked(fake_self, "third", {})

    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event_params["tool_call_history"] == "second,third"


@pytest.mark.asyncio
async def test_tracked_includes_aau_client_id_when_provided(mock_send):
    original = mock.AsyncMock(return_value="ok")
    tracked = make_tracked_call_tool(original, aau_client_id="test-anon-id")

    await tracked(mock.MagicMock(), "my_tool", {})

    metric: MetricData = mock_send.call_args[0][0]
    assert metric.event_params["aau_client_id"] == "test-anon-id"


@pytest.mark.asyncio
async def test_tracked_omits_aau_client_id_when_none(mock_send):
    original = mock.AsyncMock(return_value="ok")
    tracked = make_tracked_call_tool(original, aau_client_id=None)

    await tracked(mock.MagicMock(), "my_tool", {})

    metric: MetricData = mock_send.call_args[0][0]
    assert "aau_client_id" not in metric.event_params

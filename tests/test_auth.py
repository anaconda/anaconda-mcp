import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from unittest import mock
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from anaconda_mcp import auth
from anaconda_mcp.cli import cli
from anaconda_mcp.telemetry import MetricData, MetricNames

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_get_auth_token(mocked_token):
    with mock.patch("anaconda_mcp.auth.get_auth_token") as m:
        m.return_value = mocked_token
        yield m


@pytest.fixture
def mock_anaconda_login():
    with mock.patch("anaconda_mcp.auth.anaconda_login") as m:
        yield m


@pytest.fixture
def mocked_init_telemetry():
    return MagicMock()


@pytest.fixture
def mock_start_login():
    with mock.patch("anaconda_mcp.cli.start_login") as m:
        yield m


@pytest.fixture
def mock_serve_command():
    with mock.patch("anaconda_mcp.cli._serve") as m:
        m.return_value = 0
        yield m


@pytest.fixture
def mock_base_client():
    with mock.patch("anaconda_mcp.auth.BaseClient") as m:
        m.return_value.account = {"user": {"created_at": "2020-01-01T00:00:00Z"}}
        yield m


@pytest.fixture
def mock_snake_eyes():
    with mock.patch("anaconda_mcp.auth.SnakeEyes") as m:
        yield m


async def test_auth_flow_should_be_initialized_only_once(
    mocked_init_telemetry, mock_get_auth_token, mock_anaconda_login, mock_base_client, mock_snake_eyes
):
    # Given
    auth._initialized = False
    assert auth._initialized is False
    assert mock_get_auth_token.call_count == 0
    assert mocked_init_telemetry.call_count == 0

    # When 1
    auth.start_login(init_telemetry=mocked_init_telemetry)

    # Then 1
    assert auth._initialized is True
    assert mock_get_auth_token.call_count == 1
    assert mocked_init_telemetry.call_count == 1

    # When 2 - going for a second call, this should not start another telemetry thread
    auth.start_login(init_telemetry=mocked_init_telemetry)

    # Then 2
    assert auth._initialized is True
    assert mock_get_auth_token.call_count == 2
    assert mocked_init_telemetry.call_count == 1


async def test_serve_should_start_auth_flow(mock_start_login, mock_serve_command):
    # Given
    runner = CliRunner()
    with mock.patch("anaconda_mcp.cli.Path.exists", return_value=True):
        result = runner.invoke(cli, ["serve"])  # ← Invoke through the CLI group

    # Then
    assert result.exit_code == 0
    assert mock_start_login.call_count == 1
    assert mock_serve_command.call_count == 1


async def test_serve_transport_flag_is_passed_to_serve_command(mock_start_login, mock_serve_command):
    # Given
    runner = CliRunner()
    with mock.patch("anaconda_mcp.cli.Path.exists", return_value=True):
        result = runner.invoke(cli, ["serve", "--transport", "streamable-http"])

    # Then
    assert result.exit_code == 0
    ns = mock_serve_command.call_args[0][0]
    assert ns.transport == "streamable-http"


async def test_serve_transport_flag_defaults_to_none(mock_start_login, mock_serve_command):
    # Given
    runner = CliRunner()
    with mock.patch("anaconda_mcp.cli.Path.exists", return_value=True):
        result = runner.invoke(cli, ["serve"])

    # Then
    assert result.exit_code == 0
    ns = mock_serve_command.call_args[0][0]
    assert ns.transport is None


async def test_serve_port_flag_is_passed_to_serve_command(mock_start_login, mock_serve_command):
    # Given
    runner = CliRunner()
    with mock.patch("anaconda_mcp.cli.Path.exists", return_value=True):
        result = runner.invoke(cli, ["serve", "--port", "9000"])

    # Then
    assert result.exit_code == 0
    ns = mock_serve_command.call_args[0][0]
    assert ns.port == 9000


async def test_serve_port_omitted_leaves_config_in_control(mock_start_login, mock_serve_command):
    # Given
    runner = CliRunner()
    with mock.patch("anaconda_mcp.cli.Path.exists", return_value=True):
        result = runner.invoke(cli, ["serve"])

    # Then — port not in ns, so mcp-compose falls back to toml
    assert result.exit_code == 0
    ns = mock_serve_command.call_args[0][0]
    assert not hasattr(ns, "port")


async def test_start_login_times_out_without_token(mocked_init_telemetry, mock_get_auth_token, mock_anaconda_login):
    # Given - no token available
    auth._initialized = False
    mock_get_auth_token.return_value = None

    # When - start login with very short timeout
    auth.start_login(init_telemetry=mocked_init_telemetry, poll_interval=0.1, max_wait_sec=0.3)

    # Give threads time to timeout
    await asyncio.sleep(0.5)

    # Then - telemetry should NOT be initialized due to timeout
    assert mocked_init_telemetry.call_count == 0
    assert auth._initialized is False


async def test_start_login_handles_login_exception(
    mocked_init_telemetry, mock_get_auth_token, mock_anaconda_login, caplog
):
    # Given - no token, login will fail
    auth._initialized = False
    mock_get_auth_token.return_value = None
    mock_anaconda_login.side_effect = Exception("Login service unavailable")

    # When - start login
    with caplog.at_level(logging.ERROR):
        auth.start_login(init_telemetry=mocked_init_telemetry, poll_interval=0.1, max_wait_sec=0.3)

        # Give threads time to execute
        await asyncio.sleep(0.5)

    # Then - exception should be logged, but process continues
    assert "Login failed" in caplog.text
    assert mocked_init_telemetry.call_count == 0


async def test_init_once_thread_safety(mocked_token, mock_get_auth_token, mock_base_client, mock_snake_eyes):
    # Given
    auth._initialized = False
    mock_get_auth_token.return_value = mocked_token
    call_count = 0

    def counting_telemetry(token):
        nonlocal call_count
        call_count += 1
        time.sleep(0.01)

    # When - call start_login concurrently from multiple threads
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=lambda: auth.start_login(init_telemetry=counting_telemetry))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Then - telemetry should only be initialized once despite 10 concurrent calls
    assert call_count == 1
    assert auth._initialized is True


async def test_is_new_user_true_for_recent_account(mocked_init_telemetry, mock_get_auth_token):
    # Given - account created less than 1 day ago
    auth._initialized = False
    recent_timestamp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    with mock.patch("anaconda_mcp.auth.BaseClient") as mock_base_client:
        mock_client_instance = MagicMock()
        mock_client_instance.account = {"user": {"created_at": recent_timestamp}}
        mock_base_client.return_value = mock_client_instance

        with mock.patch("anaconda_mcp.auth.SnakeEyes") as mock_snake_eyes:
            mock_snake_eyes_instance = MagicMock()
            mock_snake_eyes.return_value = mock_snake_eyes_instance

            # When
            auth.start_login(init_telemetry=mocked_init_telemetry)

            # Then - SnakeEyes().send() should be called with is_new_user=True
            assert mock_snake_eyes_instance.send.call_count == 1
            call_args = mock_snake_eyes_instance.send.call_args
            metric_data = call_args[0][0]
            assert isinstance(metric_data, MetricData)
            assert metric_data.event == MetricNames.LOGIN_COMPLETED.value
            assert metric_data.event_params.get("is_new_user") is True


async def test_is_new_user_false_for_old_account(mocked_init_telemetry, mock_get_auth_token):
    # Given - account created 30 days ago
    auth._initialized = False
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    with mock.patch("anaconda_mcp.auth.BaseClient") as mock_base_client:
        mock_client_instance = MagicMock()
        mock_client_instance.account = {"user": {"created_at": old_timestamp}}
        mock_base_client.return_value = mock_client_instance

        with mock.patch("anaconda_mcp.auth.SnakeEyes") as mock_snake_eyes:
            mock_snake_eyes_instance = MagicMock()
            mock_snake_eyes.return_value = mock_snake_eyes_instance

            # When
            auth.start_login(init_telemetry=mocked_init_telemetry)

            # Then - SnakeEyes().send() should be called with is_new_user=False
            assert mock_snake_eyes_instance.send.call_count == 1
            call_args = mock_snake_eyes_instance.send.call_args
            metric_data = call_args[0][0]
            assert isinstance(metric_data, MetricData)
            assert metric_data.event == MetricNames.LOGIN_COMPLETED.value
            assert metric_data.event_params.get("is_new_user") is False


async def test_is_new_user_omitted_on_api_failure(mocked_init_telemetry, mock_get_auth_token):
    # Given - BaseClient raises an exception
    auth._initialized = False

    with mock.patch("anaconda_mcp.auth.BaseClient") as mock_base_client:
        mock_base_client.side_effect = Exception("API error")

        with mock.patch("anaconda_mcp.auth.SnakeEyes") as mock_snake_eyes:
            mock_snake_eyes_instance = MagicMock()
            mock_snake_eyes.return_value = mock_snake_eyes_instance

            # When
            auth.start_login(init_telemetry=mocked_init_telemetry)

            # Then - SnakeEyes().send() should be called but without is_new_user in event_params
            assert mock_snake_eyes_instance.send.call_count == 1
            call_args = mock_snake_eyes_instance.send.call_args
            metric_data = call_args[0][0]
            assert isinstance(metric_data, MetricData)
            assert metric_data.event == MetricNames.LOGIN_COMPLETED.value
            assert "is_new_user" not in metric_data.event_params

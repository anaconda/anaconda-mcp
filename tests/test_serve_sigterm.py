"""Tests for SIGTERM handling in the `serve` CLI command."""

import logging
import os
import signal
import time
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from anaconda_mcp.cli import cli


@pytest.fixture(autouse=True)
def reset_signal_handler():
    """Restore the original SIGTERM handler after every test."""
    original = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, original)


@pytest.fixture
def mock_start_login():
    with patch("anaconda_mcp.cli.start_login") as m:
        yield m


@pytest.fixture
def mock_serve_command():
    with patch("anaconda_mcp.cli._serve") as m:
        m.return_value = 0
        yield m


@pytest.fixture
def mock_render_config():
    with patch("anaconda_mcp.cli._render_config_template") as m:
        m.return_value = "/fake/rendered/mcp_compose.toml"
        yield m


@pytest.fixture
def mock_path_exists():
    with patch("anaconda_mcp.cli.Path.exists", return_value=True):
        yield


@pytest.fixture
def mock_sleep():
    with patch("anaconda_mcp.cli.time.sleep") as m:
        yield m


def invoke_serve(extra_args=None, env=None):
    runner = CliRunner()
    args = ["serve"] + (extra_args or [])
    with (
        patch("anaconda_mcp.cli.Path.exists", return_value=True),
        patch("anaconda_mcp.cli._render_config_template", return_value="/fake/mcp.toml"),
        patch("anaconda_mcp.cli.time.sleep"),
        patch("anaconda_mcp.cli.start_login"),
        patch("anaconda_mcp.cli._serve", return_value=0),
    ):
        return runner.invoke(cli, args, env=env, catch_exceptions=False)


def test_sigterm_handler_is_registered(
    mock_path_exists, mock_render_config, mock_sleep, mock_start_login, mock_serve_command
):
    """signal.signal(SIGTERM, ...) must be called as the very first thing in serve()."""
    registered_handlers = []

    original_signal = signal.signal

    def capturing_signal(signum, handler):
        registered_handlers.append((signum, handler))
        return original_signal(signum, handler)

    runner = CliRunner()
    with patch("anaconda_mcp.cli.signal.signal", side_effect=capturing_signal):
        runner.invoke(cli, ["serve"], catch_exceptions=False)

    sigterm_registrations = [h for sig, h in registered_handlers if sig == signal.SIGTERM]
    assert sigterm_registrations, "signal.signal(SIGTERM, ...) was never called"


def test_sigterm_handler_registered_before_sleep(
    mock_path_exists, mock_render_config, mock_start_login, mock_serve_command
):
    """The SIGTERM handler must be registered before time.sleep() is called."""
    call_order = []

    original_signal = signal.signal

    def capturing_signal(signum, handler):
        call_order.append("signal")
        return original_signal(signum, handler)

    def capturing_sleep(seconds):
        call_order.append("sleep")

    runner = CliRunner()
    with (
        patch("anaconda_mcp.cli.signal.signal", side_effect=capturing_signal),
        patch("anaconda_mcp.cli.time.sleep", side_effect=capturing_sleep),
    ):
        runner.invoke(cli, ["serve"], catch_exceptions=False)

    assert "signal" in call_order, "signal.signal was never called"
    assert "sleep" in call_order, "time.sleep was never called"
    assert call_order.index("signal") < call_order.index("sleep"), (
        "SIGTERM handler must be registered before time.sleep()"
    )


def test_sigterm_handler_calls_sys_exit_0():
    """Calling the SIGTERM handler directly must raise SystemExit(0)."""
    captured_handler = None
    original_signal = signal.signal

    def capturing_signal(signum, handler):
        nonlocal captured_handler
        if signum == signal.SIGTERM:
            captured_handler = handler
        return original_signal(signum, handler)

    runner = CliRunner()
    with (
        patch("anaconda_mcp.cli.signal.signal", side_effect=capturing_signal),
        patch("anaconda_mcp.cli.Path.exists", return_value=True),
        patch("anaconda_mcp.cli._render_config_template", return_value="/fake/mcp.toml"),
        patch("anaconda_mcp.cli.time.sleep"),
        patch("anaconda_mcp.cli.start_login"),
        patch("anaconda_mcp.cli._serve", return_value=0),
    ):
        runner.invoke(cli, ["serve"])

    assert captured_handler is not None, "SIGTERM handler was not registered"

    with pytest.raises(SystemExit) as exc_info:
        captured_handler(signal.SIGTERM, None)

    assert exc_info.value.code == 0


def test_sigterm_during_sleep_exits_cleanly():
    """Sending SIGTERM to the process during the sleep phase must cause a clean exit."""
    import threading

    exit_code = None
    exception_raised = None

    def run_serve():
        nonlocal exit_code, exception_raised
        runner = CliRunner()
        with (
            patch("anaconda_mcp.cli.Path.exists", return_value=True),
            patch("anaconda_mcp.cli._render_config_template", return_value="/fake/mcp.toml"),
            patch("anaconda_mcp.cli.start_login"),
            patch("anaconda_mcp.cli._serve", return_value=0),
        ):
            # Use a real short sleep so SIGTERM can interrupt it
            result = runner.invoke(cli, ["serve", "--delay", "30"], catch_exceptions=True)
            exit_code = result.exit_code

    thread = threading.Thread(target=run_serve, daemon=True)
    thread.start()

    # Give the thread a moment to reach time.sleep()
    time.sleep(0.2)

    # Send SIGTERM to ourselves
    os.kill(os.getpid(), signal.SIGTERM)

    thread.join(timeout=3)
    assert not thread.is_alive(), "serve did not exit after SIGTERM"


def test_sigterm_handler_logs_shutdown_message(caplog):
    """The SIGTERM handler must log a message at INFO level."""
    captured_handler = None
    original_signal = signal.signal

    def capturing_signal(signum, handler):
        nonlocal captured_handler
        if signum == signal.SIGTERM:
            captured_handler = handler
        return original_signal(signum, handler)

    runner = CliRunner()
    with (
        patch("anaconda_mcp.cli.signal.signal", side_effect=capturing_signal),
        patch("anaconda_mcp.cli.Path.exists", return_value=True),
        patch("anaconda_mcp.cli._render_config_template", return_value="/fake/mcp.toml"),
        patch("anaconda_mcp.cli.time.sleep"),
        patch("anaconda_mcp.cli.start_login"),
        patch("anaconda_mcp.cli._serve", return_value=0),
    ):
        runner.invoke(cli, ["serve"])

    assert captured_handler is not None

    with caplog.at_level(logging.INFO, logger="anaconda_mcp.cli"):
        with pytest.raises(SystemExit):
            captured_handler(signal.SIGTERM, None)

    assert any("SIGTERM" in record.message or "shutting down" in record.message.lower() for record in caplog.records), (
        f"Expected a SIGTERM log message, got: {[r.message for r in caplog.records]}"
    )


def test_serve_normal_flow_completes_successfully(
    mock_path_exists, mock_render_config, mock_sleep, mock_start_login, mock_serve_command
):
    """Without a SIGTERM, serve should run to completion and exit 0."""
    runner = CliRunner()
    result = runner.invoke(cli, ["serve"], catch_exceptions=False)
    assert result.exit_code == 0
    mock_start_login.assert_called_once()
    mock_serve_command.assert_called_once()


def test_serve_calls_start_login_after_sleep(
    mock_path_exists, mock_render_config, mock_start_login, mock_serve_command
):
    """start_login must be called after the delay sleep, not before."""
    call_order = []

    mock_start_login.side_effect = lambda *a, **kw: call_order.append("start_login")

    def capturing_sleep(seconds):
        call_order.append("sleep")

    runner = CliRunner()
    with patch("anaconda_mcp.cli.time.sleep", side_effect=capturing_sleep):
        runner.invoke(cli, ["serve"], catch_exceptions=False)

    assert call_order.index("sleep") < call_order.index("start_login"), (
        "start_login should be called after time.sleep()"
    )


def test_serve_exception_from_mcp_compose_exits_with_1(
    mock_path_exists, mock_render_config, mock_sleep, mock_start_login
):
    """If _serve() raises an exception, serve should catch it and exit with code 1."""
    runner = CliRunner()
    with patch("anaconda_mcp.cli._serve", side_effect=RuntimeError("mcp compose exploded")):
        result = runner.invoke(cli, ["serve"], catch_exceptions=True)
    assert result.exit_code == 1


def test_serve_missing_config_exits_with_1(mock_sleep):
    """If no config is provided and the default path doesn't exist, exit with 1."""
    runner = CliRunner()
    with patch("anaconda_mcp.cli.Path.exists", return_value=False):
        result = runner.invoke(cli, ["serve"])
    assert result.exit_code == 1
    assert "No configuration file found" in result.output


def test_serve_delay_option_is_respected(mock_path_exists, mock_render_config, mock_start_login, mock_serve_command):
    """The --delay flag must be passed directly to time.sleep."""
    runner = CliRunner()
    with patch("anaconda_mcp.cli.time.sleep") as mock_sleep:
        runner.invoke(cli, ["serve", "--delay", "11"], catch_exceptions=False)
    mock_sleep.assert_called_once_with(11)

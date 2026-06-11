"""Tests for SIGTERM handling in the `serve` CLI command."""

import signal
import subprocess
import sys
import threading
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
def mock_require_auth():
    yield


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
        patch("anaconda_mcp.cli.get_auth_token", return_value=None),
        patch("anaconda_mcp.cli._serve", return_value=0),
    ):
        return runner.invoke(cli, args, env=env, catch_exceptions=False)


def test_serve_installs_signal_handlers_via_long_running(
    mock_path_exists, mock_render_config, mock_sleep, mock_require_auth, mock_serve_command
):
    """Invoking serve() installs SIGTERM and SIGINT handlers via cli-base @long_running."""
    import anaconda_cli_base.lifecycle as lifecycle

    registered = []
    original_signal = lifecycle.signal.signal

    def capturing_signal(signum, handler):
        registered.append(signum)
        return original_signal(signum, handler)

    with patch("anaconda_cli_base.lifecycle.signal.signal", side_effect=capturing_signal):
        CliRunner().invoke(cli, ["serve"], catch_exceptions=False)

    assert signal.SIGTERM in registered, "@long_running did not register a SIGTERM handler"
    assert signal.SIGINT in registered, "@long_running did not register a SIGINT handler"


def test_serve_installs_handlers_before_sleep(
    mock_path_exists, mock_render_config, mock_require_auth, mock_serve_command
):
    """@long_running must install signal handlers before serve() reaches time.sleep()."""
    import anaconda_cli_base.lifecycle as lifecycle

    call_order = []
    original_signal = lifecycle.signal.signal

    def capturing_signal(signum, handler):
        call_order.append("signal")
        return original_signal(signum, handler)

    def capturing_sleep(seconds):
        call_order.append("sleep")

    with (
        patch("anaconda_cli_base.lifecycle.signal.signal", side_effect=capturing_signal),
        patch("anaconda_mcp.cli.time.sleep", side_effect=capturing_sleep),
    ):
        CliRunner().invoke(cli, ["serve"], catch_exceptions=False)

    assert "signal" in call_order, "signal handlers were never installed"
    assert "sleep" in call_order, "time.sleep was never called"
    assert call_order.index("signal") < call_order.index("sleep"), (
        "signal handlers must be installed before time.sleep()"
    )


def test_serve_sigterm_handler_delegates_to_trigger_shutdown(
    mock_path_exists, mock_render_config, mock_sleep, mock_require_auth, mock_serve_command
):
    """The installed SIGTERM handler routes to cli-base trigger_shutdown (no bespoke sys.exit)."""
    import anaconda_cli_base.lifecycle as lifecycle

    captured = {}
    original_signal = lifecycle.signal.signal

    def capturing_signal(signum, handler):
        if signum == signal.SIGTERM:
            captured["handler"] = handler
        return original_signal(signum, handler)

    with patch("anaconda_cli_base.lifecycle.signal.signal", side_effect=capturing_signal):
        CliRunner().invoke(cli, ["serve"], catch_exceptions=False)

    assert "handler" in captured, "SIGTERM handler was not installed"

    with patch("anaconda_cli_base.lifecycle.trigger_shutdown") as mock_trigger:
        captured["handler"](signal.SIGTERM, None)

    mock_trigger.assert_called_once_with(signal.SIGTERM)


_REAL_SIGNAL_CHILD = """
import os
import sys
import threading

os.environ["ANACONDA_TELEMETRY_ENABLED"] = "false"
os.environ.pop("OTEL_SDK_DISABLED", None)

import anaconda_cli_base.lifecycle as lc
import anaconda_mcp._shutdown as sd


@lc.long_running
def run():
    done = threading.Event()
    lc.register_shutdown_hook(done.set)
    sd.install_shutdown_handlers()
    print("READY", flush=True)
    done.wait()


run()
sys.exit(0)
"""


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGINT])
def test_real_signal_triggers_bounded_shutdown_without_hanging(signum):
    """A real OS SIGTERM/SIGINT delivered to a serve-like process must route through
    cli-base trigger_shutdown, run shutdown hooks to unblock the loop, and exit
    promptly. The watchdog guarantees exit within ~10s, so a 15s wait catches a hang."""
    proc = subprocess.Popen(
        [sys.executable, "-c", _REAL_SIGNAL_CHILD],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    ready = []
    reader = threading.Thread(target=lambda: ready.append(proc.stdout.readline()), daemon=True)
    reader.start()
    reader.join(timeout=10)

    if not ready or ready[0].strip() != "READY":
        proc.kill()
        out = proc.communicate()[0]
        pytest.fail(f"child never reached READY (got {ready!r}); output:\n{out}")

    proc.send_signal(signum)
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail(
            f"process hung after {signal.Signals(signum).name}; "
            "trigger_shutdown/watchdog should have forced exit within ~10s"
        )

    assert proc.returncode in (0, 128 + signum), (
        f"unexpected exit code {proc.returncode} after {signal.Signals(signum).name}"
    )


def test_serve_normal_flow_completes_successfully(
    mock_path_exists, mock_render_config, mock_sleep, mock_require_auth, mock_serve_command
):
    """Without a SIGTERM, serve should run to completion and exit 0."""
    runner = CliRunner()
    result = runner.invoke(cli, ["serve"], catch_exceptions=False)
    assert result.exit_code == 0
    mock_serve_command.assert_called_once()


def test_serve_exception_from_mcp_compose_exits_with_1(
    mock_path_exists, mock_render_config, mock_sleep, mock_require_auth
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


def test_serve_delay_option_is_respected(mock_path_exists, mock_render_config, mock_require_auth, mock_serve_command):
    """The --delay flag must be passed directly to time.sleep."""
    runner = CliRunner()
    with patch("anaconda_mcp.cli.time.sleep") as mock_sleep:
        runner.invoke(cli, ["serve", "--delay", "11"], catch_exceptions=False)
    mock_sleep.assert_called_once_with(11)

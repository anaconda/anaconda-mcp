"""Tests for signal handling and the native-composition `serve` CLI command."""

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
def mock_serve_deps():
    """Mock everything ``serve()`` touches except @long_running signal registration.

    Lets CliRunner drive ``anaconda-mcp serve`` without real auth, network,
    telemetry, or actually starting the stdio server.
    """
    with (
        patch("anaconda_mcp.cli.get_auth_token", return_value="tok"),
        patch("anaconda_mcp.cli.validate_auth_token", return_value=True),
        patch("anaconda_mcp.cli.BaseClient"),
        patch("anaconda_mcp.cli.emit_event"),
        patch("anaconda_mcp.cli.client_token", return_value=None),
        patch("anaconda_mcp.cli.install_shutdown_handlers"),
        patch("anaconda_mcp.cli.time.sleep"),
        patch("anaconda_mcp.cli.build_composed_server") as mock_build,
    ):
        mock_build.return_value.run.return_value = None
        yield mock_build


def test_serve_installs_signal_handlers_via_long_running(mock_serve_deps):
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


def test_serve_installs_handlers_before_sleep(mock_serve_deps):
    """@long_running must install signal handlers before serve() reaches time.sleep()."""
    import anaconda_cli_base.lifecycle as lifecycle

    call_order = []
    original_signal = lifecycle.signal.signal

    def capturing_signal(signum, handler):
        call_order.append("signal")
        return original_signal(signum, handler)

    with (
        patch("anaconda_cli_base.lifecycle.signal.signal", side_effect=capturing_signal),
        patch("anaconda_mcp.cli.time.sleep", side_effect=lambda seconds: call_order.append("sleep")),
    ):
        CliRunner().invoke(cli, ["serve"], catch_exceptions=False)

    assert "signal" in call_order, "signal handlers were never installed"
    assert "sleep" in call_order, "time.sleep was never called"
    assert call_order.index("signal") < call_order.index("sleep"), (
        "signal handlers must be installed before time.sleep()"
    )


def test_serve_sigterm_handler_delegates_to_trigger_shutdown(mock_serve_deps):
    """The installed SIGTERM handler routes to cli-base trigger_shutdown."""
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


def test_serve_normal_flow_runs_composed_server_over_stdio(mock_serve_deps):
    """Without a signal, serve builds the composed server and runs it over stdio (exit 0)."""
    result = CliRunner().invoke(cli, ["serve"], catch_exceptions=False)
    assert result.exit_code == 0
    mock_serve_deps.assert_called_once()
    mock_serve_deps.return_value.run.assert_called_once_with(transport="stdio")


def test_serve_exception_from_server_exits_with_1(mock_serve_deps):
    """If the composed server's run() raises, serve catches it and exits with code 1."""
    mock_serve_deps.return_value.run.side_effect = RuntimeError("server exploded")
    result = CliRunner().invoke(cli, ["serve"], catch_exceptions=True)
    assert result.exit_code == 1


def test_serve_unauthenticated_exits_with_1_before_building_server():
    """A missing token short-circuits with exit 1 before the server is built."""
    with (
        patch("anaconda_mcp.cli.time.sleep"),
        patch("anaconda_mcp.cli.get_auth_token", return_value=None),
        patch("anaconda_mcp.cli.build_composed_server") as mock_build,
    ):
        result = CliRunner().invoke(cli, ["serve"])
    assert result.exit_code == 1
    mock_build.assert_not_called()


def test_serve_delay_option_is_respected(mock_serve_deps):
    """The --delay flag must be passed directly to time.sleep."""
    with patch("anaconda_mcp.cli.time.sleep") as mock_sleep:
        CliRunner().invoke(cli, ["serve", "--delay", "11"], catch_exceptions=False)
    mock_sleep.assert_called_once_with(11)


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


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Real signal-driven shutdown is POSIX-only: on Windows SIGTERM maps to "
    "TerminateProcess (hard kill, no handler) and Popen.send_signal(SIGINT) raises ValueError.",
)
@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGINT])
def test_real_signal_triggers_bounded_shutdown_without_hanging(signum):
    """A real OS SIGTERM/SIGINT must route through cli-base trigger_shutdown, run
    shutdown hooks to unblock the loop, and exit promptly (watchdog forces <~10s)."""
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

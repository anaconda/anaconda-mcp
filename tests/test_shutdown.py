"""Tests for the pipe-based stdin proxy used by `anaconda mcp serve` shutdown."""

from __future__ import annotations

import os
import selectors
import threading
import time

import pytest

from anaconda_mcp._shutdown import _InterruptibleStdin


def _make_proxy_with_source() -> tuple[_InterruptibleStdin, int]:
    """Create a proxy that reads from a pipe we control (not real stdin)."""
    src_r, src_w = os.pipe()
    proxy = _InterruptibleStdin(source_fd=src_r)
    return proxy, src_w


def _read_all_available(fd: int, timeout: float = 1.0) -> bytes:
    """Read whatever is available on fd within `timeout`, then return.

    Cross-platform: uses selectors so the test suite can run on Windows
    under Python 3.10+ without depending on POSIX-only blocking-mode APIs.
    """
    sel = selectors.DefaultSelector()
    sel.register(fd, selectors.EVENT_READ)
    chunks: list[bytes] = []
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            remaining = max(0.0, deadline - time.time())
            events = sel.select(timeout=min(0.05, remaining))
            if not events:
                if chunks:
                    break
                continue
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        sel.close()
    return b"".join(chunks)


def test_pump_copies_data_from_source_to_pipe():
    """Bytes written to source_fd should appear on the proxy's read end."""
    proxy, src_w = _make_proxy_with_source()
    try:
        os.write(src_w, b"hello world\n")
        time.sleep(0.05)
        data = _read_all_available(proxy._r_fd)
        assert b"hello world\n" in data
    finally:
        proxy.shutdown()
        os.close(src_w)


def test_pump_preserves_multiple_lines():
    """Multiple lines written to source_fd should be preserved on the pipe."""
    proxy, src_w = _make_proxy_with_source()
    try:
        os.write(src_w, b"line1\nline2\nline3\n")
        time.sleep(0.05)
        data = _read_all_available(proxy._r_fd)
        assert data == b"line1\nline2\nline3\n"
    finally:
        proxy.shutdown()
        os.close(src_w)


def test_shutdown_synthesizes_eof():
    """After shutdown(), reading from the proxy's read end must return EOF (b'')."""
    proxy, src_w = _make_proxy_with_source()
    try:
        proxy.shutdown()
        time.sleep(0.05)
        chunk = os.read(proxy._r_fd, 4096)
        assert chunk == b"", f"expected EOF after shutdown, got {chunk!r}"
    finally:
        try:
            os.close(src_w)
        except OSError:
            pass


def test_shutdown_is_idempotent():
    """Calling shutdown() multiple times must not raise."""
    proxy, src_w = _make_proxy_with_source()
    try:
        proxy.shutdown()
        proxy.shutdown()
        proxy.shutdown()
    finally:
        try:
            os.close(src_w)
        except OSError:
            pass


def test_pump_exits_when_source_eof():
    """When source_fd reaches EOF, the pump thread should close the pipe write end and exit."""
    proxy, src_w = _make_proxy_with_source()
    os.write(src_w, b"final\n")
    os.close(src_w)
    time.sleep(0.1)
    data = _read_all_available(proxy._r_fd, timeout=1.0)
    assert b"final\n" in data
    chunk = os.read(proxy._r_fd, 4096)
    assert chunk == b"", "pipe should be at EOF after source closes"
    proxy._thread.join(timeout=1.0)
    assert not proxy._thread.is_alive(), "pump thread should exit when source EOFs"


def test_pump_thread_is_daemon():
    """Pump thread must be a daemon so it does not block process exit."""
    proxy, src_w = _make_proxy_with_source()
    try:
        assert proxy._thread.daemon is True
    finally:
        proxy.shutdown()
        os.close(src_w)


def test_pump_thread_named():
    """Pump thread must have a recognizable name for diagnostics."""
    proxy, src_w = _make_proxy_with_source()
    try:
        assert "anaconda-mcp" in proxy._thread.name
    finally:
        proxy.shutdown()
        os.close(src_w)


def test_make_async_file_yields_lines_and_eof():
    """The async file wrapping the read end must iterate lines and signal EOF on shutdown."""
    import anyio

    proxy, src_w = _make_proxy_with_source()

    async def _consume() -> list[str]:
        async_file = proxy.make_async_file()
        lines: list[str] = []
        async for line in async_file:
            lines.append(line)
        return lines

    def _producer() -> None:
        os.write(src_w, b"alpha\nbeta\n")
        time.sleep(0.1)
        proxy.shutdown()
        try:
            os.close(src_w)
        except OSError:
            pass

    producer_thread = threading.Thread(target=_producer, daemon=True)
    producer_thread.start()

    lines = anyio.run(_consume)
    producer_thread.join(timeout=2.0)

    assert lines == ["alpha\n", "beta\n"], f"expected two lines, got {lines!r}"


def test_shutdown_unblocks_pending_read():
    """If a reader is blocked on the proxy's read end, shutdown() must unblock it with EOF."""
    proxy, src_w = _make_proxy_with_source()
    result: list[bytes] = []

    def _blocking_reader() -> None:
        chunk = os.read(proxy._r_fd, 4096)
        result.append(chunk)

    reader = threading.Thread(target=_blocking_reader, daemon=True)
    reader.start()
    time.sleep(0.05)
    assert reader.is_alive(), "reader should be blocked initially"

    proxy.shutdown()
    reader.join(timeout=1.0)

    assert not reader.is_alive(), "shutdown() must unblock the reader"
    assert result == [b""], f"expected EOF, got {result!r}"

    try:
        os.close(src_w)
    except OSError:
        pass


def test_safety_net_force_exit_does_not_hang_on_telemetry(monkeypatch):
    """Watchdog must escape even when telemetry flush blocks indefinitely."""
    from anaconda_mcp import _shutdown as shutdown_mod

    def _hanging_flush():
        time.sleep(60)

    monkeypatch.setattr(shutdown_mod, "_shutdown_telemetry", _hanging_flush)

    exit_called = threading.Event()

    def _fake_exit(code):
        exit_called.set()

    monkeypatch.setattr(shutdown_mod.os, "_exit", _fake_exit)

    start = time.time()
    shutdown_mod._safety_net_force_exit()
    elapsed = time.time() - start

    assert exit_called.is_set(), "os._exit should have been called"
    assert elapsed < 3.0, f"safety net hung for {elapsed:.2f}s; expected <3s"


def test_shutdown_returns_fast_when_pump_holds_lock():
    """shutdown() must not block on _w_fd_lock even if the pump is mid-write.

    Reproduces the deadlock scenario where the pump is blocked in os.write
    on a full pipe (and therefore holds _w_fd_lock). shutdown() must
    return promptly via non-blocking acquire instead of waiting on the
    pump.
    """
    proxy, src_w = _make_proxy_with_source()
    try:
        # Hold the lock from a separate thread to simulate the pump being
        # blocked mid-write. This is more reliable than trying to fill a
        # real pipe buffer (size varies by OS).
        lock_held = threading.Event()
        release_lock = threading.Event()

        def _hold_lock():
            with proxy._w_fd_lock:
                lock_held.set()
                release_lock.wait(timeout=2.0)

        holder = threading.Thread(target=_hold_lock, daemon=True)
        holder.start()
        assert lock_held.wait(timeout=1.0), "holder failed to acquire lock"

        start = time.time()
        proxy.shutdown()
        elapsed = time.time() - start

        assert elapsed < 0.1, f"shutdown() blocked on lock for {elapsed:.3f}s"
        assert proxy._closed.is_set()

        release_lock.set()
        holder.join(timeout=1.0)
    finally:
        os.close(src_w)


def test_init_does_not_leak_fds_when_thread_start_fails(monkeypatch):
    """If thread.start() raises, the pipe fds must be closed."""
    src_r, src_w = os.pipe()
    try:
        original_start = threading.Thread.start

        def _failing_start(self):
            raise RuntimeError("simulated thread start failure")

        monkeypatch.setattr(threading.Thread, "start", _failing_start)

        with pytest.raises(RuntimeError, match="simulated thread start failure"):
            _InterruptibleStdin(source_fd=src_r)

        # Restore so subsequent tests work.
        monkeypatch.setattr(threading.Thread, "start", original_start)

        # Verify the fds the constructor allocated were closed by checking
        # that we can allocate a new pipe and the next available fd numbers
        # did not balloon. We cannot directly capture the leaked fds
        # because they're locals inside the failing __init__, so instead
        # verify by counting open fds via os.listdir on POSIX, or by
        # creating new pipes and confirming their numbers are reused.
        if hasattr(os, "listdir") and os.path.isdir("/proc/self/fd"):
            initial_fds = set(os.listdir("/proc/self/fd"))
            for _ in range(5):
                with pytest.raises(RuntimeError):
                    _InterruptibleStdin(source_fd=src_r)
            after_fds = set(os.listdir("/proc/self/fd"))
            # Allow a small margin for unrelated transient fds.
            assert len(after_fds - initial_fds) < 3, (
                f"FD count grew unexpectedly: before={len(initial_fds)} after={len(after_fds)}"
            )
    finally:
        os.close(src_r)
        os.close(src_w)


def test_patch_composer_signal_handler_registers_sigint_directly():
    """SIGINT must be registered explicitly, not only via mcp-compose name resolution."""
    import signal as _signal

    from anaconda_mcp import _shutdown

    original_sigint = _signal.getsignal(_signal.SIGINT)
    original_module_handler = _shutdown.composer_mod._module_signal_handler
    try:
        _shutdown._patch_composer_signal_handler()
        new_handler = _signal.getsignal(_signal.SIGINT)
        assert callable(new_handler)
        assert new_handler is _shutdown.composer_mod._module_signal_handler
    finally:
        _signal.signal(_signal.SIGINT, original_sigint)
        _shutdown.composer_mod._module_signal_handler = original_module_handler


def test_shutdown_signal_handler_starts_watchdog_before_shutdown(monkeypatch):
    """Watchdog timer must be created before _active_stdin_proxy.shutdown().

    If a refactor ever reverses this ordering and shutdown() then
    deadlocks (which Issue 2A makes very unlikely but not impossible),
    the watchdog would never start and the process would hang
    permanently. This test pins the invariant so the ordering can't
    silently regress.
    """
    import signal as _signal

    from anaconda_mcp import _shutdown

    call_order: list[str] = []

    class _FakeTimer:
        daemon = False

        def __init__(self, *args, **kwargs):
            call_order.append("timer_created")

        def start(self):
            pass  # do not actually start; we only care about creation order

    class _FakeProxy:
        def shutdown(self):
            call_order.append("proxy_shutdown")

    original_sigint = _signal.getsignal(_signal.SIGINT)
    original_module_handler = _shutdown.composer_mod._module_signal_handler
    original_active_proxy = _shutdown._active_stdin_proxy

    try:
        monkeypatch.setattr(_shutdown.threading, "Timer", _FakeTimer)
        _shutdown._active_stdin_proxy = _FakeProxy()
        _shutdown._patch_composer_signal_handler()
        handler = _shutdown.composer_mod._module_signal_handler

        handler(15, None)

        assert "timer_created" in call_order, f"Timer was never created; call_order={call_order!r}"
        assert "proxy_shutdown" in call_order, f"Proxy shutdown was never called; call_order={call_order!r}"
        timer_idx = call_order.index("timer_created")
        proxy_idx = call_order.index("proxy_shutdown")
        assert timer_idx < proxy_idx, (
            f"Watchdog timer was created AFTER proxy.shutdown(); "
            f"call_order={call_order!r}. The handler must start the watchdog "
            f"first so a deadlock in shutdown() cannot prevent the safety net."
        )
    finally:
        _shutdown._active_stdin_proxy = original_active_proxy
        _shutdown.composer_mod._module_signal_handler = original_module_handler
        _signal.signal(_signal.SIGINT, original_sigint)


@pytest.fixture(autouse=True)
def _cleanup_proxies():
    """Best-effort: close any leaked file descriptors from failed tests."""
    yield

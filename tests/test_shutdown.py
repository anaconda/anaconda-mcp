"""Tests for the pipe-based stdin proxy used by `anaconda mcp serve` shutdown."""

from __future__ import annotations

import os
import threading
import time

import pytest

from anaconda_mcp._shutdown import _InterruptibleStdin


def _make_proxy_with_source() -> tuple[_InterruptibleStdin, int]:
    """Create a proxy that reads from a pipe we control (not real stdin)."""
    src_r, src_w = os.pipe()
    proxy = _InterruptibleStdin(source_fd=src_r)
    return proxy, src_w


def _read_all_available(fd: int, timeout: float = 1.0, expected: int | None = None) -> bytes:
    """Read available bytes from `fd` within `timeout`, then return.

    Cross-platform: a daemon reader thread does blocking ``os.read``. Windows
    ``select()`` only accepts sockets, not pipe file descriptors, so a
    selectors-based poll raises ``OSError(WinError 10038)`` on a pipe. Blocking
    reads on a daemon thread behave identically on POSIX and Windows (the other
    tests in this file that block on ``os.read`` of the pipe confirm this).

    If `expected` is given, returns as soon as that many bytes have arrived so
    callers that know the payload size don't wait out the full `timeout`.
    Otherwise reads until EOF or `timeout` elapses. A leftover blocked read
    lives on a daemon thread and is reaped at process exit.
    """
    chunks: list[bytes] = []
    lock = threading.Lock()
    stop = threading.Event()

    def _reader() -> None:
        while not stop.is_set():
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                return
            if not chunk:
                return  # EOF
            with lock:
                chunks.append(chunk)
                total = sum(len(c) for c in chunks)
            if expected is not None and total >= expected:
                return

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()
    reader.join(timeout)
    stop.set()
    with lock:
        return b"".join(chunks)


def test_pump_copies_data_from_source_to_pipe():
    """Bytes written to source_fd should appear on the proxy's read end."""
    proxy, src_w = _make_proxy_with_source()
    try:
        os.write(src_w, b"hello world\n")
        time.sleep(0.05)
        data = _read_all_available(proxy._r_fd, expected=len(b"hello world\n"))
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
        data = _read_all_available(proxy._r_fd, expected=len(b"line1\nline2\nline3\n"))
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


def test_compose_signal_handler_delegates_to_trigger_shutdown(monkeypatch):
    """The patched compose signal handler must delegate to
    ``anaconda_cli_base.lifecycle.trigger_shutdown``.

    The watchdog, lifecycle hooks, and bounded telemetry flush now live in
    cli-base. The compose adapter installed by
    ``_patch_composer_signal_handler`` is a thin bridge: when a signal
    arrives, it must call ``trigger_shutdown(signum)`` so cli-base owns
    the shutdown sequence. This test pins that delegation contract so it
    cannot silently regress.
    """
    import signal as _signal

    from anaconda_mcp import _shutdown

    captured: list[int] = []

    def _spy(signum: int) -> None:
        captured.append(signum)

    original_sigint = _signal.getsignal(_signal.SIGINT)
    original_module_handler = _shutdown.composer_mod._module_signal_handler

    try:
        # Patch the module-local reference (``from ... import trigger_shutdown``
        # binds a name in ``_shutdown``; patching the source module would not
        # intercept the call site).
        monkeypatch.setattr(_shutdown, "trigger_shutdown", _spy)
        _shutdown._patch_composer_signal_handler()
        handler = _shutdown.composer_mod._module_signal_handler

        handler(15, None)

        assert captured == [15], f"compose signal handler must delegate to trigger_shutdown(15); captured={captured!r}"
    finally:
        _shutdown.composer_mod._module_signal_handler = original_module_handler
        _signal.signal(_signal.SIGINT, original_sigint)


@pytest.fixture(autouse=True)
def _cleanup_proxies():
    """Best-effort: close any leaked file descriptors from failed tests."""
    yield

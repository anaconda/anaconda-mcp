"""Graceful shutdown coordination for ``anaconda mcp serve``.

Why this module exists
----------------------
``anaconda mcp serve`` faces two compounded shutdown problems:

1. **mcp-compose's stdio transport blocks an uncancellable thread.**
   ``mcp.server.stdio.stdio_server`` runs ``stdin_reader`` which iterates
   ``async for line in stdin``.  ``stdin`` is an ``anyio.AsyncFile`` whose
   ``readline`` dispatches to ``anyio.to_thread.run_sync(file.readline)``.
   ``run_sync`` (with its default ``abandon_on_cancel=False``) wraps the
   worker thread future in a ``CancelScope(shield=True)``.  asyncio
   cancellation never propagates into the worker thread, and the OS-level
   ``read(0)`` syscall cannot be interrupted from the same process.  The
   only way the reader exits is by seeing data or EOF on the underlying
   file.  Therefore ``run_stdio_async`` never returns on SIGTERM/SIGINT
   and ``composer.stop()`` never completes.

2. **anaconda-cli-base 0.9+ leaks OTel atexit handlers on long-running
   commands.**  ``_before_command`` calls ``_ensure_initialized`` which
   constructs ``TracerProvider`` / ``MeterProvider`` / ``LoggerProvider``;
   each registers an atexit handler.  Those are only unregistered by
   ``_after_command``, which fires only on a clean ``SystemExit`` from the
   wrapped command.  Because ``serve`` blocks in ``asyncio.run`` and never
   returns, the atexit handlers stay registered.  When the process is
   eventually killed, the gRPC OTel exporters block on flush and the
   process hangs again at interpreter teardown.

How this module fixes it
------------------------
Insert a pipe between real ``stdin`` and ``stdio_server``'s reader.  A
daemon "pump" thread copies real stdin into the pipe; the reader sees only
the pipe's read end.  On SIGTERM/SIGINT we close the pipe's write end,
synthesizing EOF for the reader.  The reader exits naturally,
``run_stdio_async`` returns, ``composer.stop()`` runs from
``run_server``'s ``finally`` block, ``asyncio.run`` completes,
``sys.exit(0)`` raises ``SystemExit``, ``ErrorHandledGroup.main`` catches
it, ``_after_command`` fires, ``_shutdown_telemetry`` flushes and
unregisters the OTel atexit handlers, and the process exits cleanly with
no force-termination.

A safety-net watchdog (``WATCHDOG_DEADLINE_SECS``) is started when a
signal arrives.  It only fires if the clean shutdown path stalls; in
normal operation the process exits well before it expires and the daemon
timer dies with it.

Why the patches must be installed before ``mcp_compose.cli.serve_command``
runs:

* ``FastMCP.run_stdio_async`` is replaced at the class level so the
  ``composer.composed_server`` instance picks up our version when
  ``await composer.composed_server.run_stdio_async()`` is called inside
  ``mcp_compose.cli.run_server``.
* ``mcp_compose.composer._module_signal_handler`` is replaced at the
  module level so ``signal.signal(SIGTERM, _module_signal_handler)``
  inside ``MCPServerComposer._register_composer`` resolves the name to
  our patched handler at registration time.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from io import BufferedReader, FileIO, TextIOWrapper
from typing import Any

import mcp_compose.composer as composer_mod
from anaconda_cli_base.telemetry import _shutdown_telemetry
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

logger = logging.getLogger(__name__)

WATCHDOG_DEADLINE_SECS = 10.0
"""Safety-net timeout. Long enough to cover composer.stop() (default 5 s
process-termination timeout) plus telemetry flush; short enough to bound
worst-case shutdown latency for users."""

_active_stdin_proxy: _InterruptibleStdin | None = None
_handlers_installed: bool = False


class _InterruptibleStdin:
    """Pipe-backed stdin proxy that can synthesize EOF on demand.

    The pump thread copies real ``stdin`` into a pipe.  The exposed
    async file wraps the pipe's read end so ``stdio_server`` reads from
    the pipe instead of real ``stdin``.  ``shutdown()`` closes the pipe's
    write end, causing the reader to see EOF on its next read.

    The pump thread is a daemon, so it does not block process exit even
    if it is still blocked in ``read(real_stdin)`` when the process
    exits.

    Parameters
    ----------
    source_fd:
        File descriptor to read from.  Defaults to ``0`` (real stdin).
        Parameterised for testability.
    """

    def __init__(self, source_fd: int = 0) -> None:
        self._source_fd = source_fd
        self._r_fd, self._w_fd = os.pipe()
        try:
            self._closed = threading.Event()
            self._w_fd_lock = threading.Lock()
            self._w_fd_open = True
            self._thread = threading.Thread(
                target=self._pump,
                daemon=True,
                name="anaconda-mcp-stdin-pump",
            )
            self._thread.start()
        except BaseException:
            for fd in (self._r_fd, self._w_fd):
                try:
                    os.close(fd)
                except OSError:
                    pass
            raise

    def _pump(self) -> None:
        try:
            while not self._closed.is_set():
                try:
                    chunk = os.read(self._source_fd, 4096)
                except OSError:
                    return
                if not chunk:
                    return
                if not self._safe_write(chunk):
                    return
        finally:
            self._close_write_end()

    def _safe_write(self, data: bytes) -> bool:
        with self._w_fd_lock:
            if not self._w_fd_open:
                return False
            try:
                os.write(self._w_fd, data)
                return True
            except OSError:
                return False

    def _close_write_end(self) -> None:
        """Pump-thread path: blocking acquire is appropriate here."""
        with self._w_fd_lock:
            self._close_write_end_locked()

    def _close_write_end_locked(self) -> None:
        """Close the pipe write end. Caller MUST hold _w_fd_lock."""
        if not self._w_fd_open:
            return
        self._w_fd_open = False
        try:
            os.close(self._w_fd)
        except OSError:
            pass

    def make_async_file(self) -> Any:
        import anyio

        sync_file = TextIOWrapper(
            BufferedReader(FileIO(self._r_fd, mode="r", closefd=True)),
            encoding="utf-8",
            errors="replace",
        )
        return anyio.wrap_file(sync_file)

    def shutdown(self) -> None:
        """Synthesize EOF for the reader.

        Idempotent. Safe to call from a signal handler — never blocks on the
        pump thread's lock.

        Returning fast does NOT guarantee clean shutdown completes. If the
        pump holds ``_w_fd_lock`` (blocked in ``os.write`` on a full pipe
        whose reader is stalled), the write end won't close until the pump's
        ``finally`` block runs, which itself requires ``os.write`` to
        return. In that pathological case the reader never sees EOF; the
        watchdog timer (started before ``shutdown()`` in
        ``_shutdown_signal_handler``) is what ultimately escapes the
        process via ``os._exit()``.

        The common case — reader actively draining the pipe — closes
        cleanly within milliseconds.
        """
        if self._closed.is_set():
            return
        self._closed.set()
        if self._w_fd_lock.acquire(blocking=False):
            try:
                self._close_write_end_locked()
            finally:
                self._w_fd_lock.release()


def install_shutdown_handlers() -> None:
    """Install graceful-shutdown patches.

    Idempotent; subsequent calls are no-ops.  Must be called from the
    ``serve`` command before ``mcp_compose.cli.serve_command`` runs.
    """
    global _handlers_installed
    if _handlers_installed:
        return
    _patch_run_stdio_async()
    _patch_composer_signal_handler()
    _handlers_installed = True


def _patch_run_stdio_async() -> None:
    async def _patched_run_stdio_async(self: Any) -> None:
        global _active_stdin_proxy
        _active_stdin_proxy = _InterruptibleStdin()
        try:
            async with stdio_server(stdin=_active_stdin_proxy.make_async_file()) as (
                read_stream,
                write_stream,
            ):
                await self._mcp_server.run(
                    read_stream,
                    write_stream,
                    self._mcp_server.create_initialization_options(),
                )
        finally:
            _active_stdin_proxy = None

    FastMCP.run_stdio_async = _patched_run_stdio_async  # type: ignore[method-assign]


def _patch_composer_signal_handler() -> None:
    original_handler = composer_mod._module_signal_handler

    def _shutdown_signal_handler(signum: int, frame: Any) -> None:
        # Start the watchdog FIRST so it cannot be blocked by anything below.
        # Without this ordering, a deadlock in shutdown() or original_handler()
        # would prevent the watchdog from ever firing.
        timer = threading.Timer(WATCHDOG_DEADLINE_SECS, _safety_net_force_exit)
        timer.daemon = True
        timer.start()

        if _active_stdin_proxy is not None:
            _active_stdin_proxy.shutdown()

        try:
            original_handler(signum, frame)
        except Exception:
            logger.debug("mcp-compose signal handler raised", exc_info=True)

    composer_mod._module_signal_handler = _shutdown_signal_handler
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _shutdown_signal_handler)


def _safety_net_force_exit() -> None:
    """Last-resort exit if the clean shutdown path stalls.

    The telemetry flush runs on a daemon thread with a hard 2 s timeout
    so the watchdog cannot itself hang on the same operation that
    stalled the clean path (e.g. a gRPC OTLP exporter blocked on a
    dropped network connection).
    """
    flush_thread = threading.Thread(target=_try_flush_telemetry, daemon=True)
    flush_thread.start()
    flush_thread.join(timeout=2.0)
    os._exit(0)


def _try_flush_telemetry() -> None:
    try:
        _shutdown_telemetry()
    except Exception:
        logger.debug("Failed to flush telemetry on safety-net exit", exc_info=True)

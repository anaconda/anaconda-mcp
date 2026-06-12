"""Graceful shutdown for ``anaconda mcp serve``.

Makes a long-running ``anaconda mcp serve`` process exit promptly and cleanly on
SIGTERM/SIGINT (and when the client closes stdin) without hanging on telemetry
flush or on mcp/anyio's shielded, effectively uncancellable stdin reader. The
watchdog, lifecycle hooks, and bounded telemetry flush live in
``anaconda_cli_base.lifecycle`` (and ``serve()`` is decorated with
``@long_running``); this module supplies two mcp-specific monkey-patches plus
the hook that unblocks the serve loop.

Byte path (stdin -> server)
---------------------------
``stdio_server`` normally reads real stdin directly via an anyio worker thread.
That thread runs under a shielded cancel scope (anyio's default
``abandon_on_cancel=False``), so cancellation is deferred until the blocking
read returns -- and a read blocked on idle stdin never returns, so it would
otherwise keep the process alive on shutdown. ``_InterruptibleStdin``
interposes an OS pipe::

    real stdin (fd 0)
      --[daemon pump thread: os.read -> os.write]--> os.pipe() write end
      --> read end wrapped as an anyio async file --> stdio_server --> server

``_patch_run_stdio_async`` replaces ``FastMCP.run_stdio_async`` so the composed
server reads from the pipe's read end instead of real stdin. The pump is a
daemon thread: if it is still blocked in ``os.read(real_stdin)`` at exit, it
does not block process termination.

Threads vs. coroutines
----------------------
Exactly one extra OS thread is introduced: the pump. It *blocks* in ``os.read``
(which releases the GIL) when stdin is idle -- no busy-spin -- and only contends
for the GIL briefly per ~4 KB chunk, so the cost scales with stdin volume
(negligible for bursty, low-volume MCP JSON-RPC). Everything else runs on the
main thread's anyio event loop. Pump and loop communicate only through the pipe;
``shutdown()`` and the close path are guarded by ``_w_fd_lock`` so the signal
handler and the pump never corrupt the write-end state.

Signal flow (shutdown)
----------------------
mcp-compose installs its own process-wide signal handlers during composer
construction. ``_patch_composer_signal_handler`` swaps mcp-compose's
``_module_signal_handler`` for a bridge that first calls ``trigger_shutdown``
(cli-base: start the 10s watchdog, run hooks, bounded telemetry flush) and then
the original mcp-compose handler (schedules ``composer.stop()``). Unlike
cli-base's SIGINT handler, the bridge does not re-raise ``KeyboardInterrupt`` --
that would unwind the stack before the loop-scheduled ``composer.stop()`` runs,
leaking downstream processes.

Three layers register handlers, and ordering matters. ``serve()``'s
``@long_running`` installs cli-base SIGTERM/SIGINT handlers first; this patch
then rebinds the module global and re-registers SIGINT only (not SIGTERM);
finally composer construction registers the now-bridged
``_module_signal_handler`` for both signals, overwriting cli-base's SIGTERM
handler. Because the patch runs before construction, the composer picks up the
bridged handler. A SIGTERM arriving in the gap before construction falls
through to cli-base's handler -- correct, since no composer exists yet to stop,
and ``trigger_shutdown`` is idempotent so the bridged path cannot double-fire
it.

On shutdown the registered hook ``_shutdown_stdin_proxy`` closes the pipe's
write end -> the reader sees EOF -> ``run_stdio_async`` unblocks and returns (no
longer holding the event loop open). Meanwhile the bridge also calls the
original handler, which schedules ``composer.stop()`` -> ``asyncio.run``
completes -> clean exit. The watchdog ``os._exit`` is only a backstop if that
unwinding stalls.

No init race
------------
The pump is the *only* reader of fd 0, and ``_patch_run_stdio_async`` is applied
at the class level inside ``install_shutdown_handlers()`` -- before
``serve_command`` runs -- so the unpatched direct-stdin reader is never used.
Bytes arriving before the pump's first ``os.read`` are buffered by the OS and
read once it starts; none are lost.

Portability
-----------
The pump uses portable ``os.read``/``os.write`` (not Linux-only ``os.splice``)
so it works on macOS and Windows. Signal-driven *graceful* shutdown is
POSIX-only: on Windows SIGTERM maps to ``TerminateProcess`` (hard kill, no
handler), but the stdin-EOF path above is signal-independent and works
cross-platform -- it is the normal way an MCP client stops a stdio server.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from io import BufferedReader, FileIO, TextIOWrapper
from typing import Any

import mcp_compose.composer as composer_mod
from anaconda_cli_base.lifecycle import register_shutdown_hook, trigger_shutdown
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

logger = logging.getLogger(__name__)

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
    """Install graceful-shutdown patches; idempotent. Call before serve.

    Logs a warning if the composer signal bridge is not detectable after
    patching, signalling that mcp-compose's internals may have changed.
    """
    global _handlers_installed
    if _handlers_installed:
        return
    _patch_run_stdio_async()
    _patch_composer_signal_handler()
    register_shutdown_hook(_shutdown_stdin_proxy)
    _handlers_installed = True
    if not getattr(composer_mod._module_signal_handler, _BRIDGE_SENTINEL, False):
        logger.warning(
            "shutdown bridge not present on mcp_compose._module_signal_handler; "
            "SIGTERM may bypass cli-base bounded shutdown (mcp-compose internals changed?)"
        )


def _shutdown_stdin_proxy() -> None:
    """Lifecycle hook: close the stdin proxy pipe to unblock the reader."""
    if _active_stdin_proxy is not None:
        _active_stdin_proxy.shutdown()


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


_BRIDGE_SENTINEL = "_anaconda_shutdown_bridge"


def _patch_composer_signal_handler() -> None:
    """Replace mcp-compose's module signal handler with a cli-base bridge.

    Idempotent: re-invocation is a no-op. The sentinel attribute prevents the
    new bridge from wrapping a previous bridge (which would make
    ``trigger_shutdown`` fire once per accumulated layer).
    """
    original_handler = composer_mod._module_signal_handler
    if getattr(original_handler, _BRIDGE_SENTINEL, False):
        return

    def _shutdown_signal_handler(signum: int, frame: Any) -> None:
        # trigger_shutdown owns the watchdog + bounded telemetry flush; it does
        # not raise (SIGINT KeyboardInterrupt is not re-raised here) so that
        # mcp-compose's loop-scheduled composer.stop() still runs after it.
        trigger_shutdown(signum)
        try:
            original_handler(signum, frame)
        except Exception:
            logger.debug("mcp-compose signal handler raised", exc_info=True)

    setattr(_shutdown_signal_handler, _BRIDGE_SENTINEL, True)
    composer_mod._module_signal_handler = _shutdown_signal_handler
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _shutdown_signal_handler)

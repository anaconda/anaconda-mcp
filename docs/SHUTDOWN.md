# Shutdown Fix: `anaconda mcp serve` SIGTERM/SIGINT hang

This document explains why `src/anaconda_mcp/_shutdown.py` exists, what it patches, and how to verify it works. It's written for reviewers and maintainers, not end users.

---

## What this fixes

Before this fix, sending SIGTERM or SIGINT to `anaconda mcp serve` caused the process to hang indefinitely, requiring a SIGKILL to terminate. Two independent issues compound to produce the hang; both must be addressed for clean shutdown. This module makes shutdown clean and bounded: the process exits in under one second on the primary path, with a 10-second safety-net watchdog as a last resort.

---

## Root cause 1: mcp-compose's stdio reader is uncancellable

`mcp-compose`'s STDIO mode awaits `composer.composed_server.run_stdio_async()`, a `mcp.server.fastmcp.FastMCP` method. That method opens an `async with stdio_server()` block whose `stdin_reader` task does:

```python
async for line in stdin:    # mcp/server/stdio.py:63
    ...
```

`stdin` is an `anyio.AsyncFile` wrapping `sys.stdin.buffer`. Iterating it calls `await self.readline()`, which calls:

```python
return await to_thread.run_sync(self._fp.readline)   # anyio/_core/_fileio.py:99
```

`anyio.to_thread.run_sync` defaults to `abandon_on_cancel=False`, which wraps the worker-thread future in a `CancelScope(shield=True)`. A shielded cancel scope absorbs every form of asyncio cancellation. The worker thread is uncancellable from Python, and the OS thread is blocked in `read(0)`, a kernel syscall on `sys.stdin`'s file descriptor.

On POSIX systems, `read(0)` cannot be reliably interrupted from within the same process. As a result, `run_stdio_async()` never returns on SIGTERM/SIGINT. The `finally: await composer.stop()` block in `mcp_compose/cli.py` never executes, the asyncio loop never terminates, and `serve()` never reaches `sys.exit(_serve(ns))`.

---

## Root cause 2: cli-base 0.9 leaks OTel atexit handlers

`anaconda-cli-base`'s `ErrorHandledGroup.main()` calls `_before_command()` on every CLI invocation. `_before_command()` calls `_ensure_initialized()`, which constructs `TracerProvider`, `MeterProvider`, and `LoggerProvider`. Each provider's `__init__` calls `atexit.register(self.shutdown)` when `shutdown_on_exit=True` (the default). Source citations:

- `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py:1340-1341`
- `opentelemetry-sdk/src/opentelemetry/sdk/metrics/_internal/__init__.py:503-504`
- `opentelemetry-sdk/src/opentelemetry/sdk/_logs/_internal/__init__.py:809-810`

cli-base's `_after_command()` calls `_shutdown_telemetry()`, which `force_flush`es each provider and then `atexit.unregister`s its handler. But `_after_command()` only runs on a clean `SystemExit` from `super().main()`. Because `serve()` blocks forever in `asyncio.run()` (per root cause 1), `_after_command()` never fires, and the OTel atexit handlers stay registered.

When the process is finally killed, the Python interpreter runs the still-registered atexit handlers. The gRPC OTLP exporters attempt to flush via `channel.close()`, which blocks waiting for in-flight calls to drain. The default `OTEL_EXPORTER_OTLP_TIMEOUT` is 10 seconds per call, multiplied by retries. The process hangs again at interpreter teardown.

`KeyboardInterrupt` is not caught by `ErrorHandledGroup.main()`. It propagates out, bypassing every `_after_command()` call site, so SIGINT cannot heal this either.

---

## Why this is unique to `anaconda mcp serve`

Other anaconda CLI commands are short-lived: they `print -> sys.exit -> SystemExit -> _after_command fires -> _shutdown_telemetry -> clean exit`. `mcp serve` is the only consumer that:

1. Blocks indefinitely inside `asyncio.run()` via mcp-compose.
2. Uses mcp-compose's STDIO transport, which has the uncancellable-thread issue.
3. Relies on external SIGTERM rather than raising `SystemExit` itself.

No other anaconda CLI plugin runs a persistent asyncio event loop with an uncancellable stdin reader.

---

## The fix mechanism

We can't directly cancel the OS thread blocked in `read(0)`. Instead, we route around it: insert a pipe between real `stdin` and `stdio_server`'s reader.

```
real stdin --> pump thread --> pipe write end --> pipe read end --> stdio_server
```

A daemon "pump" thread copies real stdin into the pipe. `stdio_server` reads only from the pipe's read end. On SIGTERM/SIGINT, we close the pipe's write end, synthesizing EOF for the reader. The reader exits naturally, `run_stdio_async()` returns, `composer.stop()` runs from `run_server`'s `finally` block, `asyncio.run()` completes, `sys.exit(0)` raises `SystemExit`, `ErrorHandledGroup.main()` catches it, `_after_command` fires, `_shutdown_telemetry` flushes and unregisters the OTel atexit handlers, and the process exits cleanly with no `os._exit` on the primary path.

The pump thread is `daemon=True`, so it doesn't block process exit even if it's still blocked in `read(real_stdin)` when the process exits. The OS reaps it.

A safety-net watchdog (`threading.Timer`) starts when a signal arrives. It only fires if the clean shutdown path stalls for some unforeseen reason. In normal operation the process exits well before it expires and the daemon timer dies with it.

The implementation lives in `src/anaconda_mcp/_shutdown.py`.

---

## Why approaches that look simpler do not work

| Approach | Why it fails |
|---|---|
| `os.close(0)` from another thread | Kernel-dependent and unreliable; on Linux/macOS, the in-progress `read(0)` holds a reference to the open file, so closing the fd doesn't reliably interrupt the syscall |
| `os.dup2(/dev/null, 0)` | Updates the fd table only; the in-progress syscall already holds the original `struct file*` |
| `signal.pthread_kill(tid, SIGUSR1)` | Wakes the syscall with EINTR, but Python's I/O layer retries internally on EINTR |
| `ctypes.PyThreadState_SetAsyncExc` | Acts only at Python bytecode boundaries, not inside C-level syscalls |
| `asyncio.wait_for(run_stdio_async(), timeout=N)` | `CancelScope(shield=True)` absorbs the cancellation; the thread keeps running |
| `loop.remove_reader(0)` | anyio uses `to_thread.run_sync`, not `loop.add_reader` — there is no asyncio reader registered |
| `OTEL_SDK_DISABLED=true` | Disables instruments but the atexit handler is still registered (no-op `shutdown` only); does not solve the asyncio loop hang |
| Catching `KeyboardInterrupt` in `ErrorHandledGroup.main()` | Only addresses SIGINT. SIGTERM does not raise `KeyboardInterrupt`. |
| `loop.add_signal_handler` to cancel main task | Overridden by mcp-compose's `signal.signal(...)` call which runs later inside `_serve()` |
| `lifespan=` hook on `FastMCP` | The instance has no `lifespan` kwarg passed; even if it did, `_mcp_server.run()` never exits, so `__aexit__` never fires |

---

## Cross-platform behavior

| Shutdown trigger | Behavior |
|---|---|
| AI client closes child's stdin (canonical MCP shutdown) | Works on Linux/macOS/Windows. Pump's `read(real_stdin)` returns 0, pump exits, pipe write end closes, reader sees EOF, clean unwind. No signal involved. |
| Ctrl+C (SIGINT) in console | Works on Linux/macOS/Windows. mcp-compose registers SIGINT; our patch wraps it. |
| `kill -TERM pid` (Linux/macOS) | Works. Same path as SIGINT. |
| `taskkill /F` on Windows | Unstoppable for any code (`TerminateProcess` bypasses all userspace cleanup). Same as `kill -9` on Unix. mcp-compose already gates SIGTERM registration behind `hasattr(signal, "SIGTERM")`. |

The fix introduces no Windows regressions. mcp-compose's existing `hasattr(signal, "SIGTERM")` guard already handles the Windows limitation, and the canonical MCP shutdown path (client closes stdin) is signal-free and works identically on every platform.

---

## Compatibility

This fix was validated against the following package versions, as pinned in `pyproject.toml`:

| Package | Version constraint |
|---|---|
| `mcp-compose` | `>=0.1.12,<2.0.0` |
| `anaconda-cli-base` | `>=0.9.0,<1.0.0` |
| `anaconda-auth` | `>=0.13.0,<1.0.0` |
| Python | `>=3.10,<3.14` |

The `anyio` version is not pinned directly in `pyproject.toml`. It comes from mcp-compose's transitive dependencies. The private symbol `anyio/_core/_fileio.py:99` was verified against the version of anyio shipped with `mcp-compose` as installed in the `anaconda-mcp-dev` conda env.

---

## Glossary of private symbols patched

The fix monkey-patches three private symbols. All three are imported at module top-level in `_shutdown.py` — `mcp`, `mcp-compose`, and `anaconda-cli-base` are required runtime dependencies declared in `pyproject.toml`, so a missing dependency surfaces immediately as `ImportError` rather than degrading silently.

| Symbol | Provided by | Risk |
|---|---|---|
| `mcp.server.fastmcp.FastMCP.run_stdio_async` | mcp Python SDK | Method name has been stable since the SDK was introduced. Replacing it at the class level is a documented monkey-patch pattern. |
| `mcp_compose.composer._module_signal_handler` | mcp-compose | Underscore-prefixed; a future refactor could rename it. If renamed, `composer_mod._module_signal_handler` raises `AttributeError` at install time (see Failure modes). If mcp-compose ever exposes a public `register_shutdown_hook` API, migrate to that. |
| `anaconda_cli_base.telemetry._shutdown_telemetry` | anaconda-cli-base | Underscore-prefixed; imported at module top-level and called from the safety-net path. If renamed in a future cli-base release, the top-level import fails immediately, blocking `serve` startup — a loud failure preferable to silently losing telemetry flush. The call inside `_safety_net_force_exit` is wrapped in `try/except Exception` so a runtime flush failure (e.g., network timeout) does not prevent `os._exit(0)`. |

The patches must be installed before `mcp_compose.cli.serve_command` runs:

- `FastMCP.run_stdio_async` is replaced at the class level so the `composer.composed_server` instance picks up our version when `await composer.composed_server.run_stdio_async()` is called inside `mcp_compose.cli.run_server`.
- `mcp_compose.composer._module_signal_handler` is replaced at the module level so `signal.signal(SIGTERM, _module_signal_handler)` inside `MCPServerComposer._register_composer` resolves the name to our patched handler at registration time.

---

## Failure modes

**If cli-base renames `_shutdown_telemetry`:** The top-level import in `_shutdown.py` fails with `ImportError`, propagating through `cli.py` and crashing `anaconda mcp serve` at startup. This is a loud failure that surfaces immediately during dependency upgrades, preferable to a silent loss of telemetry flush. Acceptable because cli-base is a required dependency pinned to `>=0.9.0,<1.0.0`.

**If mcp-compose renames `_module_signal_handler`:** The patch in `_patch_composer_signal_handler` raises `AttributeError` at install time (not `ImportError`). The module-level attribute lookup `composer_mod._module_signal_handler` will fail. The signal handler patch becomes a no-op, and the hang returns on SIGTERM/SIGINT. The canonical stdin-close path (AI client closes stdin) still works. This is the highest-risk failure mode; see "When to revisit" below.

**If the pump thread dies unexpectedly:** The pump thread's `finally` block calls `_close_write_end()`. The pipe's write end closes, the reader sees EOF, and `run_stdio_async()` returns. This is a safe failure: the process shuts down cleanly rather than hanging.

---

## Why `os._exit(0)` in the safety net

`os._exit(0)` is a last resort, fired only by the 10-second watchdog timer if the clean shutdown path stalls. It bypasses all atexit handlers and Python teardown, which is exactly what's needed when those handlers are the source of the hang.

The 10-second deadline is chosen to cover:

- `composer.stop()` default process-termination timeout: 5 seconds
- A 2-second daemon-thread bound on `_shutdown_telemetry` (see next section for why this matters more than the SDK's own `timeout_millis` argument)
- Margin for scheduling jitter

`WATCHDOG_DEADLINE_SECS` must not be lowered below 6 seconds. In normal operation the process exits well before the watchdog fires, and the daemon timer dies with it.

---

## Telemetry shutdown timeouts and the `OTEL_EXPORTER_OTLP_TIMEOUT` knob

cli-base's `_shutdown_telemetry()` calls `force_flush(timeout_millis=500)` on each of `TracerProvider`, `MeterProvider`, and `LoggerProvider`. The parameter name suggests a 500 ms ceiling per provider. **It is not.**

Tracing the OTel SDK call chain (`opentelemetry-sdk` 1.x, verified against the version installed by `anaconda-cli-base[telemetry]`):

1. `TracerProvider.force_flush` and `LoggerProvider.force_flush` delegate to `_active_span_processor.force_flush(timeout_millis)`.
2. `BatchSpanProcessor.force_flush` calls `BatchProcessor.force_flush`, whose body is:
   ```python
   def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
       if self._shutdown:
           return False
       # Blocking call to export.
       self._export(BatchExportStrategy.EXPORT_ALL)
       return True
   ```
   The `timeout_millis` parameter is accepted but never consulted. `_export` is a blocking call.
3. `_export` invokes `self._exporter.export(...)` with no timeout argument.
4. The OTLP gRPC exporter then uses its own knob: `OTEL_EXPORTER_OTLP_TIMEOUT` (default **10 seconds**) with `_MAX_RETRYS = 6` and exponential backoff (~50 s cumulative).

`MeterProvider.force_flush` is the only one that even computes a deadline at the provider level, but it still bottoms out in the same `BatchProcessor.force_flush` that ignores `timeout_millis`. The asymmetry is documented here so future maintainers don't generalize from one provider to all three.

**Realistic worst case for `_shutdown_telemetry()` when the OTLP endpoint is unreachable:** roughly 6 retries × 10 s + 50 s backoff ≈ 110 s per provider, ×3 providers ≈ 330 s. Without an external bound, that is enough to make `anaconda mcp serve` look completely wedged after SIGTERM.

This is the reason `_safety_net_force_exit` runs `_shutdown_telemetry()` on a daemon thread with a hard `join(timeout=2.0)` rather than calling it directly. The watchdog's whole purpose is to escape exactly the stall it would otherwise re-enter.

### Tuning knobs available to users

If the clean shutdown path (which runs `_shutdown_telemetry()` from `_after_command` BEFORE the watchdog ever fires) is too slow on your network, two environment variables help:

| Variable | Effect |
|---|---|
| `OTEL_EXPORTER_OTLP_TIMEOUT=1` | Reduces per-attempt OTLP gRPC timeout from 10 s to 1 s. Retries and backoff still apply, so worst case is ~6 s per provider plus backoff, not zero. |
| `OTEL_SDK_DISABLED=true` | Disables the OTel SDK entirely. Snake-eyes still fires; nothing goes through OTLP. Eliminates the stall surface completely at the cost of losing OTel signals. |

The 2-second daemon-thread bound inside `_safety_net_force_exit` is fixed in code; users cannot tune it. If a future change demands tuning, the constant lives near the top of `_shutdown.py`.

---

## When to revisit

Two upstream changes would make this module simpler or obsolete:

1. **mcp-compose exposes a public `register_shutdown_hook` API.** The current patch of `_module_signal_handler` could be replaced with a supported call. This would eliminate the private-symbol risk for the signal handler.

2. **mcp exposes a public `lifespan` hook that fires on SIGTERM.** The current patch of `FastMCP.run_stdio_async` could be replaced with a supported lifecycle callback. This would eliminate the class-level monkey-patch entirely.

Until either of those exists, the private-symbol patches are the only reliable approach.

---

## Smoke test

A full verification recipe, including a reference smoke-test script, lives in `.omo/handoff.md` (lines 754-880). The script spawns `anaconda mcp serve`, waits for startup, sends SIGTERM, and asserts the process exits within 5 seconds with exit code 0.

Expected results:

- **Without the fix:** process hangs more than 30 seconds after SIGTERM, requires SIGKILL.
- **With the fix:** process exits in under 1 second. Exit code is 0, via `SystemExit` raised by `sys.exit(_serve(ns))`, caught by `ErrorHandledGroup.main`, with `_after_command` firing cleanly.
- The 10-second safety-net watchdog should not fire under normal conditions.

The smoke test requires a conda env with `anaconda-cli-base >= 0.9.0`, a dev install of `anaconda-mcp` (`pip install -e .`), a logged-in user (`anaconda login`), and network reachability to validate the auth token.

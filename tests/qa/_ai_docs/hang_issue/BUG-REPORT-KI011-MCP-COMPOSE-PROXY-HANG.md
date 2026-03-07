# Chat Session Freezes After a Tool Error with No Recovery

**Component**: `mcp-compose`
**Severity**: High — requires process restart to recover
**Reproducibility**: Deterministic
**Reported**: 2026-03-06

---

## Summary

When a user triggers a tool error — for example, installing a package into a
non-existent environment — using Cursor or Claude Code over HTTP transport, the chat
session may freeze indefinitely. The client shows "Generating…" with no error message.
Starting a new chat session does not help. Only restarting `mcp-compose` restores
normal operation.

The root cause is in `mcp-compose`'s internal proxy: under certain timing conditions
it silently drops the tool result and holds the upstream connection open indefinitely,
corrupting the process-wide connection pool.

---

## Environment

| | |
|---|---|
| OS | macOS 15.3, arm64 |
| `anaconda-mcp` | 1.0.0.rc.1 |
| `environments-mcp-server` | 1.0.0.rc.1 |
| Server Python | 3.10, 3.12, 3.13 |
| AI clients | Cursor, Claude Code |
| Transport | Streamable HTTP (port 8888), STDIO |

---

## Found In: E2E Testing

Observed across multiple QA runs. After a tool call returned an error, clients froze
with no error message and no way to recover short of a server restart.

| Client | Transport | Python | Hangs? | Observed |
|--------|-----------|--------|--------|----------|
| Cursor | Streamable HTTP | 3.13 | **Yes** | 2026-03-05 |
| Claude Code (`--http`) | Streamable HTTP | 3.10 | **Yes** | 2026-03-05 |
| Cursor | STDIO | 3.12 | **Yes** | 2026-03-06 |
| Claude Desktop | STDIO | — | No | — |

---

## Steps to Reproduce

**Setup** — follow [QUICK_START.md](../QUICK_START.md) HTTP transport section:

1. Create the RC environment and start the HTTP server:
   ```bash
   conda activate anaconda-mcp-rc-py313
   ./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
   ```

2. Configure your client ([QUICK_START.md — Configure client](../QUICK_START.md#http-transport)):
   - **Cursor**: add `http://localhost:8888/mcp` to `~/.cursor/mcp.json`, restart Cursor
   - **Claude Code**: `claude mcp add --transport http anaconda-mcp http://localhost:8888/mcp`

**Trigger the hang**

3. Open a new chat session and ask the AI to install a package into a non-existent
   environment — for example:
   > *"Install numpy into /tmp/nonexistent-env"*

4. Repeat the same request several times in quick succession (3–5 times).

## Expected

Each request completes with a clear error message (environment not found) within a
few seconds. The chat session remains responsive.

## Actual

After a few repetitions the client stops responding — it shows "Generating…"
indefinitely. No error is surfaced. Opening a new chat session in the same client
also hangs. Only restarting the `mcp-compose` server restores normal operation.

**To reproduce programmatically** (no AI client required):

```bash
conda activate anaconda-mcp-qa
python -m pytest tests/qa/http_tools/test_guard_proxy_error_hang.py \
    -k test_hang_002 -v -s --start-server
```

The hang triggers deterministically at iteration 4 of 20 and fails with a 60-second
timeout.

---

## What Lower-Level Testing Shows

The regression test suite (`tests/qa/http_tools/`, `tests/qa/stdio_tools/`) reproduces
the hang programmatically and confirms:

- The hang is **deterministic**: triggers at iteration 4 over HTTP, iteration 16 over STDIO
- The hang is **not upstream-transport-dependent** — the same internal race fires whether
  the AI client uses HTTP or STDIO
- The corruption is **process-wide**: a new chat session does not recover; only a restart does
- `environments_mcp_server` responds correctly in all cases — the bug is exclusively in
  `mcp-compose`'s internal proxy

See [KI-011-HTTP-PROXY-HANG.md](./KI-011-HTTP-PROXY-HANG.md) for the full technical
investigation, protocol flow diagrams, and fix plan.

---

## Root Cause

`mcp-compose` expects tool results from the downstream server to arrive on the SSE
stream. Under certain timing conditions the downstream server returns the result inline
in the `tools/call` POST body (HTTP 200 OK) instead. `mcp-compose` does not handle
the inline case — the result is dropped, the upstream connection is held open while the
proxy waits for a result that was already delivered, and the internal HTTP connection
pool slot is never released, blocking all subsequent calls process-wide.

The inline path is triggered specifically by error-path calls because
`environments_mcp_server` returns error results synchronously (no async work before
returning), causing FastMCP to serve them inline in the 200 OK body rather than via
SSE. Success-path calls await long-running conda operations, so FastMCP issues 202
Accepted and uses SSE — the path `mcp-compose` handles correctly.

---

## Impact

| Scenario | Impact |
|---|---|
| Call that triggers the hang | Hangs indefinitely |
| All subsequent calls | Also hang — process-wide |
| AI client | Shows "Generating…" indefinitely; no error surfaced |
| New chat session | Does not recover |
| Recovery | `mcp-compose` process restart required |

---

## Suggested Fix

In `mcp-compose`: when `tools/call` returns HTTP 200 OK, read and forward the inline
response body instead of waiting on the SSE stream. Add a defensive timeout on the SSE
read loop as a second line of defence.

See [KI-011-HTTP-PROXY-HANG.md — Fix Plan](./KI-011-HTTP-PROXY-HANG.md#fix-plan) for
implementation details.

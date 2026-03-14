# KI-019: After First-Call Hang on Windows, Retry Also Fails When User Is Logged In

**Component**: `environments_mcp_server` / `anaconda_mcp` auth/telemetry
**Affected version**: `1.0.0.rc.1`
**Severity**: High
**Platform**: Windows only
**Transport**: stdio (Claude Desktop / Cursor MCP)
**Auth state**: Logged in (Anaconda account, telemetry initialized)
**Jira**: [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386)

---

## Summary

When the user is logged in to Anaconda, the first `conda_list_environments` call hangs (same as KI-018). Unlike the logged-out case where a retry succeeds in ~2 seconds, the retry **also fails** with `unhandled errors in a TaskGroup`. Both calls fail and the LLM receives no result.

The additional failure is caused by telemetry initialization: when telemetry is active, something in the auth/telemetry path during the tool call leaves `environments_mcp_server` in a degraded state after the GET SSE stream disconnects and reconnects. The logged-out path skips this work and recovers cleanly.

---

## Environment

| | Value |
|---|---|
| OS | Windows 11 |
| MCP transport | stdio (via `mcp-compose` / `anaconda_mcp serve --delay 5`) |
| Client | Claude Desktop / Cursor MCP |
| `anaconda_mcp` version | `1.0.0.rc.1` |
| MCP protocol `serverInfo.version` | `1.26.0` (reported by `mcp-compose` in handshake — `mcp` SDK version, not package version) |
| `environments_mcp_server` | auto-started on port 4041 |
| Auth state | Logged in — `Initializing telemetry` on startup (token cached) |
| Conda | Miniconda3 at `C:\Users\JuliaIliukhina\miniconda3` |

---

## Steps to Reproduce

1. On a Windows machine, install `anaconda_mcp` and configure Claude Desktop or Cursor MCP with stdio transport (`python -m anaconda_mcp serve --delay 5`)
2. Log in to Anaconda (browser login, token cached before opening Claude Desktop)
3. Kill any leftover `environments_mcp_server` processes on port 4041 (see KI-017)
4. Open Claude Desktop / Cursor
5. Wait for anaconda-mcp to show as connected (~13 seconds)
6. Send: `use 'anaconda-mcp' tools, list conda environments`
7. When it fails (after ~4 minutes), send: `try again`

---

## Observed Results

### First call — hangs, result lost (same as KI-018)

```
18:54:45  Processing request of type CallToolRequest
18:54:45  POST http://localhost:4041/mcp → 200 OK        ← session created
18:54:46  GET  http://localhost:4041/mcp → 200 OK        ← SSE stream opened
18:54:46  POST http://localhost:4041/mcp → 202 Accepted
18:54:46  POST http://localhost:4041/mcp → 200 OK
18:55:16  GET stream disconnected, reconnecting in 1000ms ← 30s SSE timeout
18:55:47  GET  http://localhost:4041/mcp → 200 OK        ← stream reconnected
22:58:45  notifications/cancelled: MCP error -32001: Request timed out
18:58:45  Request 4 cancelled - duplicate response suppressed
```

LLM response:
> *"It seems the Anaconda MCP tool didn't return a result"*

### Retry — also fails with TaskGroup error (30 seconds)

```
18:59:24  Processing request of type CallToolRequest   ← retry dispatched
22:59:54  {"id":5,"result":{"content":[{"type":"text","text":
          "Error executing tool conda_list_environments:
          unhandled errors in a TaskGroup (1 sub-exception)"}],
          "isError":true}}
```

LLM response:
> *"The tool is returning an error again — this appears to be a connection or server-side issue"*

No environments listed. Session is stuck — no subsequent retry will succeed without restarting the server.

---

## Measurements

| | Logged out (KI-018) | Logged in (this bug) |
|---|---|---|
| Auth on startup | `Starting Anaconda login in background` → timeout | `Initializing telemetry` ✓ |
| First call | Hang → `duplicate response suppressed` | Hang → `duplicate response suppressed` |
| Retry | **Succeeded in ~2 seconds** | **Failed: `unhandled errors in a TaskGroup`** |
| Session usable after? | Yes | No — server degraded |

**Reproducibility**: 100% across Sessions 3 and 4 (both logged-in, clean process state). Sessions 1 and 5 (logged out) both recovered successfully on retry — confirming the auth state is the distinguishing variable.

Controlled comparison (Sessions 3 and 4 vs Sessions 1 and 5):
- Same code version, same transport, same `mcp-compose` config
- Same first-call hang behavior
- Only variable: whether `Initializing telemetry` fires at startup
- Sessions with `Initializing telemetry`: retry always fails
- Sessions without: retry always succeeds

---

## Expected Result

- First call: same behavior as KI-018 (hang on cold start — tracked separately)
- Retry: succeeds in ~2 seconds and returns the list of environments, regardless of auth/telemetry state

---

## Root Cause

**First call hang**: identical to KI-018 — Windows cold-start overhead makes the first conda call exceed the 30-second SSE timeout.

**Retry failure (this bug)**: when telemetry is initialized (`Initializing telemetry`), `anaconda_mcp` performs additional background work on each tool call — likely token validation, telemetry event dispatch, or credential refresh. After the GET SSE stream disconnects and reconnects (the 30-second timeout cycle), this background work encounters an unhandled error that propagates as an `unhandled errors in a TaskGroup` exception in `environments_mcp_server`'s async task group.

When not authenticated, this background work is skipped (no token, no telemetry events), so the server's async task group is not corrupted by the stream disconnect cycle, and the retry goes through cleanly.

**Hypothesis to verify**: the telemetry-related async task that runs during a tool call does not handle session invalidation (caused by the GET stream cycling to a new session ID). When the session changes mid-call, the telemetry task fails without being caught, poisoning the task group.

---

## Fix

Two separate fixes needed:

1. **Fix KI-018 first** (pre-warm conda at startup): eliminates the first-call hang, which is the trigger for this bug. If the first call succeeds, the GET stream never cycles and the task group is never corrupted.

2. **Fix telemetry error handling in `anaconda_mcp`**: the telemetry/auth background task running during tool calls must handle session invalidation gracefully — catch exceptions and degrade silently rather than propagating to the task group. This makes the system resilient even if the first-call hang is not fully fixed.

---

## Related

- **KI-018**: root cause of the first-call hang that triggers this bug — fix KI-018 to eliminate the trigger
- **KI-014**: auth/telemetry initialization behavior (browser opens on startup, 60s timeout when not logged in)
- **KI-015**: `unhandled errors in a TaskGroup` in a different context (`logger.exception()` — different trigger, same exception type)
- **KI-011 / KI-013**: proxy response-loss mechanism (`duplicate response suppressed`)

---

## Evidence Files

| File | Description |
|---|---|
| `mcp_server_loggedin_before_2.log` | Session 3: logged in, stale procs killed — first clean logged-in reproduction |
| `mcp_server_loggedin_3.log` | Session 4: logged in, clean start — confirms Session 3 result |
| `mcp_server_loggedout_2.log` | Session 5: logged out — retry succeeds, confirming auth state is the variable |

# KI-018: First `conda_list_environments` Call Always Hangs on Windows (Cold-Start Timeout)

**Component**: `environments_mcp_server`
**Affected version**: `1.0.0.rc.1`
**Severity**: High
**Platform**: Windows only (not reproducible on macOS — see Measurements)
**Transport**: stdio (Claude Desktop / Cursor MCP)
**Auth state**: Logged out (no Anaconda account / telemetry not initialized)
**Jira**: [DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385)

---

## Summary

On Windows, the first `conda_list_environments` tool call after server startup always hangs and returns no result to the LLM. The server does compute the result — it arrives after the 30-second SSE stream timeout has already fired and the response is discarded. A retry of the same call succeeds in ~2 seconds.

The root cause is that `environments_mcp_server` does not pre-warm conda at startup. On Windows, the first conda invocation pays a cold-start cost (DLL loading, Windows Defender scanning, batch script activation) that exceeds the 30-second GET SSE stream timeout. On macOS the identical call completes in under 1 second.

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
| Auth state | Logged out — `Starting Anaconda login in background` → timed out after 60s |
| Conda | Miniconda3 at `C:\Users\JuliaIliukhina\miniconda3` |

---

## Steps to Reproduce

1. On a Windows machine, install `anaconda_mcp` and configure Claude Desktop or Cursor MCP with stdio transport (`python -m anaconda_mcp serve --delay 5`)
2. Ensure the user is **not** logged in to Anaconda (or log out)
3. Kill any leftover `environments_mcp_server` processes on port 4041 (see KI-017)
4. Open Claude Desktop / Cursor
5. Wait for anaconda-mcp to show as connected (~13 seconds)
6. Send: `use 'anaconda-mcp' tools, list conda environments`

---

## Observed Results

### First call — hangs, result lost

The LLM waits 4 minutes then reports no result:

> *"It seems the anaconda-mcp tool didn't return any results"*

**Server log sequence:**
```
18:46:25  Processing request of type CallToolRequest
18:46:26  POST http://localhost:4041/mcp → 200 OK        ← session created
18:46:26  GET  http://localhost:4041/mcp → 200 OK        ← SSE stream opened
18:46:26  POST http://localhost:4041/mcp → 202 Accepted  ← tool call dispatched
18:46:26  POST http://localhost:4041/mcp → 200 OK        ← downstream accepted
18:46:56  GET stream disconnected, reconnecting in 1000ms ← 30s SSE timeout fires
18:47:27  GET  http://localhost:4041/mcp → 200 OK        ← stream reconnected
22:50:25  notifications/cancelled: MCP error -32001: Request timed out  ← Claude 4-min timeout
18:50:25  Request 4 cancelled - duplicate response suppressed  ← result arrived but discarded
```

The critical line: **`duplicate response suppressed`** — `environments_mcp_server` did compute and return the result, but the GET SSE stream had already cycled to a new connection, so `mcp-compose` discarded it.

### Retry — succeeds in ~2 seconds

```
18:51:02  Processing request of type CallToolRequest
18:51:03  POST → 200 OK, GET → 200 OK, POST → 202, POST → 200 OK (result), DELETE → 200 OK
22:51:04  Result returned: 4 environments listed
```

---

## Measurements

| Metric | Windows | macOS |
|---|---|---|
| First call duration | **>30 seconds (timeout)** | **<1 second** |
| GET stream drop | At exactly 30s | Never |
| Retry duration | ~2 seconds | N/A (no hang) |
| Total time to first successful result | ~4–5 minutes | <1 second |

**macOS comparison**: tested on 2026-03-11 with identical setup — same code version, same stdio transport, same `mcp-compose` config, same `--delay 5` flag, fresh cold start. macOS first call completed in <1 second with no GET stream disconnect. This confirms the issue is Windows-specific.

**Reproducibility**: 100% — observed in every Windows session across Sessions 1 and 5 (logged-out sessions).

---

## Expected Result

First `conda_list_environments` call completes in under 5 seconds and returns the list of environments. The LLM receives the result on the first attempt without any hang or retry needed.

---

## Root Cause

`environments_mcp_server` starts, registers its tools, then sits idle. No conda code runs until the first tool call arrives. On Windows, that first call pays the full cold-start cost inside the request window:

1. **Windows Defender real-time scanning**: scans Python DLLs, bytecache files, and conda package metadata on first invocation — adds 15–30 seconds
2. **DLL loading**: Python loads many DLLs on first import on Windows; significantly slower than macOS dylib loading
3. **Conda activation overhead**: conda activation on Windows runs through batch scripts and PowerShell, sets dozens of environment variables via `cmd.exe` — much slower than the macOS shell equivalent

Total cold-start cost on Windows: **>30 seconds**, which exceeds the `mcp.client.streamable_http` GET SSE stream timeout.

On macOS, the same cold-start completes in <1 second because dylib loading is faster, no Defender scanning, and conda activation is a simpler shell operation.

The existing `--delay 5` flag delays `mcp-compose` startup but does not warm up conda — it does not help with this issue.

---

## Fix

Pre-warm conda in `environments_mcp_server` during server startup, before any tool call arrives. A lightweight conda invocation (e.g. `conda info` or importing conda internals) at init time would pay the cold-start cost once at startup rather than during the first user request. After warm-up, all subsequent calls complete in <2 seconds on Windows.

---

## Related

- **KI-019**: When the user is logged in (telemetry initialized), the retry after this hang also fails — see KI-019
- **KI-017**: Stale `environments_mcp_server` process on port 4041 after Claude Desktop closes on Windows
- **KI-014**: Anaconda login initiated on every startup without user request; telemetry uninitialized when skipped
- **KI-011 / KI-013**: Mac-side proxy response-loss and delay issues (same `duplicate response suppressed` mechanism, different trigger)

---

## Evidence Files

| File | Description |
|---|---|
| `mcp_server_loggedout_2.log` | Primary reproduction: logged out, stale processes killed before start — clean, unambiguous |
| `macos_loggedin.log` | macOS comparison: identical setup, first call <1s, no hang |

# Bug Report: mcp-compose Streamable HTTP Proxy Hangs Permanently After Tool Error

**Component**: `mcp-compose` — Streamable HTTP proxy
**Severity**: High — requires server process restart to recover; no automatic recovery
**Reproducibility**: Consistent — triggers at the 4th rapid sequential call in every test run
**First observed**: 2026-03-05, internal testing, macOS
**Reported**: 2026-03-06

---

## Summary

When `mcp-compose` proxies a tool call to a downstream Streamable HTTP server
(`environments_mcp_server`), a sequential series of rapid calls eventually causes the
proxy to abandon the downstream backend session without forwarding the result. The upstream
connection stays open indefinitely — for Streamable HTTP upstream clients it keeps sending
SSE keepalive bytes; for STDIO upstream clients it never writes to stdout. The entire
`mcp-compose` process becomes permanently unresponsive — no subsequent tool calls on any
session can complete until the process is restarted.

**STDIO negative-control test result (2026-03-06):** The hang is **not** upstream-transport-
dependent. STDIO-HANG-001 completed iterations 1–15 successfully, then hung at iteration 16.
The race condition lives in `mcp-compose`'s **internal** Streamable HTTP pool to
`environments_mcp_server` (port 4042), which is always HTTP regardless of how the external
client connects.

---

## Environment

| Item | Value |
|---|---|
| OS | macOS 15.3, arm64 |
| Python | 3.13 (server), 3.14 (test client) |
| `mcp-compose` | 0.1.10 |
| `environments_mcp_server` | version in `anaconda-mcp-rc-py313` conda environment |
| Transport | Streamable HTTP (SSE), port 8888 → port 4041 |
| Python MCP SDK | `mcp` (python-sdk), version negotiated `2025-11-25` |

---

## Steps to Reproduce

### Setup

```bash
# Terminal 1 — start the server
conda activate anaconda-mcp-rc-py313
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888

# Terminal 2 — run the test
conda activate anaconda-mcp-qa
python -m pytest tests/qa/http_tools/test_guard_proxy_error_hang.py \
    -k test_hang_002 -v
```

### What the test does

`test_hang_002_install_into_nonexistent_env_does_not_hang` calls
`conda_install_packages` with a prefix that does not exist
(`/tmp/nonexistent-conda-env-xyz123`) in a loop of 20 iterations. Each call should
return `isError: true` within a few seconds. A SIGALRM-based 60-second timer
interrupts any call that does not complete.

### Observed behaviour

Iterations 1–3 complete immediately (< 1 second each). Iteration 4 hangs for exactly
60 seconds until the SIGALRM fires, then fails with:

```
httpx.ReadTimeout: _call_tool: no complete response within 60s
(SIGALRM fired after 60.0s — likely an SSE-keepalive hang, KI-011)
```

After that, any further call to any tool on any session also hangs until the server
process is restarted.

---

## Expected Result

Every call returns `{"is_error": true, ...}` within a few seconds, regardless of
iteration number. The server remains responsive after the call completes.

## Actual Result

The 4th call hangs indefinitely. The server never writes a response body to the
upstream connection. After the hang, the server is permanently unresponsive to all
further tool calls until the process is restarted.

---

## Server-Side Evidence

The `start-http-server.sh` server log shows the following pattern for the hanging
call (mcp-compose → `environments_mcp_server` :4041):

**Normal call** (iterations 1–3) — 5 requests + DELETE:
```
POST http://localhost:4041/mcp  200 OK    ← create session
POST http://localhost:4041/mcp  202 Acc.  ← initialize
GET  http://localhost:4041/mcp  200 OK    ← open SSE stream
POST http://localhost:4041/mcp  200 OK    ← tools/call request
POST http://localhost:4041/mcp  200 OK    ← session close
DELETE http://localhost:4041/mcp 200 OK   ← delete session
```

**Hanging call** (iteration 4) — 4 requests, no DELETE:
```
POST http://localhost:4041/mcp  200 OK    ← create session
GET  http://localhost:4041/mcp  200 OK    ← SSE stream opened BEFORE initialize
POST http://localhost:4041/mcp  202 Acc.  ← initialize
POST http://localhost:4041/mcp  200 OK    ← tools/call returns result INLINE
[no 5th POST, no DELETE — session abandoned]
```

The downstream server (`environments_mcp_server`) responded correctly in all cases.
The result for the hanging call was delivered inline in the `tools/call` POST body
(HTTP 200 OK with JSON body). The proxy did not forward it.

**Uvicorn log** for the hanging upstream connection:
```
127.0.0.1:XXXXX - "POST /mcp HTTP/1.1" 200 OK
```
The `200 OK` here reflects that response headers were sent. The response body
(the SSE stream) was never closed — the connection stayed open streaming keepalive
bytes (`:\n\n`) until the client's 60-second timer fired.

---

## Impact

| Scenario | Impact |
|---|---|
| Tool call that triggers the hang | Hangs indefinitely; client session appears frozen |
| All subsequent tool calls | Also hang — process-level corruption |
| AI client sessions (Cursor, Claude Code) | Show "Generating…" indefinitely |
| Recovery | Requires `mcp-compose` process restart |
| New chat sessions (without restart) | Do not recover — corruption is process-wide |

Confirmed affected AI clients: **Cursor** (Streamable HTTP transport) and
**Claude Code** (with `--http` flag). Both hang for the same reason: they receive the
HTTP 200 OK headers from `mcp-compose` but the response body is never written.

**Update after STDIO tests with function-scoped fixture (2026-03-06, Run 6):**
Claude Desktop uses STDIO transport to `mcp-compose`. With each test getting its own
fresh `mcp-compose` process:

- `conda_remove_environment` error path (**STDIO-HANG-001**): **PASSED** all 20 iterations — no hang over STDIO for this tool
- `conda_install_packages` error path (**STDIO-HANG-002**): **FAILED** at iteration 16/20 — hang confirmed
- Warm-up + error+health cycle (**STDIO-HANG-003**): **FAILED** at iteration 20/20 health step — 20 warm-up calls + 19 complete error+health cycles succeeded; the 20th `list_environments` call following an error timed out

The hang is tool-path-dependent over STDIO. Claude Desktop is more resilient for
`remove_environment` (never hangs in 20 iterations) but still affected by
`install_packages` (hangs at iteration 16). The internal proxy corruption accumulates
and eventually surfaces regardless of upstream transport.

---

## Reproduction Frequency

Across four HTTP test runs and two STDIO test runs on 2026-03-06:

| Run | Suite | Upstream transport | Test | Result | Hang at iteration |
|---|---|---|---|---|---|
| 1–4 | `http_tools` HANG-001 | Streamable HTTP | `remove_environment` × 20 | **FAILED** | 4/20 |
| 1–4 | `http_tools` HANG-002 | Streamable HTTP | `install_packages` × 20 | **FAILED** | 4/20 |
| 5 | `stdio_tools` STDIO-HANG-001 (module-scoped) | STDIO | `install_packages` × 20 | **FAILED** | 16/20 |
| 5 | `stdio_tools` STDIO-HANG-002 (module-scoped) | STDIO | `remove_environment` × 20 | **FAILED** | 1/20 (cascade) |
| 6 | `stdio_tools` STDIO-HANG-001 (function-scoped) | STDIO | `remove_environment` × 20 | **PASSED** | — |
| 6 | `stdio_tools` STDIO-HANG-002 (function-scoped) | STDIO | `install_packages` × 20 | **FAILED** | 16/20 |
| 6 | `stdio_tools` STDIO-HANG-003 (function-scoped) | STDIO | warm-up × 20 + (error+health) × 20 | **FAILED** | health step 20/20 |

Run 5 used a module-scoped subprocess (shared across tests); cascade failures inflated the count.
Run 6 uses function-scoped fixtures (fresh process per test) for clean isolation.

Key observations:
- Over HTTP: both error paths hang at iteration **4**
- Over STDIO: `remove_environment` path does **not** hang in 20 iterations; `install_packages` hangs at **16**
- HANG-003 (STDIO): accumulated state from error calls eventually corrupts the internal pool — the 20th health call timed out even though the error call itself did not hang (failure mode 2)

**Note on Run 4 (`--start-server`)**: This is the test suite's Option B mode, where
the pytest session itself starts and stops `mcp-compose` automatically via
`start-http-server.sh`. The transport is still Streamable HTTP in this mode — the
`--start-server` flag only automates server lifecycle management; it does not change
the transport layer. The test client always connects to `mcp-compose` over HTTP
(`http://localhost:8888/mcp`). STDIO transport is not available in this test suite:
it would require the test process to spawn `mcp-compose` as a subprocess and pipe
stdin/stdout directly — a fundamentally different architecture.

The identical failure in both modes confirms that the hang is in `mcp-compose`'s
internal HTTP proxy logic, not in any external startup or configuration factor.

---

## STDIO Transport — Negative Control

A STDIO test suite (`tests/qa/stdio_tools/`) was created to determine whether the hang
is gated on the upstream transport or lives in `mcp-compose`'s internal proxy logic.

**Architecture under test:**

```
test process  --stdin/stdout pipe-->  mcp-compose (STDIO upstream)
                                              │
                                    Streamable HTTP (port 4042)
                                              │
                                    environments_mcp_server
```

The internal path from `mcp-compose` to `environments_mcp_server` is **identical** to
the HTTP tests — Streamable HTTP, auto-started subprocess, same proxy code. Only the
upstream transport (test process → mcp-compose) differs.

**Run command** (no pre-started server required — test manages its own subprocess):

```bash
conda activate anaconda-mcp-qa
python -m pytest tests/qa/stdio_tools/ -v -s
```

### STDIO Test Results (2026-03-06, Run 6 — function-scoped fixture)

Each test spawns a fresh `mcp-compose` process; results are fully independent.

| Test | Tool(s) | Result | Detail |
|---|---|---|---|
| STDIO-HANG-001 | `conda_remove_environment` × 20 | **PASSED** | All 20 iterations returned in < 2 s |
| STDIO-HANG-002 | `conda_install_packages` × 20 | **FAILED** | Hung at iteration **16/20** |
| STDIO-HANG-003 | warm-up (list × 20) + (remove+list) × 20 | **FAILED** | Health step timed out at iteration **20/20** |

**HANG-003 detail:** Phase 1 (20 × `list_environments`) and 19 full Phase 2 cycles all
completed without a hang. On the 20th iteration, the error step (`remove_environment`)
succeeded, but the immediately following `list_environments` health check timed out.
This is failure mode 2: the proxy corrupted its internal state while forwarding an
error, causing the next call to block — even though the error call itself returned.

**Interpretation:** The race condition is **not** upstream-transport-dependent, but
it is **tool-path-dependent**. The `conda_remove_environment` error path is more
resilient over STDIO (no hang in 20 standalone iterations) while `conda_install_packages`
still hangs at iteration 16. Both paths can eventually corrupt the internal pool when
combined with accumulated state (HANG-003).

STDIO Note — response format difference discovered:

Over STDIO, `mcp-compose` encodes a tool error as:
```json
{"result": {"isError": false, "content": [{"type": "text", "text": "{\"is_error\":true,...}"}]}}
```

Over HTTP, the same error arrives as:
```json
{"result": {"isError": true, "content": [{"type": "text", "text": "{\"is_error\":true,...}"}]}}
```

The outer `isError` flag is `false` in STDIO mode — `mcp-compose` wraps the backend
error as a "successful" tool result containing an error payload string. This is a
separate, lower-severity issue (incorrect `isError` propagation) distinct from KI-011.

---

## Root Cause (observed, confirmed by STDIO test)

In the hanging call, `mcp-compose` opened the SSE GET stream to `:4041` **before**
sending the initialize POST. Because the GET stream was already established when
`tools/call` was sent, `environments_mcp_server` delivered the result inline in the
POST response body (HTTP 200 OK) rather than via the SSE stream. `mcp-compose` was
listening for the result on the SSE stream and did not read the inline POST body.
The result was silently dropped. `mcp-compose` kept the upstream connection open
and continued sending SSE keepalive bytes while waiting for a result that was already
delivered.

This is visible from the GET/POST order in the `:4041` log:
- Normal: `POST (create) → POST (initialize) → GET (SSE) → POST (tools/call)`
- Hanging: `POST (create) → GET (SSE) → POST (initialize) → POST (tools/call)`

**Confirmed by STDIO test (2026-03-06):** The STDIO negative-control test reproduced the
same hang at iteration 16/20, proving the race condition is in `mcp-compose`'s internal
HTTP pool to `:4042`, not in the upstream transport handler. The pool accumulates corrupted
state across calls; HTTP mode enters the bad state at iteration 4, STDIO mode at iteration 16,
suggesting the upstream transport affects the timing or frequency of the internal GET/POST
race but not whether it occurs.

---

## Cursor Client Behaviour After Server Shutdown

When Run 4 (`--start-server`) completed, the pytest session sent SIGTERM to the
auto-started `mcp-compose` process. Cursor had its MCP configuration pointing to
`http://localhost:8888/mcp` and immediately began retrying:

```
[info]  Creating streamableHttp transport
[info]  Connecting to streamableHttp server
[error] Client error for command fetch failed
[warning] Retryable network error, scheduling reconnect: fetch failed
[warning] Error connecting to streamableHttp server, falling back to SSE: fetch failed
[error] SSE error: TypeError: fetch failed: connect ECONNREFUSED 127.0.0.1:8888
[warning] Reconnect attempt N failed: ...
[info]  Scheduling reconnect in Xms (attempt N/15)
```

Cursor retried 15 times with exponential backoff, then switched to periodic retries
every ~19 seconds. This is expected Cursor behaviour when the MCP server is
unavailable — it is not caused by or related to the HANG-002 failure. It does,
however, confirm that Cursor connects to `mcp-compose` exclusively via Streamable
HTTP (it tries Streamable HTTP first, falls back to SSE, and has no STDIO fallback
for HTTP-configured servers).

---

## Diagnostic Artifacts

All artifacts are in `tests/qa/_ai_docs/`:

| File | Contents |
|---|---|
| `BUG-REPORT-KI011-MCP-COMPOSE-PROXY-HANG.md` | This document |
| `KI-011-HTTP-PROXY-HANG.md` | Full investigation log with server logs, evidence table, protocol flow diagrams, and fix plan |
| `tests/qa/http_tools/test_guard_proxy_error_hang.py` | Automated regression test — HANG-001, HANG-002, HANG-003 (HTTP transport) |
| `tests/qa/stdio_tools/test_guard_proxy_error_hang_stdio.py` | Negative-control test — STDIO-HANG-001, STDIO-HANG-002 (STDIO transport; expected PASS) |
| `tests/qa/http_tools/common/utils/mcp_client.py` | Test HTTP client with SIGALRM-based timeout to detect SSE-keepalive hangs |

---

## Suggested Fix

`mcp-compose` should not open the SSE GET stream to the downstream server until
after the initialize POST completes. Additionally, when a `tools/call` POST returns
HTTP 200 OK (inline result), the proxy must read and forward that inline result rather
than waiting on the SSE stream.

A defensive timeout on the SSE read loop would prevent the upstream connection from
being held open indefinitely if the result is missed:

```python
# mcp-compose tool_proxy.py (sketch)
async with asyncio.timeout(180):
    async for event in backend_sse_stream:
        yield event
```

See `KI-011-HTTP-PROXY-HANG.md` section 9 for a detailed fix plan.

---

## Test Command to Reproduce

**Option A — manual server start (two terminals):**

```bash
# Terminal 1 — start a fresh server
conda activate anaconda-mcp-rc-py313
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888

# Terminal 2 — run the reproducer
conda activate anaconda-mcp-qa
python -m pytest tests/qa/http_tools/test_guard_proxy_error_hang.py \
    -k test_hang_002 -v -s
```

**Option B — auto-start server (single terminal):**

```bash
conda activate anaconda-mcp-qa
python -m pytest tests/qa/http_tools/test_guard_proxy_error_hang.py \
    -k test_hang_002 -v -s --start-server
```

Both options use Streamable HTTP transport and produce identical failures.

Expected output on a **buggy** build:
```
FAILED ... test_hang_002_install_into_nonexistent_env_does_not_hang
Failed: HANG-002: conda_install_packages hung for > 60s. ... iteration 4/20
```

Expected output after the **fix**:
```
PASSED ... test_hang_002_install_into_nonexistent_env_does_not_hang
```

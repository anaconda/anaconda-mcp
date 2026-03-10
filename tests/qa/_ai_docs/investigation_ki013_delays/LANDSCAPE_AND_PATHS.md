# KI-011/KI-013 Investigation: Landscape and Potential Paths

**Date**: 2026-03-10
**Status**: Active Investigation
**Last Updated**: 2026-03-10 — Phase 4: Confirmed delays do NOT prevent hang

---

## Executive Summary

After extensive investigation, we've identified that MCP tool call hangs (KI-011) and delays (KI-013) are caused by connection pool/SSE stream management issues in the `mcp-compose` proxy layer. The fix in mcp-compose 0.1.11 (PR #28) improved but did not fully resolve the issue.

**Key Finding**: The downstream server (`environments_mcp_server`) sends HTTP 200 OK with `text/event-stream` headers but fails to write SSE body after ~16-17 rapid sequential calls. The client waits 60 seconds with 0 events before timing out.

---

## System Landscape

### Component Architecture

```
┌─────────────────┐     HTTP      ┌─────────────────┐     HTTP      ┌──────────────────────┐
│   Test Client   │ ──────────►  │   mcp-compose   │ ──────────►  │ environments_mcp_server │
│  (pytest/curl)  │   :8888      │    (proxy)      │   :4041      │   (FastMCP/Starlette)   │
└─────────────────┘              └─────────────────┘              └──────────────────────┘
                                        │
                                        │ uses
                                        ▼
                                 ┌─────────────────┐
                                 │    MCP SDK      │
                                 │ (streamable_http│
                                 │    _client)     │
                                 └─────────────────┘
```

### Key Components

| Component | Version | Role | Location |
|-----------|---------|------|----------|
| `anaconda-mcp` | 1.0.0.rc.1 | CLI/config orchestrator | This repo |
| `mcp-compose` | 0.1.11 | HTTP proxy between client and downstream | PyPI |
| `mcp` (SDK) | 1.26.0 | MCP protocol client/server | PyPI |
| `environments_mcp_server` | 1.0.0.rc.1 | Downstream MCP server (conda tools) | conda channel |
| `httpx` | (via mcp-compose) | Async HTTP client | PyPI |

### Data Flow During Tool Call

```
1. Client POST /mcp/tools/call ──► mcp-compose :8888
2. mcp-compose POST /tools/call ──► environments_mcp_server :4041
3. Server returns: HTTP 200 OK, Content-Type: text/event-stream
4. Server writes SSE events: data: {"result": ...}\n\n
5. mcp-compose forwards SSE to client
6. Client receives result
```

**Failure Point (KI-011)**: Step 4 fails after ~16-17 rapid calls — server sends headers but never writes SSE body.

---

## Current State

### What We Know

| Aspect | Status | Details |
|--------|--------|---------|
| KI-013 (delays) | UNDERSTOOD | Caused by `timeout` config; use `timeout=60` to avoid |
| KI-011 (hangs) | PARTIALLY FIXED | PR #28 improved threshold from ~4 to ~16-17 iterations |
| Root cause location | NARROWED | Issue is between mcp-compose and environments_mcp_server |
| Trigger condition | IDENTIFIED | ~16-17 rapid sequential error-triggering tool calls |

### Test Results (mcp-compose 0.1.11)

| Test | Iterations | Before Fix | After Fix |
|------|------------|------------|-----------|
| HANG-001 (remove_environment) | 20 | Hangs at 4 | PASSED |
| HANG-002 (install_packages) | 20 | Hangs at 4 | Hangs at 16-17 |
| HANG-003 (mixed) | 40 | Hangs early | Other error |

### Debug Logging Added

During investigation, debug logging was patched into:

1. **mcp-compose** (`/Users/iiliukhina/projects/mcp-compose/mcp_compose/http_client.py`)
   - Markers: `[HTTP_CLIENT #N]`
   - Tracks request/response lifecycle

2. **MCP SDK** (`/opt/miniconda3/envs/anaconda-mcp-dev/lib/python3.13/site-packages/mcp/client/streamable_http.py`)
   - Markers: `[POST_REQ]`, `[SSE_RESP]`
   - Tracks SSE event reception

**WARNING**: This constitutes "dirty state" that may affect test behavior.

---

## Dirty State Concerns

"Dirty state" has two distinct aspects that can affect test behavior:

### 1. Code State (Debug Patches)

| Issue | Impact | Resolution |
|-------|--------|------------|
| Debug patches in mcp-compose | May alter timing/behavior | Recreate conda environment |
| Debug patches in MCP SDK | May alter timing/behavior | Recreate conda environment |

### 2. Runtime State (Ports and Processes)

| Issue | Impact | Resolution |
|-------|--------|------------|
| Zombie processes on port 8888 | mcp-compose cannot bind | Kill before starting |
| Zombie processes on port 4041 | environments_mcp_server cannot bind | Kill before starting |
| Hung process accepting but not responding | Silent timeout (KI-012) | Kill before starting |
| Corrupted connection pool from previous run | May cause earlier hangs | Full process restart |

### 3. Concurrent MCP Clients (IDEs)

**Critical discovery**: IDEs like Cursor, Claude Desktop, or VS Code with anaconda-mcp extensions configured may interfere with test execution.

| Issue | Impact | Resolution |
|-------|--------|------------|
| Cursor with anaconda-mcp extension | Shares port 8888/4041, interleaved requests | Close Cursor during tests |
| Claude Desktop with MCP servers | Competing connections exhaust pool faster | Disable MCP servers in settings |
| Claude Code with MCP configured | Additional request load | Close or reconfigure |

**Symptoms when IDEs are running:**
- Hang threshold becomes unpredictable (varies with IDE activity)
- Connection pool exhausts faster than expected
- Tests that passed in isolation fail when IDE is open

**Check for conflicting clients before testing:**
```bash
# Check if MCP ports are in use (most reliable check)
lsof -i:8888 2>/dev/null && echo "WARNING: Port 8888 in use by another process"
lsof -i:4041 2>/dev/null && echo "WARNING: Port 4041 in use by another process"

# Also check test ports (9888/5041) in case a previous test run is still active
lsof -i:9888 2>/dev/null && echo "WARNING: Test port 9888 in use"
lsof -i:5041 2>/dev/null && echo "WARNING: Test port 5041 in use"
```

Note: Checking process names like `ps aux | grep anaconda-mcp` is NOT reliable —
it matches workspace/project folder names, not actual MCP server processes.

**Recommendation**: Close all IDEs with MCP servers configured before running hang regression tests, or use different ports for test servers.

**Port configuration (as of 2026-03-10)**:
- Test default: **9888** (proxy), **5041** (downstream)
- IDE default: **8888** (proxy), **4041** (downstream)

Tests now use different ports by default to avoid IDE conflicts.

**Important**: The hanging behavior may differ depending on whether the server starts from a clean port state vs. inherits state from zombie processes. A process holding the port but not responding (from a previous hang) can cause KI-012-style silent timeouts that look different from fresh KI-011 hangs.

**Recommendation**: Always kill all related processes before starting tests to ensure consistent baseline:

```bash
pkill -9 -f "anaconda-mcp"
pkill -9 -f "environments_mcp"
lsof -ti:8888 | xargs kill -9 2>/dev/null
lsof -ti:4041 | xargs kill -9 2>/dev/null
sleep 2  # Allow ports to fully release
```

**Critical for reproducibility**: Both servers must start from fresh-no-zombie state:

| Server | Port | Role | Why Fresh Start Matters |
|--------|------|------|------------------------|
| `anaconda-mcp` (mcp-compose) | 8888 | Proxy | Corrupted httpx connection pool may cause earlier hangs |
| `environments_mcp_server` | 4041 | Downstream | Accumulated state may affect SSE response handling |

If either server inherits state from a previous hung session, the hang threshold (normally ~16-17 iterations) may vary unpredictably — sometimes failing earlier, sometimes later. This makes root cause analysis difficult.

**Test protocol**: Before each test run:
1. **Close IDEs** with anaconda-mcp configured (Cursor, Claude Desktop, VS Code)
2. Kill both servers completely
3. Verify ports are free (`lsof -i:8888`, `lsof -i:4041` should return nothing)
4. Verify no competing MCP clients (`ps aux | grep anaconda-mcp`)
5. Start both servers fresh
6. Run test

### Clean-Up Procedure

The simplest way to ensure clean state is to **delete and recreate the conda environment**:

```bash
# 1. Kill any zombie processes
pkill -9 -f "anaconda-mcp"
pkill -9 -f "environments_mcp"
lsof -ti:8888 | xargs kill -9 2>/dev/null
lsof -ti:4041 | xargs kill -9 2>/dev/null

# 2. Deactivate if active
conda deactivate

# 3. Delete the environment entirely
conda env remove -n anaconda-mcp-dev

# 4. Recreate from scratch (from anaconda-mcp repo root)
conda env create -f environment-dev.yml

# 5. Activate and verify clean state
conda activate anaconda-mcp-dev
pip show mcp | grep Version        # mcp doesn't expose __version__
pip show mcp-compose | grep Version
```

This ensures:
- No debug patches remain in MCP SDK or mcp-compose
- Clean package versions matching environment-dev.yml
- No accumulated state from previous test runs

---

## Potential Investigation Paths

### Path A: Clean State Baseline

**Goal**: Confirm issue reproduces without debug patches

**Steps**:
1. Clean up dirty state (see procedure above)
2. Re-run HANG-002 test
3. Verify hang still occurs at iteration ~16-17
4. Document clean baseline behavior

**Effort**: Low (1-2 hours)
**Value**: Establishes reliable baseline for further investigation

---

### Path B: Investigate Downstream Server (environments_mcp_server)

**Goal**: Understand why server stops writing SSE body

**Hypothesis**: Server-side resource exhaustion (connection pool, file descriptors, async task limits)

**Steps**:
1. Add logging to `environments_mcp_server` SSE response handling
2. Monitor file descriptor count during test run
3. Check Starlette/FastMCP connection limits
4. Look for exceptions being swallowed silently

**Where to look**:
- `environments_mcp_server` source (in installed package or repo)
- FastMCP SSE response implementation
- Starlette StreamingResponse handling

**Effort**: Medium (4-8 hours)
**Value**: High — likely location of root cause

---

### Path C: Test with Artificial Delays

**Goal**: Confirm resource exhaustion hypothesis

**Steps**:
1. Modify HANG-002 test to add `time.sleep(0.5)` between iterations
2. Run test — if it passes all 20 iterations, confirms resource exhaustion
3. Binary search for minimum safe delay
4. Document as workaround if root cause fix is not feasible

**Effort**: Low (1-2 hours)
**Value**: Quick validation of hypothesis; potential workaround

---

### Path D: httpx Connection Pool Analysis

**Goal**: Understand connection pool behavior under rapid load

**Steps**:
1. Review mcp-compose httpx client configuration
2. Check pool size limits (`max_connections`, `max_keepalive_connections`)
3. Add connection pool metrics logging
4. Test with increased pool limits

**Relevant code**:
```python
# mcp-compose likely creates httpx.AsyncClient somewhere
# Look for: httpx.AsyncClient(..., limits=httpx.Limits(...))
```

**Effort**: Medium (2-4 hours)
**Value**: Medium — may reveal pool exhaustion

---

### Path E: Network-Level Debugging

**Goal**: Capture exact HTTP traffic when hang occurs

**Steps**:
1. Use `mitmproxy` or `tcpdump` to capture traffic
2. Run HANG-002 test
3. Analyze traffic at iteration 16-17
4. Look for: incomplete responses, connection resets, TCP state

**Commands**:
```bash
# Option 1: mitmproxy
mitmproxy --mode reverse:http://localhost:4041 -p 4040
# Configure mcp-compose to connect to :4040 instead of :4041

# Option 2: tcpdump
sudo tcpdump -i lo0 port 4041 -w hang_capture.pcap
```

**Effort**: Medium (2-4 hours)
**Value**: Definitive answer on what's happening at network level

---

### Path F: Report to mcp-compose Maintainers

**Goal**: Get upstream help/fix

**Steps**:
1. Clean up and document minimal reproduction case
2. File GitHub issue with:
   - Reproduction steps
   - Debug logs showing 0 SSE events for 60s
   - Test environment details
3. Reference PR #28 as partial fix
4. Request investigation of connection pool management

**Effort**: Medium (2-3 hours for good issue)
**Value**: May get fix from maintainers who know the codebase

---

## Recommended Path Forward (Updated)

### Completed
- ✅ Phase 1: Clean baseline established
- ✅ Phase 2: Delay testing (initial results)
- ✅ Phase 3: Test client investigation (client code is correct)
- ✅ Phase 4: **Delays do NOT prevent hang** — call-count-based, not timing-based

### Current Understanding

The hang is a **call-count-based server bug**, not a race condition:
- Occurs after ~15 tool calls regardless of timing
- "GET stream disconnected" is the failure signature
- Requires server restart to clear

### Next Steps

1. **Report to mcp-compose maintainers (Path F)** — HIGH PRIORITY
   - Evidence: hang is call-count-based, delays don't help
   - Provide reproduction: 15 sequential tool calls → hang
   - Key log message: "GET stream disconnected, reconnecting in 1000ms..."

2. **Resource monitoring during test** — NEW
   - Track file descriptors, connections, memory per iteration
   - Identify what accumulates (FDs? async tasks? SSE handlers?)

3. **Server code analysis**
   - Find what counter/resource hits limit at ~15
   - Check httpx Limits configuration
   - Check SSE stream cleanup code

### Workarounds for Now

1. **For CI**: Restart servers between hang test runs (no delay workaround available)
2. **For development**: Use STDIO transport tests (may have different behavior)
3. **For production**: **WARNING** — Real clients WILL hit this if they make >15 tool calls per session, even with normal human-paced usage. Server restart is the only recovery.

---

## Phase 1 Results (2026-03-10)

### Clean Baseline Test

**Environment:**
- Fresh `anaconda-mcp-dev` conda environment (recreated from `environment-dev.yml`)
- `mcp`: 1.26.0
- `mcp-compose`: 0.1.11
- `environments-mcp-server`: 1.0.0.rc.3
- Both servers started fresh (no zombie processes)

**HANG-002 Results (install_packages × 20 iterations):**

| Iteration | Response Time | Status |
|-----------|---------------|--------|
| 1-15 | 0.03-0.16s | ✅ Success |
| 16 | 60s timeout | ❌ **HANG** |

**Conclusions:**
1. Dirty state (debug patches) was **NOT** the cause — issue reproduces with clean packages
2. Hang threshold is consistently **~16 iterations**
3. Server state corruption is cumulative — subsequent test runs fail on iteration 1 if servers not restarted
4. **Both servers must be restarted between test runs** for reproducible results

---

## Phase 2 Results (2026-03-10)

> ⚠️ **NOTE**: These results were **INVALIDATED** by Phase 4. The custom script was using
> the wrong tool name (`conda__conda_install_packages` with prefix) which returned instant
> "Unknown tool" errors without exercising the full tool execution path. See Phase 4 for
> definitive results showing delays do NOT prevent the hang.

### Delay Testing

| Test | Delay | Iterations | Result |
|------|-------|------------|--------|
| pytest HANG-002 | 0ms | 20 | ❌ Fails at iteration 16 |
| Custom script | 0ms | 50 | ✅ All pass ⚠️ (wrong tool name) |
| Custom script | 10ms | 20 | ✅ All pass ⚠️ (wrong tool name) |
| Custom script | 20ms | 20 | ✅ All pass ⚠️ (wrong tool name) |
| Custom script | 50ms | 20 | ✅ All pass ⚠️ (wrong tool name) |
| Custom script | 100ms | 20 | ✅ All pass ⚠️ (wrong tool name) |
| Custom script | 500ms | 20 | ✅ All pass ⚠️ (wrong tool name) |

**Key finding**: Custom script with identical HTTP calls (same headers, same payload, same session handling) passes 50 iterations with NO delay, while pytest test fails at iteration 16.

### Difference Analysis

The custom script and pytest test differ in:

| Aspect | pytest test | Custom script |
|--------|-------------|---------------|
| Timeout mechanism | SIGALRM (60s hard timeout) | httpx.Timeout |
| Response reading | via `response.text` | via `response.text` |
| Headers | `Accept: application/json, text/event-stream` | Same |
| Session handling | `fresh_session_id` fixture | Manual init |

**Primary suspect**: SIGALRM handling may be corrupting httpx connection state. When SIGALRM fires (even if response completes quickly), it could interrupt async cleanup or socket handling in subtle ways.

### Hypothesis Update

**Original**: Resource exhaustion under rapid sequential load causes server to fail writing SSE body.

**Revised**: The hang may be **test infrastructure specific**:
1. SIGALRM interferes with httpx's connection pool management
2. After ~16 iterations, accumulated state corruption causes the next request to hang
3. The server itself may be fine — the issue is in how the test client handles connections

### Implications

1. **For test reliability**: Consider removing SIGALRM-based timeout in favor of httpx timeout only
2. **For production**: Real clients (Cursor, Claude Desktop) don't use SIGALRM — they may not experience this issue
3. **For mcp-compose**: May still want to investigate connection pool behavior, but priority lowered

### Test Script

The custom test script is at `/tmp/test_hang_with_delay.py` — can be used to verify behavior without SIGALRM interference.

---

## Phase 3 Results (2026-03-10)

### Test Client Investigation

**Hypothesis tested**: SIGALRM/threading wrappers in test client cause httpx connection corruption.

**Method**: Compared pytest test behavior vs direct Python script using identical mcp_client.py code.

**Results**:

| Test Method | Outcome | Notes |
|-------------|---------|-------|
| Direct script (wrong tool name) | ✅ 50 iterations | Tool `conda__conda_install_packages` returned instant error |
| Direct script (correct tool name) | ✅ 20 iterations | Tool `conda_install_packages` works with fresh server |
| Pytest test | ❌ Hangs at ~8-16 | Same httpx calls, same tool name |

**Key discovery**: The test was accidentally using wrong tool name (`conda__conda_install_packages` with prefix) which returned "Unknown tool" error instantly. The correct name is `conda_install_packages` (mcp-compose adds prefix).

### Root Cause Confirmation

The hang is **NOT** caused by:
- ❌ SIGALRM interference (pytest-timeout not installed)
- ❌ Threading wrappers
- ❌ Test client httpx configuration
- ❌ Wrong tool names (fixed)

The hang **IS** caused by:
- ✅ **Server state corruption** after N rapid sequential tool calls
- ✅ Both mcp-compose AND environments_mcp_server contribute
- ✅ Corruption persists until servers are restarted

### Evidence

```
Fresh server state:
  - Iteration 1: 0.18s ✅
  - Iteration 2-8: 0.03-0.04s ✅
  - Iteration 9+: HANG (60s timeout)

After restart:
  - Same pattern repeats
```

Direct downstream server test:
```bash
# Fresh session to environments_mcp_server:4041
curl install_packages → "environment not found" in 0.02s ✅

# After mcp-compose corruption:
curl install_packages → HANG (2+ minutes)
```

### Test Client Fix Applied

Updated `mcp_client.py` to use direct httpx calls without wrappers:

```python
# Direct httpx call — matches real client behavior (Cursor, Claude Desktop)
response = httpx.post(
    BASE_URL,
    json=request_body,
    headers=headers,
    timeout=httpx.Timeout(connect=10, read=TOOL_TIMEOUT, write=10, pool=10),
)
```

This is correct behavior - the hang is not a test artifact.

---

## Open Questions (Updated)

1. **Why does the hang threshold vary (8-16 iterations)?**
   - ✅ **PARTIALLY ANSWERED**: In isolated testing (Phase 4), threshold is consistent at ~15
   - Earlier variation (8-16) may have been due to:
     - Concurrent IDE clients (now ruled out with isolated ports)
     - Zombie processes from previous runs
     - Server state carried over between test runs
   - **Phase 4 conclusion**: With clean isolated setup, threshold is ~15 calls

2. **Is the issue in mcp-compose or environments_mcp_server?**
   - Both are involved - downstream server also hangs when tested directly after corruption
   - Likely mcp-compose connection pool corruption propagates to downstream

3. **Why does server restart fix it?**
   - Connection pool reset
   - Async task cleanup
   - Socket state reset

---

## Files in This Investigation

| File | Purpose |
|------|---------|
| `INVESTIGATION.md` | Detailed investigation log |
| `todo.md` | Status tracking |
| `LANDSCAPE_AND_PATHS.md` | This file — overview and next steps |
| `test_logs/` | Raw test output logs |
| `config_snapshots/` | Environment configuration captures |

---

## Phase 4 Results (2026-03-10)

### Delay Testing — Initial Results

**Hypothesis tested**: Adding delays between iterations prevents hang by allowing connection pool recovery.

**Method**: Added 2-second `ITERATION_DELAY` between each iteration in pytest tests.

**Configuration**:
- Test ports: 9888 (proxy), 5041 (downstream) — isolated from IDEs
- IDEs: Cursor restarted, no anaconda-mcp in MCP config
- Delay: 2 seconds between iterations ("human-like" pacing)
- Total iterations: 20
- **Single instance**: Only one anaconda-mcp and one environments-mcp-server running
- **No concurrency**: Verified no other MCP processes on system

**Results with real conda.install()**:

| Test | Delay | Outcome | Hang Iteration |
|------|-------|---------|----------------|
| HANG-002 (no delay) | 0s | ❌ Hang | ~15-16 |
| HANG-002 (with delay) | 2s | ❌ **Hang** | ~15-16 |

**Server log evidence** (with 2s delays):
```
17:29:12 — Iteration 1: conda_install_packages ✅
17:29:15 — Iteration 2: ✅
17:29:17 — Iteration 3: ✅
... (properly spaced ~2s apart)
17:30:41 — Iteration 15: ✅
17:30:41 — "GET stream disconnected, reconnecting in 1000ms..."
[HANG — no further responses]
```

---

## Phase 5 Results (2026-03-10)

### Mock Implementation Testing — ROOT CAUSE IDENTIFIED

**Hypothesis tested**: Is the hang caused by mcp-compose proxy or by the actual conda operation?

**Method**: Replaced `install_packages.py` in environments_mcp_server with a mock that:
- Skips all actual conda operations
- Returns the same error response structure
- Uses `asyncio.sleep()` with configurable delay

**Results**:

| Test Scenario | Mock Delay | Outcome | Conclusion |
|---------------|------------|---------|------------|
| Real `conda.install()` | N/A | ❌ Hangs at ~15 | Bug is in conda operation |
| Mock implementation | 0.1s | ✅ **PASSED** all 20 | Not call-count-based |
| Mock implementation | 3.0s | ✅ **PASSED** all 20 | Not timing-related |

### Critical Finding — Bug Location Identified

**The bug is 100% in `environments_mcp_server` / `anaconda-connector-conda`**, NOT in mcp-compose.

The mock bypassed this code:
```python
conda = await get_conda()                    # ← possibly here
install_result = await conda.install(...)    # ← likely here
```

And the test passed all 20 iterations with both 0.1s and 3.0s delays.

### What This Proves

| Component | Status | Evidence |
|-----------|--------|----------|
| mcp-compose proxy | ✅ **INNOCENT** | Mock passes 20 iterations |
| MCP SDK (streamable_http) | ✅ **INNOCENT** | Same transport, mock works |
| httpx connection pool | ✅ **INNOCENT** | 3s delays work fine |
| `environments_mcp_server` | ❌ **BUG HERE** | Only fails with real conda ops |
| `anaconda-connector-conda` | ❌ **BUG HERE** | `conda.install()` causes hang |

### Ruled Out

- ❌ mcp-compose proxy connection pool exhaustion
- ❌ SSE stream handling in proxy
- ❌ Call count alone (mock with same count passes)
- ❌ Response timing/duration (3s mock passes)
- ❌ Test infrastructure artifacts

### Root Cause

Something in the `conda.install()` code path accumulates state/resources that eventually causes the hang. Possible culprits in `anaconda-connector-conda`:
- Conda solver state not being released
- Subprocesses or file handles not being cleaned up
- Async task accumulation
- Memory/object accumulation in conda internals

### Next Steps — COMPLETED

Binary search completed. Root cause identified.

---

## Phase 6 Results (2026-03-10)

### ROOT CAUSE IDENTIFIED: `logger.exception()` causes the hang

**Method**: Added `[PATH]` logging to trace code execution, then systematically commented out code.

**Key Evidence**:
```
# environments_mcp_server log shows 14 successful iterations:
18:35:27 - [PATH] Calling conda.install()...
18:35:27 - [PATH] Caught EnvironmentLocationNotFound  # iteration 1
...
18:35:54 - [PATH] Calling conda.install()...
18:35:54 - [PATH] Caught EnvironmentLocationNotFound  # iteration 14
# NO LOG FOR ITERATION 15 — request never reached install_packages function!
```

The hang occurs in **environments_mcp_server's request dispatch layer**, not in `install_packages()` itself.

**Final Test**:

| Test | `logger.exception()` | Result |
|------|---------------------|--------|
| With `logger.exception(ex)` | ✅ Enabled | ❌ Hangs at ~15 |
| Without `logger.exception(ex)` | ❌ Commented | ✅ **PASSED all 20** |

### Root Cause

`logger.exception()` in the `EnvironmentLocationNotFound` exception handler causes state accumulation that eventually blocks the MCP request dispatch after ~15 calls.

**Likely mechanisms**:
1. **File descriptor exhaustion** — logging handlers opening files that aren't closed
2. **Async/threading conflict** — `logger.exception()` blocking the event loop
3. **Telemetry middleware** — `environments_mcp_server` has telemetry that may intercept logging
4. **Log buffer exhaustion** — unbounded log growth blocking I/O

### Fix Recommendation

In `environments_mcp_server/tools/environments/install_packages.py`:

```python
# BEFORE (causes hang):
except conda_exceptions.EnvironmentLocationNotFound as ex:
    logger.exception(ex)  # <-- PROBLEM
    return ServerToolResult(...)

# AFTER (fix):
except conda_exceptions.EnvironmentLocationNotFound as ex:
    logger.warning(f"Environment not found: {ex}")  # Use warning, not exception
    return ServerToolResult(...)
```

Or investigate why `logger.exception()` causes issues in the async MCP context.

### Files to Report Bug

1. **Primary**: `environments_mcp_server` — the `logger.exception()` call
2. **Secondary**: Check if MCP SDK's async handling conflicts with sync logging

### Workaround

Remove or replace `logger.exception()` calls in exception handlers with `logger.warning()` or `logger.error()` (without stack trace).

---

## References

- [KI-011 in KNOWN_ISSUES.md](../KNOWN_ISSUES.md#ki-011-mcp-compose-proxy-hangs-and-corrupts-session-on-tool-error)
- [KI-013 in KNOWN_ISSUES.md](../KNOWN_ISSUES.md#ki-013-mcp-compose-delays-all-responses-by-exactly-the-configured-timeout-value)
- [mcp-compose PR #28](https://github.com/datalayer/mcp-compose/pull/28)
- [mcp-compose issue #27](https://github.com/datalayer/mcp-compose/issues/27)

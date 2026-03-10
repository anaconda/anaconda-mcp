# KI-011/KI-013 Investigation: Landscape and Potential Paths

**Date**: 2026-03-10
**Status**: Active Investigation
**Last Updated**: After mcp-compose 0.1.11 testing

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
1. Kill both servers completely
2. Verify ports are free (`lsof -i:8888`, `lsof -i:4041` should return nothing)
3. Start both servers fresh
4. Run test

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
python -c "import mcp; print(mcp.__version__)"
python -c "import mcp_compose; print(mcp_compose.__version__)"
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

## Recommended Path Forward

### Phase 1: Establish Clean Baseline (Path A)
- Remove debug patches
- Confirm issue reproduces
- Document baseline

### Phase 2: Quick Validation (Path C)
- Test with artificial delays
- If delays fix it → confirms resource exhaustion
- Provides immediate workaround

### Phase 3: Root Cause (Path B or E)
- If delays help → investigate server-side resource limits (Path B)
- If delays don't help → network-level debugging (Path E)

### Phase 4: Upstream (Path F)
- Report findings to mcp-compose with reproduction case
- Include all evidence gathered

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

### Delay Testing

| Test | Delay | Iterations | Result |
|------|-------|------------|--------|
| pytest HANG-002 | 0ms | 20 | ❌ Fails at iteration 16 |
| Custom script | 0ms | 50 | ✅ All pass |
| Custom script | 10ms | 20 | ✅ All pass |
| Custom script | 20ms | 20 | ✅ All pass |
| Custom script | 50ms | 20 | ✅ All pass |
| Custom script | 100ms | 20 | ✅ All pass |
| Custom script | 500ms | 20 | ✅ All pass |

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

## Open Questions

1. **Why does HANG-001 pass but HANG-002 fail?**
   - Different code paths in `environments_mcp_server`?
   - Different response sizes?
   - Different async handling?

2. **Is the issue in mcp-compose or environments_mcp_server?**
   - Server sends headers but no body → likely server issue
   - But mcp-compose pool management may contribute

3. **Why exactly 16-17 iterations?**
   - Suggests a fixed resource limit being hit
   - Connection pool size? Async task limit? FD limit?

4. **Can we reproduce with a minimal MCP server?**
   - Would isolate whether issue is in environments_mcp_server specifically
   - Or in the mcp-compose/MCP SDK stack

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

## References

- [KI-011 in KNOWN_ISSUES.md](../KNOWN_ISSUES.md#ki-011-mcp-compose-proxy-hangs-and-corrupts-session-on-tool-error)
- [KI-013 in KNOWN_ISSUES.md](../KNOWN_ISSUES.md#ki-013-mcp-compose-delays-all-responses-by-exactly-the-configured-timeout-value)
- [mcp-compose PR #28](https://github.com/datalayer/mcp-compose/pull/28)
- [mcp-compose issue #27](https://github.com/datalayer/mcp-compose/issues/27)

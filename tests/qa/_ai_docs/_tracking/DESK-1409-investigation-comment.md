# DESK-1409 Investigation Results

**Date**: 2026-03-20
**Tested by**: QA Team (iiliukhina)

---

## Summary

Bug is isolated to **mcp-compose's proxy layer** — NOT in MCP SDK, NOT in environments_mcp_server.

---

## Test Results

| Test | Target | Result | Notes |
|------|--------|--------|-------|
| **Test 1**: Direct to environments_mcp_server | Port 5041 | **PASS 50/50** | No hang, ~0.25s per call |
| **Test 2**: mcp-compose 0.1.11 (installed) | Port 9999→6041 | **FAIL at 21** | Timeout after 60s |
| **Test 3**: mcp-compose 0.1.10 (local debug) | Port 9999→6041 | **FAIL at 21** | Same behavior |
| **Test 4**: MCP SDK direct sessions | Port 5041 | **PASS 30/30** | SDK session handling OK |

---

## Root Cause Analysis

### What the logs show:
1. **Upstream sessions**: Only 1 session tracked in `_server_instances` (single client reusing session)
2. **Downstream sessions**: 22 sessions created (1 init + 21 tool calls attempted)
3. **Iteration 21**: Request sent by curl but **never logged by uvicorn** — server stopped accepting connections

### Timeline at hang (from logs):
```
19:05:33 - POST /mcp HTTP/1.1 200 OK (iteration 20 response)
19:05:33 - Processing request of type CallToolRequest
19:05:33 - Received session ID: f3b2eac21c124c82b2e5574fbf2e42a7
19:05:35 - [SESSION MONITOR] Active sessions: 1  ← No new request logged
19:05:40 - [SESSION MONITOR] Active sessions: 1  ← curl waiting...
... (continues until 60s timeout)
```

### Key observation:
- mcp-compose creates a **NEW downstream session for every tool call** (22 sessions in 21 iterations)
- After ~20 downstream session create/destroy cycles, the HTTP server stops accepting new connections
- The server process is alive (session monitor keeps logging) but uvicorn doesn't log incoming requests
- This suggests **connection pool exhaustion** or **async resource leak** in the proxy code

---

## Scripts Used

All scripts available in `tests/qa/_ai_docs/scripts/`:

1. `test-env-mcp-direct.sh` — Test environments_mcp_server directly (bypass mcp-compose)
2. `test-mcp-compose-direct.sh` — Test mcp-compose with downstream server
3. `test-mcp-compose-local.sh` — Test with LOCAL mcp-compose source + debug logging
4. `test-mcp-sdk-sessions.py` — Minimal MCP SDK test to isolate session handling

---

## Root Cause Analysis (Deep Dive)

**Location**: `mcp_compose/cli.py` lines 878-918 — `streamable_http_tool_proxy` function

**The Problem**: Every tool call creates a brand new downstream session:

```python
async def streamable_http_tool_proxy(**kwargs):
    # For EVERY tool call:
    async with streamablehttp_client(url=...) as (...):  # NEW httpx client
        async with ClientSession(...) as session:        # NEW MCP session
            await session.initialize()                   # Re-initialize every time
            result = await session.call_tool(...)        # Then call tool
    # Context exit: DELETE request sent, connections closed
```

**Why this causes hangs after ~20 iterations**:

1. **httpx client churn**: Each `streamablehttp_client` creates a NEW `httpx.AsyncClient` with its own connection pool
2. **TCP TIME_WAIT accumulation**: Rapid connection teardown leaves sockets in TIME_WAIT state
3. **Resource exhaustion**: After ~20 cycles, OS/uvicorn connection limits are reached
4. **Silent hang**: uvicorn stops accepting new connections but process stays alive

**Evidence from logs**:
- Iteration 20: `POST /mcp HTTP/1.1 200 OK` logged by uvicorn
- Iteration 21: **No uvicorn log at all** — request never accepted
- Server process alive (SESSION MONITOR keeps logging)

---

## Recommended Fix

**mcp-compose should maintain persistent downstream sessions** instead of creating new ones per tool call:

```python
# Suggested architecture:
class DownstreamSessionManager:
    """Maintain persistent sessions to downstream servers."""
    _sessions: dict[str, tuple[ClientSession, streamablehttp_client_context]] = {}

    async def call_tool(self, server_url: str, tool_name: str, args: dict):
        session = await self._get_or_create_session(server_url)
        return await session.call_tool(tool_name, args)

    async def _get_or_create_session(self, server_url: str) -> ClientSession:
        if server_url not in self._sessions:
            # Create persistent session (initialize once)
            ctx = streamablehttp_client(url=server_url)
            read, write, get_id = await ctx.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            self._sessions[server_url] = (session, ctx)
        return self._sessions[server_url][0]
```

This follows MCP best practices — sessions should be reused for multiple tool calls.

---

## Logs

Full debug logs available at: `/tmp/mcp-compose-local-20260320-190457/`
- `mcp-compose-full-at-hang.log` — Complete log at time of hang
- `results.log` — Test iteration results

---

---

## Update (2026-03-20 19:45)

### Additional Investigation on Latest mcp-compose (0.1.11)

Tested with latest mcp-compose main branch which includes:
- `streamable_http_client_compat` helper using non-deprecated `streamable_http_client`
- Explicit httpx client management

**Result**: Still fails at iteration 21.

### Fixes Attempted (all unsuccessful):
1. **Shared httpx client pool** - Doesn't help
2. **Increased httpx connection limits** (max_connections=200, max_keepalive=100) - Doesn't help
3. **Small delay after session cleanup** - Doesn't help

### Key Finding:
The issue is NOT with httpx client creation. Even with shared clients, the hang persists at exactly iteration 21.

### Current Theory:
The problem appears to be in the MCP SDK's internal handling of:
- `streamable_http_client` context creates TaskGroups and memory streams per call
- These internal resources may not be fully cleaned up
- Something accumulates after ~20 iterations that blocks uvicorn from accepting new connections

### Suggested Next Steps:
1. Investigate MCP SDK's `streamable_http_client` cleanup (anyio TaskGroups)
2. Check if there's a limit in anyio/asyncio event loop
3. Consider filing issue with MCP SDK maintainers
4. Workaround: Maintain truly persistent downstream sessions (requires architectural changes)

---

## Update (2026-03-20 20:20) - FIX FOUND

### Root Cause
The hang at iteration 21 was caused by **HTTP/1.1 connection exhaustion** in the httpx client. When mcp-compose acts as a proxy (server + client in same process), rapid HTTP/1.1 connection cycling caused resource exhaustion.

### The Fix
Enable **HTTP/2** in the httpx client used for downstream connections:

```python
# mcp_compose/http_client.py
limits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=5.0,
)
async with httpx.AsyncClient(
    headers=headers,
    timeout=httpx.Timeout(float(timeout)),
    verify=verify,
    limits=limits,
    http2=True,  # Key fix: Use HTTP/2 for better connection handling
) as http_client:
    ...
```

### Why HTTP/2 Fixes It
1. **Connection multiplexing**: HTTP/2 reuses a single TCP connection for multiple requests
2. **No connection cycling**: Avoids rapid connect/disconnect that exhausts resources
3. **Better cleanup**: HTTP/2's stream-based model handles cleanup more gracefully
4. **Performance boost**: Response times dropped from ~0.85s to ~0.03s per call

### Test Results After Fix
- **50/50 iterations passed** (previously failed at 21)
- Response times: 0.03s (vs 0.85s with HTTP/1.1)
- No hangs detected

### Files Changed
- `mcp_compose/http_client.py`: Added `http2=True` and explicit connection limits

---

CC: @Romulo Goncalves

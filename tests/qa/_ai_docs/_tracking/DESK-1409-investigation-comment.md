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

CC: @Romulo Goncalves

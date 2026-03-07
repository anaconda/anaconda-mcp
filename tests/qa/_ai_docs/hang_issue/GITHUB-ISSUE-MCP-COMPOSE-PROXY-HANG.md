# Streamable HTTP proxy hangs indefinitely after fast-returning tool call, corrupting process-wide connection pool

**`mcp-compose` version**: 0.1.10
**`mcp` SDK version**: 1.26.0
**Python**: 3.10, 3.12, 3.13
**OS**: macOS 15.3 arm64 (also observed on Linux)
**Reproducibility**: Deterministic

---

## Summary

When `mcp-compose` proxies a call to a downstream Streamable HTTP server and that server
returns its result **quickly** (the tool handler returns synchronously, before awaiting
any async operation), FastMCP serves the result inline in the `tools/call` POST body
with HTTP 200 OK and `Content-Type: application/json`. The `cli.py` proxy uses the
**deprecated `streamablehttp_client`** from the MCP SDK, which opens a concurrent GET
SSE stream and defaults to a **5-minute SSE read timeout**. The cleanup of that SSE
stream — which keeps receiving server keepalives — hangs for up to 5 minutes.

After one hang the underlying httpx connection pool slot is never released. All
subsequent calls to the downstream server block on this stuck slot, making the
corruption **process-wide**. Only restarting `mcp-compose` recovers.

---

## Affected code

`mcp_compose/cli.py` — the `streamable_http_tool_proxy` closure (inside
`run_server`) calls the deprecated function for every tool invocation:

```python
# mcp_compose/cli.py  (current)
async with streamablehttp_client(          # ← deprecated; adds sse_read_timeout=300s
    url=http_config.url,
    headers=hdrs if hdrs else None,
    timeout=float(http_config.timeout),    # ← 30 s, but SSE read timeout is 5 min
) as (read_stream, write_stream, get_session_id):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        result = await session.call_tool(original_tool_name, kwargs)
```

The function signature of the deprecated wrapper confirms the default:

```python
# mcp/client/streamable_http.py
@deprecated("Use `streamable_http_client` instead.")
async def streamablehttp_client(
    ...
    timeout: float | timedelta = 30,
    sse_read_timeout: float | timedelta = 60 * 5,   # ← 5 minutes default
    ...
```

---

## What happens step by step

```
1.  mcp-compose calls streamablehttp_client(timeout=30)
2.  MCP SDK opens GET /mcp  → SSE stream to downstream server
        ⚠️  Race: GET stream opens before initialize POST completes
3.  POST /mcp  initialize    → 202 Accepted, result via SSE  ✓
4.  POST /mcp  tools/call    → 200 OK, result inline (JSON body)
        ↳ downstream server returned synchronously (error path)
        ↳ FastMCP serves result inline when no SSE stream was ready
5.  MCP SDK reads 200 OK inline result correctly via _handle_json_response  ✓
6.  ClientSession exits — tries to cancel the GET SSE stream task
7.  GET SSE stream is alive and receiving keepalives
        ↳ sse_read_timeout = 300 s → cleanup hangs up to 5 minutes
8.  streamablehttp_client context never closes cleanly
9.  httpx connection pool slot is leaked
10. All subsequent calls to the downstream server block on the stuck slot
        → process-wide hang, requires mcp-compose restart
```

The hang is specific to **fast-returning calls** (tool error paths, argument
validation, etc.) because those return before any async I/O, causing FastMCP to
serve the result inline rather than via SSE. Slow calls (real conda/subprocess work)
await I/O first, so FastMCP uses 202 Accepted + SSE — the path that cleans up
correctly.

---

## Reproduction

Minimal reproducer against any FastMCP-based downstream server. Trigger a tool that
returns immediately (e.g. validation error, non-existent resource):

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client  # deprecated

async def main():
    for i in range(1, 21):
        print(f"call {i}/20 ...", end=" ", flush=True)
        async with streamablehttp_client("http://localhost:4041/mcp", timeout=30) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.call_tool("install_packages", {
                    "prefix": "/tmp/nonexistent-env-ki011",
                    "packages": ["numpy"],
                })
                print("ok")

asyncio.run(main())
# Hangs at call 4 (HTTP) or call 16 (STDIO upstream), then all subsequent calls hang
```

The hang triggers deterministically at a fixed call count because it depends on the
httpx connection pool reaching a threshold — not on any timing.

---

## Impact

| Scenario | Behaviour |
|---|---|
| Call that triggers the hang | Hangs for up to 5 minutes, then errors |
| All subsequent calls | Hang indefinitely (process-wide pool corruption) |
| AI client (Cursor, Claude Code) | Shows "Generating…" with no error surfaced |
| New chat session in same client | Also hangs — process restart required |
| STDIO upstream (same internal path) | Same hang, triggers at call 16 instead of 4 |

Confirmed with:

| Client | Transport to mcp-compose | Python | Hangs? |
|---|---|---|---|
| Cursor | Streamable HTTP | 3.13 | Yes |
| Claude Code (`--http`) | Streamable HTTP | 3.10 | Yes |
| Cursor | STDIO | 3.12 | Yes |
| Claude Desktop | STDIO | — | No |

---

## Suggested fix

### Fix 1 — Switch from deprecated `streamablehttp_client` to `streamable_http_client`

The new API does not add the 5-minute SSE read timeout and is the currently
recommended entry point:

```python
# mcp_compose/cli.py  (proposed)
from mcp.client.streamable_http import streamable_http_client  # not deprecated

async def streamable_http_tool_proxy(**kwargs):
    async with streamable_http_client(
        url=http_config.url,
        headers=hdrs if hdrs else None,
    ) as (read_stream, write_stream, get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(original_tool_name, kwargs)
            ...
```

### Fix 2 — Bound the entire call with `asyncio.timeout`

Ensures no single proxied call can hang the process regardless of SDK internals or
downstream misbehaviour:

```python
async def streamable_http_tool_proxy(**kwargs):
    async with asyncio.timeout(float(http_config.timeout)):
        async with streamable_http_client(url=http_config.url, ...) as (...):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(original_tool_name, kwargs)
                ...
```

Both fixes together prevent the pool corruption and bound recovery to the configured
timeout per call.

---

## Additional finding — STDIO transport inconsistency

Over STDIO transport, `mcp-compose` encodes a downstream tool error with
`isError: false` at the outer JSON-RPC level (the error payload is inside
`content[0].text` as a JSON string). Over HTTP the same error surfaces as
`isError: true`. This is a separate, lower-severity serialisation inconsistency
unrelated to the hang.

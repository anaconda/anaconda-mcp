# Streamable HTTP proxy hangs due to deprecated `streamablehttp_client`

**Version**: mcp-compose 0.1.10, mcp SDK 1.26.0, Python 3.13
**Reproducibility**: Deterministic (hangs at ~4th call)

## Problem

`mcp-compose` uses the deprecated `streamablehttp_client` which has a hidden 5-minute SSE read timeout (`sse_read_timeout=300`). When a downstream tool returns quickly (validation errors, etc.), the SSE stream cleanup hangs, corrupting the httpx connection pool. All subsequent calls block indefinitely.

## Reproduction

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    for i in range(1, 21):
        print(f"call {i}/20 ...", end=" ", flush=True)
        async with streamablehttp_client("http://localhost:8080/mcp", timeout=30) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                # Any fast-returning call triggers the bug
                await session.call_tool("some_tool", {"invalid": "args"})
                print("ok")

asyncio.run(main())
# Hangs at call 4, then all subsequent calls hang
```

## Root Cause

```python
# mcp/client/streamable_http.py
@deprecated("Use `streamable_http_client` instead.")
async def streamablehttp_client(
    ...
    sse_read_timeout: float | timedelta = 60 * 5,  # ← hidden 5-min default
)
```

The deprecated function opens an SSE stream with a 5-minute read timeout. When tool handlers return synchronously (before any async I/O), FastMCP serves results inline (200 OK) instead of via SSE. The SSE cleanup then hangs waiting for the timeout, leaking the connection pool slot.

## Solution

Replace deprecated `streamablehttp_client` with non-deprecated `streamable_http_client` using explicit `httpx.AsyncClient`:

```python
def streamable_http_client_compat(url, headers=None, timeout=30):
    import httpx
    from contextlib import asynccontextmanager
    from mcp.client.streamable_http import streamable_http_client

    @asynccontextmanager
    async def _context():
        async with httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(float(timeout)),
        ) as http_client:
            async with streamable_http_client(url=url, http_client=http_client) as streams:
                yield streams

    return _context()
```

## Related

- [python-sdk #1941](https://github.com/modelcontextprotocol/python-sdk/issues/1941)
- [python-sdk #1811](https://github.com/modelcontextprotocol/python-sdk/issues/1811)

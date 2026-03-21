# fix: enable HTTP/2 to prevent proxy hang after ~20 tool calls

Fixes #XX (link to issue)

## Summary

Enable HTTP/2 in the downstream httpx client to prevent connection exhaustion that causes mcp-compose to hang after approximately 20 sequential tool calls when proxying to streamable HTTP servers.

## Problem

When mcp-compose acts as a proxy (upstream MCP server + downstream MCP client in the same process), sequential tool calls would hang at exactly iteration 21. The root cause was HTTP/1.1 connection cycling - each tool call creates a new downstream session, and the rapid connect/disconnect pattern exhausts connection resources.

**Symptoms:**
- Works fine for first 20 tool calls (~0.85s each)
- Iteration 21 hangs indefinitely (60s timeout)
- uvicorn stops accepting new connections but process stays alive
- Direct calls to downstream server work fine (50+ iterations)

## Solution

Enable HTTP/2 in the httpx client used for downstream connections:

```python
limits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=5.0,
)
async with httpx.AsyncClient(
    ...
    limits=limits,
    http2=True,  # Key fix
) as http_client:
```

## Why HTTP/2 Fixes It

1. **Connection multiplexing**: HTTP/2 reuses a single TCP connection for multiple requests instead of creating new connections
2. **No connection cycling**: Avoids the rapid connect/disconnect pattern that exhausts resources
3. **Better resource cleanup**: HTTP/2's stream-based model handles cleanup more gracefully
4. **Performance improvement**: Response times drop from ~0.85s to ~0.03s (28x faster)

## Test Results

| Test | Before | After |
|------|--------|-------|
| 25 iterations | FAIL at 21 | PASS 25/25 |
| 50 iterations | FAIL at 21 | PASS 50/50 |
| Response time | ~0.85s | ~0.03s |

## Changed Files

- `mcp_compose/http_client.py` - Added `http2=True` and explicit connection limits (8 lines)

## Testing

```bash
# Run the test script
ITERATIONS=50 ./tests/qa/_ai_docs/scripts/test-mcp-compose-local.sh
```

# Streamable HTTP proxy hangs after ~20 tool calls

## Summary

When mcp-compose proxies tool calls to a downstream streamable HTTP server, it consistently hangs at the 21st sequential tool call. The issue is caused by HTTP/1.1 connection exhaustion.

## Environment

- **mcp-compose**: 0.1.11
- **MCP SDK**: 1.26.0
- **httpx**: 0.28.1
- **Python**: 3.13
- **OS**: macOS (Darwin 25.2.0)

## Reproduction

1. Configure mcp-compose to proxy to a streamable HTTP downstream server (e.g., environments_mcp_server)
2. Make sequential tool calls through mcp-compose

```bash
# Start downstream server
python -m environments_mcp_server start --transport streamable-http --port 6041

# Start mcp-compose proxy
mcp-compose serve --config config.toml --port 9999

# Make sequential tool calls
for i in $(seq 1 25); do
    curl -X POST "http://localhost:9999/mcp" \
        -H "Content-Type: application/json" \
        -H "Mcp-Session-Id: $SESSION_ID" \
        -d '{"jsonrpc":"2.0","id":'$i',"method":"tools/call","params":{"name":"some_tool","arguments":{}}}' \
        --max-time 60
done
```

**Expected**: All 25 calls succeed
**Actual**: Calls 1-20 succeed, call 21 hangs indefinitely

## Root Cause Analysis

The issue is in `mcp_compose/http_client.py`. The `streamable_http_client_compat` function creates a new httpx client for each downstream call using HTTP/1.1 (default):

```python
async with httpx.AsyncClient(
    headers=headers,
    timeout=httpx.Timeout(float(timeout)),
    verify=verify,
) as http_client:
```

When mcp-compose acts as both server (upstream) and client (downstream) in the same process:

1. Each tool call creates a new HTTP/1.1 connection to the downstream server
2. Connections are rapidly created and destroyed
3. After ~20 iterations, connection resources are exhausted
4. uvicorn stops accepting new connections (but process stays alive)
5. The 21st request never gets processed

**Key evidence:**
- Direct calls to downstream server work fine (50+ iterations)
- The hang is always at exactly iteration 21
- Logs show request sent but never received by uvicorn

## Proposed Fix

Enable HTTP/2 in the httpx client:

```python
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
    http2=True,  # Use HTTP/2 for connection multiplexing
) as http_client:
```

HTTP/2 multiplexes requests over a single TCP connection, avoiding the connection cycling that causes exhaustion.

## Test Results After Fix

- **50/50 iterations pass** (vs failing at 21)
- Response times: ~0.03s (vs ~0.85s with HTTP/1.1) - 28x faster

## Related

- PR #28 fixed a similar issue with the deprecated `streamablehttp_client` (5-min SSE timeout)
- This is a separate issue that emerged after PR #28

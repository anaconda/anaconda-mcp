# Proxy Hang Fix Summary

## What We Changed

**File**: `mcp_compose/http_client.py`

**Change**: Added HTTP/2 support (with fallback) and explicit connection limits

**Dependency**: Requires `h2` package for HTTP/2:
```bash
pip install httpx[http2]
```

```diff
     @asynccontextmanager
     async def _context():
+        # Use explicit limits to prevent connection exhaustion
+        limits = httpx.Limits(
+            max_connections=100,
+            max_keepalive_connections=20,
+            keepalive_expiry=5.0,
+        )
         async with httpx.AsyncClient(
             headers=headers,
             timeout=httpx.Timeout(float(timeout)),
             verify=verify,
+            limits=limits,
+            http2=True,  # Use HTTP/2 for better connection handling
         ) as http_client:
```

## Why We Changed It

### The Problem
mcp-compose hangs at exactly the 21st sequential tool call when proxying to streamable HTTP servers.

### Root Cause
HTTP/1.1 connection exhaustion. Each tool call:
1. Creates new httpx client
2. Opens new TCP connection to downstream
3. Closes connection after response

After ~20 cycles, connection resources are exhausted and uvicorn stops accepting new connections.

### Why HTTP/2 Fixes It
- **Connection multiplexing**: Single TCP connection handles multiple requests
- **No connection cycling**: Reuses connection instead of create/destroy
- **Better cleanup**: Stream-based model handles resource cleanup gracefully

## Results (Unit Test)

| Metric | Before | After |
|--------|--------|-------|
| Max iterations | 20 (hangs at 21) | 50+ |
| Response time | ~0.85s | ~0.03s |
| Connection pattern | New connection per call | Multiplexed |

## E2E Verification (DESK-1409)

| Test | Config | Result |
|------|--------|--------|
| Through mcp-compose | Claude Desktop → anaconda-mcp → mcp-compose → environments-mcp | FAIL at iteration 15 |
| Direct STDIO | Claude Desktop → environments-mcp (STDIO) | PASS 30+ operations |

**Conclusion**: Bug is confirmed to be in mcp-compose's HTTP proxy layer.

## HTTP/2 Limitation

The fix requires HTTP/2 to actually negotiate, which needs either:
- **HTTPS** (TLS/SSL)
- **hypercorn** instead of uvicorn (supports h2c)

uvicorn does NOT support HTTP/2 over plain HTTP, so the fix doesn't work in typical local dev.

## Workaround

Use environments-mcp-server directly with STDIO transport (bypasses mcp-compose):
```json
{
  "mcpServers": {
    "environments-mcp-server": {
      "command": "conda",
      "args": ["run", "-n", "your-env", "python", "-m", "environments_mcp_server", "start", "--transport", "stdio"]
    }
  }
}
```

## Files

- `ISSUE.md` - GitHub issue to raise for mcp-compose
- `PR_DESCRIPTION.md` - PR description for the fix
- `SUMMARY.md` - This file

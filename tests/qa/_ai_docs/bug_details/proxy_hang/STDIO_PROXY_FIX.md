# DESK-1409: STDIO Proxy Fix for mcp-compose Hang

## Problem Statement

mcp-compose proxy hangs after ~15-20 sequential tool calls when proxying to downstream MCP servers (environments-mcp-server).

## Investigation Timeline

### Initial Hypothesis: HTTP Connection Exhaustion

When using `streamable-http` proxy mode:
- Each tool call creates a new HTTP session to downstream server
- Rapid connect/disconnect cycles exhaust connection resources
- uvicorn stops accepting new connections at ~20 iterations
- Process stays alive but unresponsive

**Attempted Fix**: Enable HTTP/2 in `http_client.py` for connection multiplexing.

**Result**: Fix is technically correct but **doesn't work in practice** - uvicorn doesn't support HTTP/2 over plain HTTP (requires HTTPS or switching to hypercorn).

### Solution: Switch to STDIO Proxy Mode

STDIO proxy mode eliminates the HTTP layer between mcp-compose and downstream servers.

**However**, the original STDIO proxy implementation had a **response desync bug**:
- Hardcoded request IDs (`1`, `2`, `"tool-call"`)
- No matching of response ID to request ID
- Just read "next line" from stdout - responses got mixed up
- No locking for concurrent access

## Root Cause Analysis

### HTTP Transport Issues

```
Claude Desktop -> anaconda-mcp (STDIO) -> mcp-compose -> environments-mcp (HTTP)
                                              ^
                                              |
                                    Connection exhaustion here
```

Each tool call:
1. Creates new httpx client
2. Opens new TCP connection to downstream
3. Closes connection after response
4. After ~20 cycles, resources exhausted

### STDIO Transport Issues (Before Fix)

The original STDIO proxy in `mcp_compose/tool_proxy.py` had a response desync bug. It used hardcoded request IDs and simply read the next line from stdout without verifying the response ID matched the request. If the downstream server output anything unexpected (logs, notifications, delayed responses), responses would get mismatched to requests.

## The Fix

### mcp-compose PR: `stdio-proxy-fixes` branch

**File**: `mcp_compose/tool_proxy.py`

We fixed the STDIO proxy by adding proper JSON-RPC request/response matching:

1. **Unique request IDs**: Added an incrementing counter per process instead of hardcoded IDs
2. **Request serialization**: Added a lock per process to prevent concurrent request/response interleaving
3. **Response ID matching**: Changed `_send_request()` to loop and read responses until finding one with a matching ID, skipping non-JSON output and notifications
4. **Increased timeout**: Changed default from 5s to 30s to handle slower operations

### anaconda-mcp Config Change

**File**: `src/anaconda_mcp/mcp_compose.toml.template`

Switched from `[[servers.proxied.streamable-http]]` to `[[servers.proxied.stdio]]`. This eliminates the HTTP layer between mcp-compose and environments-mcp-server, using direct stdin/stdout communication instead.

## Why STDIO Works Better

| Aspect | HTTP Proxy | STDIO Proxy |
|--------|------------|-------------|
| Connection model | New TCP connection per call | Single persistent pipe |
| Resource exhaustion | Yes, at ~20 calls | No |
| Session management | Complex (session IDs, reconnect) | Simple (stdin/stdout) |
| Speed | Faster (parallel capable) | Slower (sequential) |
| Reliability | Fragile under load | Robust |

## Test Results

### Before Fix (HTTP)
- Hangs at iteration 15-20
- `TaskGroup` errors after hang
- Requires Claude Desktop restart

### After Fix (STDIO)
- **28+ sequential tool calls** without hang
- Batch operations work (deleted 7 envs, installed 15 packages)
- Listed 46 packages successfully

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/opt/miniconda3/envs/anaconda-mcp-rc2-mcpc-py313/bin/python",
      "args": ["-m", "anaconda_mcp", "serve", "--delay", "5"],
      "env": {
        "ANACONDA_MCP_PYTHON_EXECUTABLE": "/opt/miniconda3/envs/anaconda-mcp-rc2-mcpc-py313/bin/python",
        "MCP_COMPOSE_CONFIG_DIR": "/Users/iiliukhina/projects/anaconda-mcp/src/anaconda_mcp",
        "PYTHONUNBUFFERED": "1",
        "LOG_LEVEL": "DEBUG",
        "MCP_COMPOSE_LOG_LEVEL": "DEBUG",
        "CONDA_MCP_SERVER_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

**Note**: `MCP_COMPOSE_CONFIG_DIR` points to local source for editable install testing.

## Performance Comparison

| Transport | Response Time | Max Iterations | Reliability |
|-----------|---------------|----------------|-------------|
| Direct STDIO (no mcp-compose) | ~0.3s | 50+ | Excellent |
| HTTP Proxy | ~0.85s | 15-20 (hangs) | Poor |
| STDIO Proxy (with fix) | ~0.5s | 28+ | Good |

## Known Remaining Issues

1. **First tool call error**: Occasional "No response from tool execution" on first call after startup. Retry succeeds. This is a separate issue, not related to the hang.

2. **Slower than HTTP**: STDIO is sequential by nature. HTTP could be faster if the connection exhaustion issue were fixed (requires HTTPS or hypercorn).

## Files Changed

### mcp-compose Repository
- `mcp_compose/tool_proxy.py` - STDIO proxy ID matching fix

### anaconda-mcp Repository
- `src/anaconda_mcp/mcp_compose.toml.template` - Switch to STDIO proxy
- `src/anaconda_mcp/mcp_compose.toml` - Switch to STDIO proxy (fallback)

## Related Links

- DESK-1409: Original bug report
- mcp-compose PR: `stdio-proxy-fixes` branch
- Previous HTTP/2 fix attempt: `mcp_compose/http_client.py`

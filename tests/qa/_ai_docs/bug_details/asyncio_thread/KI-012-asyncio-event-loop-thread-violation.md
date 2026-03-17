# KI-012: Asyncio Event Loop Thread Violation in create_environment

## Summary

`conda_create_environment` fails with "Non-thread-safe operation invoked on an event loop other than the current one" error. The operation fails but does not corrupt process state - subsequent requests succeed.

## Status

- **Severity**: Low (production) / Medium (debug mode)
- **Component**: environments_mcp_server (conda transaction layer)
- **Related**: May be related to KI-011 (proxy hang) - both involve async operation issues
- **Root cause**: Thread-safety violation exposed by `PYTHONASYNCIODEBUG=1`

## Key Finding

**The bug only manifests when `PYTHONASYNCIODEBUG=1` is set.**

- With `PYTHONASYNCIODEBUG=1`: `create_environment` fails with thread-safety error
- Without `PYTHONASYNCIODEBUG=1`: `create_environment` works normally

This means:
1. A real thread-safety violation exists in the code
2. Python's asyncio debug mode enforces strict checks and raises the error
3. In production (without debug flag), the violation is **silent**
4. The underlying bug could still cause intermittent issues or race conditions

## Error Message

```
('conda:transaction:failed', 'Transaction execution failed: Non-thread-safe operation invoked on an event loop other than the current one', 'f0ac614157844a878107af780f4ae414')
```

## End User Impact

**Affected users**: Claude Desktop users with Anaconda MCP

### What happens

1. User asks Claude to create a conda environment
2. Tool call fails with transaction error
3. User sees error message about operation failure
4. Subsequent operations (like `list_environments`) still work

### User experience

- **Symptom**: Environment creation fails with cryptic error
- **Recovery**: Automatic - no restart needed
- **Workaround**: Retry may work, or create environment manually

## Environment

- **anaconda-mcp version**: 1.26.0
- **Transport**: STDIO (observed), likely affects HTTP too
- **Python**: 3.13
- **OS**: macOS

## Reproduction

### Steps

1. Start Claude Desktop with anaconda-mcp configured
2. Ask: "Create a conda environment called test-env"
3. Observe error in response

### Logs (2026-03-17)

```
2026-03-17T21:02:22.693Z [anaconda-mcp] [info] Message from client: {"method":"tools/call","params":{"name":"conda_create_environment","arguments":{"environment_name":"anaconda-mcp-rc2-c111-py313-3","environment_root_path":"/opt/miniconda3/envs"}},"jsonrpc":"2.0","id":5}

2026-03-17 17:02:22 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-03-17 17:02:22 - httpx - INFO - HTTP Request: POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
2026-03-17 17:02:22 - mcp.client.streamable_http - INFO - Received session ID: 96a1f28930ee4e6fb92c743b33efe937
2026-03-17 17:02:22 - mcp.client.streamable_http - INFO - Negotiated protocol version: 2025-11-25
2026-03-17 17:02:22 - httpx - INFO - HTTP Request: POST http://localhost:4041/mcp "HTTP/1.1 202 Accepted"
2026-03-17 17:02:22 - httpx - INFO - HTTP Request: GET http://localhost:4041/mcp "HTTP/1.1 200 OK"
2026-03-17 17:02:22 - httpx - INFO - HTTP Request: POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
2026-03-17 17:02:23 - httpx - INFO - HTTP Request: POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
2026-03-17 17:02:23 - httpx - INFO - HTTP Request: DELETE http://localhost:4041/mcp "HTTP/1.1 200 OK"

2026-03-17T21:02:23.482Z [anaconda-mcp] [info] Message from server: {"jsonrpc":"2.0","id":5,"result":{"content":[{"type":"text","text":"{\"is_error\":true,\"error_description\":\"('conda:transaction:failed', 'Transaction execution failed: Non-thread-safe operation invoked on an event loop other than the current one', 'f0ac614157844a878107af780f4ae414')\",\"tool_result\":{}}"}],"isError":false}}
```

**Note**: The HTTP request cycle completed normally (including DELETE) - the error is in the tool execution, not the transport.

## Key Observations

1. **Error is in conda transaction layer** - not mcp-compose or MCP protocol
2. **Transport completes normally** - full POST→GET→POST→POST→DELETE cycle
3. **Process recovers** - subsequent `list_environments` (id:6) succeeded
4. **Asyncio threading violation** - code running on wrong event loop

## Technical Analysis

### Error origin

The error message format `('conda:transaction:failed', ...)` suggests:
- Error originates in `environments_mcp_server`
- Specifically in conda transaction execution
- Involves `conda-libmamba-solver` or similar async code

### Asyncio issue

"Non-thread-safe operation invoked on an event loop other than the current one" indicates:
- An async operation was scheduled on the wrong event loop
- Likely a subprocess or thread callback trying to use the main event loop
- Could be in:
  - Conda subprocess execution
  - libmamba solver callbacks
  - Transaction commit/rollback handling

### Difference from KI-011 (proxy hang)

| Aspect | KI-011 (Hang) | KI-012 (This bug) |
|--------|---------------|-------------------|
| Symptom | Silent hang, no response | Error returned |
| Transport | Incomplete (missing DELETE) | Complete cycle |
| Recovery | Requires restart | Automatic |
| Corruption | Process-wide (TaskGroup error) | None |
| Component | mcp-compose | environments_mcp_server |

## Hypothesis

The `create_environment` tool may:
1. Run conda subprocess in a thread pool
2. Subprocess callback tries to interact with asyncio event loop
3. Callback runs on thread pool thread, not main event loop thread
4. Python raises RuntimeError for thread-safety violation

## Workaround

**Remove `PYTHONASYNCIODEBUG=1` from environment configuration.**

The bug is silent without this flag, and `create_environment` works normally. However, the underlying thread-safety issue remains and should be fixed.

## Potential Fixes

1. **Use `asyncio.run_coroutine_threadsafe()`** for cross-thread async calls
2. **Use `loop.call_soon_threadsafe()`** for scheduling from threads
3. **Ensure subprocess callbacks don't touch event loop** directly
4. **Review conda-libmamba-solver integration** for async patterns

## Files

- Log: `tests/qa/_ai_docs/bug_details/asyncio_thread/reproduction_log_20260317.txt` (to be added)

## Related Issues

| Issue | Relationship |
|-------|--------------|
| KI-011 | Different bug - proxy hang vs transaction error |
| DESK-1355 | May be related - both involve async operation issues |

## Next Steps

1. Add deeper logging to `environments_mcp_server` transaction handling
2. Identify exact line where event loop violation occurs
3. Review conda subprocess execution pattern
4. Test with different conda solvers (classic vs libmamba)

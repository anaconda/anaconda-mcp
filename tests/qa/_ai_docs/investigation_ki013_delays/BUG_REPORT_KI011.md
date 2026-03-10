# Bug Report: `logger.exception()` causes MCP server hang after ~15 tool calls

**Date**: 2026-03-10
**Severity**: High
**Component**: `environments_mcp_server`
**Affects**: Any MCP client making >15 error-triggering tool calls per session
**Transports Affected**: HTTP (Streamable) and STDIO — transport-independent

---

## Summary

Repeated calls to `logger.exception()` in exception handlers cause the `environments_mcp_server` to stop processing new requests after approximately 15 calls. The server accepts HTTP connections but never dispatches requests to tool functions, resulting in a 60-second timeout and client hang.

---

## Impact

- **Production Impact**: Any MCP client (Cursor, Claude Desktop, Claude Code) making more than ~15 tool calls that trigger exceptions will experience hangs
- **Session Recovery**: Requires full server restart — no automatic recovery
- **User Experience**: Appears as unresponsive AI assistant after extended usage

---

## Root Cause

`logger.exception()` calls in exception handlers accumulate state that eventually blocks the MCP request dispatch layer.

**Problematic Code** (`environments_mcp_server/tools/environments/install_packages.py:101-102`):
```python
except conda_exceptions.EnvironmentLocationNotFound as ex:
    logger.exception(ex)  # <-- CAUSES HANG AFTER ~15 CALLS
    return ServerToolResult(...)
```

---

## Steps to Reproduce

### Prerequisites
- `environments-mcp-server` 1.0.0.rc.3
- `mcp-compose` 0.1.11
- `mcp` SDK 1.26.0

### Reproduction Steps

1. Start HTTP server:
```bash
conda activate anaconda-mcp-dev
./tests/qa/_ai_docs/scripts/start-http-server.sh 9888 5041
```

2. Run hang regression test:
```bash
python -m pytest tests/qa/http_tools/test_guard_proxy_error_hang.py::TestProxyErrorHangHttp::test_hang_002_install_into_nonexistent_env_does_not_hang -v
```

3. **Expected**: Test passes all 20 iterations
   **Actual**: Test hangs at iteration 15-16

### Minimal Reproduction

Call `conda_install_packages` with a non-existent prefix 15+ times:
```python
for i in range(20):
    response = call_tool("conda_install_packages", {
        "prefix": "/nonexistent/path",
        "packages": ["some-package"]
    })
    # Iterations 1-14: ~0.1s response
    # Iteration 15+: 60s timeout, hang
```

---

## Evidence

### Server Logs Show Request Never Reaches Tool Function

```
# Iteration 14 (last successful):
18:35:54,027 INFO [PATH] Calling conda.install() with prefix=/tmp/nonexistent...
18:35:54,030 INFO [PATH] Caught EnvironmentLocationNotFound

# Iteration 15 (HANG):
# NO LOG ENTRY — request never dispatched to install_packages function
```

### mcp-compose Logs Show Request Was Received

```
18:35:53 - Processing request of type CallToolRequest
18:35:54 - HTTP Request: POST http://localhost:5041/mcp "HTTP/1.1 200 OK"
18:36:54 - GET stream disconnected, reconnecting in 1000ms...
```

**60-second gap** between request and disconnect = request stuck in dispatch layer.

---

## Hypotheses Tested

| Hypothesis | Test | Result |
|------------|------|--------|
| mcp-compose proxy issue | Mock tool returning same response | ✅ PASSED — proxy is innocent |
| Timing/rate issue | Added 3-second delays between calls | ❌ Still hangs at ~15 |
| `conda.install()` issue | Skipped install, returned mock | ✅ PASSED — install() is innocent |
| `get_conda()` issue | Called get_conda() only | ✅ PASSED — get_conda() is innocent |
| `logger.exception()` issue | Commented out logger.exception() | ✅ **PASSED — ROOT CAUSE** |
| STDIO transport | Ran same test over STDIO | ❌ Same hang at ~15 — transport-independent |

---

## Confirmed Findings

1. **Bug is in `environments_mcp_server`**, not mcp-compose or MCP SDK
2. **`logger.exception()` is the root cause** — commenting it out fixes the issue
3. **Hang occurs at ~15 iterations** regardless of:
   - Request timing (tested with 0s, 2s, 3s delays)
   - Concurrent clients (tested in isolation)
   - Port configuration (tested on 9888/5041)
4. **`remove_environment` passes** because it catches `CondaEnvironmentNotFoundError` which does NOT call `logger.exception()`
5. **`install_packages` hangs** because it catches `EnvironmentLocationNotFound` which DOES call `logger.exception()`

---

## Recommended Fix

### Option 1: Replace `logger.exception()` with `logger.warning()`

```python
# BEFORE:
except conda_exceptions.EnvironmentLocationNotFound as ex:
    logger.exception(ex)
    return ServerToolResult(...)

# AFTER:
except conda_exceptions.EnvironmentLocationNotFound as ex:
    logger.warning(f"Environment not found: {ex}")
    return ServerToolResult(...)
```

### Option 2: Investigate logging configuration

Check if:
- Logging handlers have file descriptor limits
- Async logging conflicts with MCP's event loop
- Telemetry middleware intercepts logging calls

---

## Affected Files

| File | Line | Issue |
|------|------|-------|
| `install_packages.py` | 102 | `logger.exception(ex)` in `EnvironmentLocationNotFound` handler |
| `install_packages.py` | 109 | `logger.exception(ex)` in `ResolvePackageNotFound` handler |
| `install_packages.py` | 127 | `logger.exception(...)` in generic `Exception` handler |

Similar patterns may exist in other tool files.

---

## Workaround

Until fixed, users can:
1. Restart the server after extended usage
2. Avoid operations that trigger repeated exceptions

---

## Test Environment

- macOS Darwin 25.2.0 (arm64)
- Python 3.13
- `environments-mcp-server`: 1.0.0.rc.3
- `mcp-compose`: 0.1.11
- `mcp` SDK: 1.26.0
- `anaconda-connector-conda`: (bundled)

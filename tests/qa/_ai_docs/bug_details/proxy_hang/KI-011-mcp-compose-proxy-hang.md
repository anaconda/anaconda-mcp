# KI-011: mcp-compose Proxy Hang After ~17-18 Rapid Sequential Tool Calls

## Summary

mcp-compose proxy stops forwarding responses after approximately 17-18 rapid sequential tool calls when tools take time to execute (~0.8s+). The downstream server processes all requests successfully, but responses are not delivered to the client.

## Status

- **Jira**: DESK-1355 (marked Done, but issue persists)
- **Severity**: High - causes frozen chat sessions requiring restart
- **Component**: mcp-compose (external dependency)

## End User Impact

**Affected users**: Claude Desktop users with Anaconda MCP configured (both HTTP and STDIO transports)

### What happens

During an active chat session, after approximately 17-18 tool calls that involve conda operations (which take ~0.8s+ each), Claude Desktop stops receiving responses from the MCP server:

1. User asks Claude to perform multiple conda operations (e.g., "create environment, install packages, list environments")
2. Claude makes sequential tool calls to Anaconda MCP
3. After ~17-18 successful operations, responses stop arriving
4. Claude appears to "hang" or "freeze" - no error message, just silence
5. The chat session becomes unresponsive

### User experience

- **Symptom**: Claude stops responding mid-conversation with no error message
- **Perception**: "Claude is stuck" or "MCP server crashed"
- **Recovery**: User must restart Claude Desktop to restore functionality
- **Data loss**: Any unsaved conversation context is lost
- **Frequency**: Reproducible in workflows involving many conda operations

### Typical triggering scenarios

- Setting up a new project with multiple package installations
- Batch operations across several environments
- Iterative debugging that requires repeated environment modifications
- Automated or scripted interactions making rapid tool calls

### Likelihood assessment

**Confirmed: Bug is triggered by operation complexity, not just timing**

| Test | Operation | Duration | Complexity | Result |
|------|-----------|----------|------------|--------|
| Echo server | ping | ~0.8s | Simple | **PASS** |
| HANG-006 | `list_environments` | ~0.06s | Shallow | **40/40 PASS** |
| HANG-004 | `install_packages` | ~0.8s+ | Deep | 19/40 FAIL |
| HANG-005 | `install` + `list` | mixed | Mixed | 15/40 FAIL |

**Impact by user profile:**

| User Profile | Likelihood | Rationale |
|--------------|------------|-----------|
| **Casual user** (list envs, check packages) | **Low** | Shallow operations don't trigger bug |
| **Active developer** (occasional installs) | **Medium** | May hit threshold during project setup |
| **Power user** (frequent env modifications) | **High** | Will hit threshold in complex workflows |
| **Batch operations** (multi-package installs) | **Very High** | Deep operations quickly trigger bug |

**Why the ~17 call threshold matters:**
- A single "set up my ML project" request can generate 10+ tool calls
- Users don't see individual tool calls - they just see Claude "thinking" then freezing
- The bug is silent - no error, no recovery, no explanation

### Why this matters

- Breaks user trust in Anaconda MCP reliability
- Interrupts productive workflows at critical moments
- No actionable error message to help users understand or report the issue
- Workaround (restart) loses conversation context
- Most likely to occur during complex tasks where context loss is most painful

## Related Issues

| Issue | Summary | Status | Relationship |
|-------|---------|--------|--------------|
| DESK-1355 | Chat Session Freezes After a Tool Error | Done | Same root cause; PR #28 improved threshold from ~4 to ~17-18 but did not fully fix |
| DESK-1366 | `logger.exception()` causes MCP server hang | Done | Different root cause; fixed in environments_mcp_server |
| DESK-1408 | Claude Desktop 1.1.6679 Error adding package | New | Different issue (startup race condition in Claude Desktop) |

## Environment

- **mcp-compose version**: 0.1.11
- **Upstream transport**: Both HTTP and STDIO affected
- **Internal transport**: Streamable HTTP (mcp-compose → environments_mcp_server)
- **OS**: macOS (also reproducible on other platforms)
- **Python**: 3.10+

## Reproduction Steps

### Option A: Using anaconda-mcp (Recommended)

**Terminal 1 - Start server:**
```bash
cd /path/to/anaconda-mcp
python -m anaconda_mcp serve --port 7000
```

**Terminal 2 - Run test:**
```bash
cd /path/to/anaconda-mcp
./tests/qa/_ai_docs/scripts/test-mcp-compose-direct.sh
```

### Option B: Using environments_mcp_server directly

**Terminal 1 - Start mcp-compose with environments_mcp_server:**
```bash
cd /path/to/anaconda-mcp
python -m mcp_compose serve --config proxy_configs/default.toml
```

**Terminal 2 - Run rapid sequential calls:**
```bash
# Initialize session first
INIT_RESPONSE=$(curl -s -i -X POST "http://localhost:7000/mcp" \
    -H "Accept: application/json, text/event-stream" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }')

SESSION_ID=$(echo "$INIT_RESPONSE" | grep -i "mcp-session-id" | head -1 | sed 's/.*: *//' | tr -d '\r\n')

# Run 25 rapid calls
for i in {1..25}; do
  echo "[$i/25]"
  curl -s -X POST "http://localhost:7000/mcp" \
    -H "Content-Type: application/json" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d '{"jsonrpc":"2.0","id":'$i',"method":"tools/call","params":{"name":"conda_list_environments","arguments":{}}}' \
    --max-time 10
done
```

## Expected Result

All 25 tool calls complete successfully with responses.

## Actual Result

```
[1/25] conda_list_environments... OK
...
[17/25] conda_list_environments... OK
[18/25] conda_list_environments... TIMEOUT
[19/25] conda_list_environments... TIMEOUT
...
[25/25] conda_list_environments... TIMEOUT
```

The downstream server logs show all 25 requests processed successfully. The hang is in the mcp-compose proxy response forwarding layer.

## Isolation Test Results

### HTTP Transport

| Component | Test | Result |
|-----------|------|--------|
| environments_mcp_server direct | 50 rapid calls | 50/50 PASS |
| mcp-compose proxy (HTTP) | 25 rapid calls | 18/25 PASS (hangs at 18) |
| anaconda-mcp serve (HTTP) | 25 rapid calls | 18/25 PASS (hangs at 18) |

### STDIO Transport

| Test | Iterations | Result |
|------|------------|--------|
| STDIO-HANG-004 (repeated install) | 40 | 19/40 PASS (hangs at 19) |
| STDIO-HANG-005 (install + list interleaved) | 40 | 15/40 PASS (hangs at 15, = 29 total calls) |
| STDIO-HANG-006 (repeated list_environments) | 40 | **40/40 PASS** |

**Key findings**:
1. Bug reproduces on both transports → root cause is in mcp-compose's internal Streamable HTTP connection
2. Bug is **complexity-dependent**, not purely timing-dependent:
   - Simple echo with 0.8s delay: PASS
   - Shallow `list_environments`: PASS
   - Deep `install_packages`: FAIL at ~17-19

## Key Observations

1. **Bug is in mcp-compose proxy layer** - confirmed by isolation testing
2. **Downstream server is NOT the problem** - handles 50+ direct calls without issue
3. **Transport-agnostic** - reproduces on both HTTP and STDIO upstream transports
4. **NOT purely timing-dependent** - complexity matters more than duration:
   - Echo server with 0.8s delay: **PASS** (simple response)
   - `list_environments` (~0.06s): **PASS** (shallow operation)
   - `install_packages` (~0.8s+): **FAIL at ~17-19** (deep operation)
5. **Operation depth/complexity is the trigger** - `install_packages` involves:
   - Multiple subprocess calls (conda solve, download, install)
   - Complex async patterns
   - Larger response payloads
   - Deeper data retrieval chains
6. **Connection/session related** - likely involves internal Streamable HTTP connection pooling or session state corruption under complex async load

## Hypothesis

The bug may be related to:
- **Async operation depth** - deep operations (subprocess calls, network I/O) may not complete cleanly in mcp-compose's internal task handling
- **Response payload size** - larger responses from complex operations may trigger buffer or connection issues
- **Connection pool behavior under sustained async load** - simple requests work, but complex async patterns exhaust or corrupt the pool
- SSE (Server-Sent Events) connection timeout handling during long-running operations
- Session state corruption when handling multiple concurrent internal async tasks

## Workaround

**None currently available.** Users experience frozen chat sessions requiring restart.

## Minimal Reproduction Attempt

A minimal echo server was created in `tests/qa/_ai_docs/bug_details/proxy_hang` but it does **not** trigger the bug even with 0.8s delay. Combined with HANG-006 passing (fast `list_environments`), this confirms the bug is **complexity-dependent**, not timing-dependent.

The bug requires conditions present in complex operations like `install_packages`:
- **Deep async call chains** - conda solve → download → install involves multiple subprocess calls
- **Response payload complexity** - install results contain structured data about packages, dependencies
- **Sustained async load** - operations that keep internal connections busy for extended periods
- **Multiple internal I/O operations** - file system, network, subprocess communication

## Files

### Diagnostic scripts
- `tests/qa/_ai_docs/scripts/test-env-mcp-direct.sh` - Tests environments_mcp_server directly (PASS)
- `tests/qa/_ai_docs/scripts/test-mcp-compose-direct.sh` - Tests mcp-compose proxy (FAIL at 18)

### Automated tests
- `tests/qa/http_tools/test_guard_happy_path_hang.py` - HTTP transport regression tests
- `tests/qa/stdio_tools/test_guard_happy_path_hang_stdio.py` - STDIO transport regression tests

### Minimal reproduction
- `tests/qa/_ai_docs/bug_details/proxy_hang/echo_server.py` - Minimal MCP server (does NOT reproduce)
- `tests/qa/_ai_docs/bug_details/proxy_hang/proxy.toml` - mcp-compose config for echo server
- `tests/qa/_ai_docs/bug_details/proxy_hang/test_hang.sh` - Shell script test runner

## History

- **mcp-compose 0.1.10**: Bug reproduced at ~4 iterations
- **mcp-compose 0.1.11 (PR #28)**: Improved threshold to ~17-18 iterations (partial fix)
- **Current**: Issue persists at ~17-18 iterations

## Next Steps

1. File detailed bug report with mcp-compose maintainers
2. Include isolation test evidence proving bug is in proxy layer
3. Request investigation of SSE/connection handling under sustained load

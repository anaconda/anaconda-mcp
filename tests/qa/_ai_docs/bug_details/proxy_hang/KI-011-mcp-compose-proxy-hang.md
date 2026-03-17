# KI-011: mcp-compose Proxy Hang After ~17-18 Rapid Sequential Tool Calls

## Summary

mcp-compose proxy stops forwarding responses after approximately 17-18 rapid sequential tool calls when tools take time to execute (~0.8s+). The downstream server processes all requests successfully, but responses are not delivered to the client.

## Status

- **Jira**: DESK-1355 (marked Done, but issue persists)
- **Severity**: High - causes frozen chat sessions requiring restart
- **Component**: mcp-compose (external dependency)

## End User Impact

**Affected users**: Claude Desktop users with Anaconda MCP configured (HTTP transport)

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

### Why this matters

- Breaks user trust in Anaconda MCP reliability
- Interrupts productive workflows at critical moments
- No actionable error message to help users understand or report the issue
- Workaround (restart) loses conversation context

## Related Issues

| Issue | Summary | Status | Relationship |
|-------|---------|--------|--------------|
| DESK-1355 | Chat Session Freezes After a Tool Error | Done | Same root cause; PR #28 improved threshold from ~4 to ~17-18 but did not fully fix |
| DESK-1366 | `logger.exception()` causes MCP server hang | Done | Different root cause; fixed in environments_mcp_server |
| DESK-1408 | Claude Desktop 1.1.6679 Error adding package | New | Different issue (startup race condition in Claude Desktop) |

## Environment

- **mcp-compose version**: 0.1.11
- **Transport**: Streamable HTTP
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

| Component | Test | Result |
|-----------|------|--------|
| environments_mcp_server direct | 50 rapid calls | 50/50 PASS |
| mcp-compose proxy | 25 rapid calls | 18/25 PASS (hangs at 18) |
| anaconda-mcp serve | 25 rapid calls | 18/25 PASS (hangs at 18) |

## Key Observations

1. **Bug is in mcp-compose proxy layer** - confirmed by isolation testing
2. **Downstream server is NOT the problem** - handles 50+ direct calls without issue
3. **Timing-dependent** - only occurs with tools that take time (~0.8s+)
4. **Instant tools work** - DELAY=0 does not trigger the bug
5. **Connection/session related** - likely involves connection pooling, SSE handling, or session state
6. **Simple echo server does NOT reproduce** - suggests bug may be triggered by response size, multiple tool registrations, or specific async patterns

## Hypothesis

The bug may be related to:
- SSE (Server-Sent Events) connection timeout handling
- Connection pool exhaustion under rapid sequential requests
- Session state corruption after multiple concurrent responses
- Keep-alive connection reuse issues

## Workaround

**None currently available.** Users experience frozen chat sessions requiring restart.

## Minimal Reproduction Attempt

A minimal echo server was created in `tests/qa/_ai_docs/bug_details/proxy_hang` but it does **not** trigger the bug even with 0.8s delay. This suggests the bug requires specific conditions present in environments_mcp_server:
- Response size/complexity
- Multiple tool registrations
- Specific async patterns

## Files

- `tests/qa/_ai_docs/scripts/test-env-mcp-direct.sh` - Tests environments_mcp_server directly (PASS)
- `tests/qa/_ai_docs/scripts/test-mcp-compose-direct.sh` - Tests mcp-compose proxy (FAIL at 18)
- `tests/qa/http_tools/test_guard_happy_path_hang.py` - Pytest that reproduces the issue

## History

- **mcp-compose 0.1.10**: Bug reproduced at ~4 iterations
- **mcp-compose 0.1.11 (PR #28)**: Improved threshold to ~17-18 iterations (partial fix)
- **Current**: Issue persists at ~17-18 iterations

## Next Steps

1. File detailed bug report with mcp-compose maintainers
2. Include isolation test evidence proving bug is in proxy layer
3. Request investigation of SSE/connection handling under sustained load

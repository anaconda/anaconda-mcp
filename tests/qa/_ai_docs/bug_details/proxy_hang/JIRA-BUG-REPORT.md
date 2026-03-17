# Jira Bug Report: MCP Proxy Hang

**Jira**: [DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409)

---

## Title

Claude Desktop chat freezes after ~17 conda_install_packages calls (mcp-compose proxy hang)

## Summary

Claude Desktop chat becomes unresponsive after approximately 17 sequential `conda_install_packages` tool calls during normal user workflow. The user sees Claude "thinking" indefinitely with no response or error message. After ~4 minutes, a timeout occurs, and all subsequent MCP requests fail until Claude Desktop is restarted.

**Reproduction scenario**: User creates a conda environment, then installs packages one by one (pyyaml, requests, six, python-dateutil, pytz, packaging, attrs...). Around the 11th-14th package install (~17th total tool call), the chat freezes.

**Relation to DESK-1355**: This issue belongs to the same category as [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355) (Chat Session Freezes After Tool Error), which was fixed in mcp-compose PR #28. That fix improved the hang threshold from ~4 to ~17 tool calls but did not fully resolve the underlying issue. DESK-1355 was triggered by tool errors returned in correct format; this case occurs during **successful `conda_install_packages` operations** when responses stop being forwarded after ~17 sessions.

**Root cause**: After ~17 tool call sessions, the mcp-compose proxy stops forwarding responses from the downstream server. The SSE stream times out after 30 seconds of waiting, and internal TaskGroup state becomes corrupted.

## Severity

**High** - Causes frozen Claude Desktop chat sessions requiring restart. Most likely to occur during productive workflows like setting up new projects with multiple package installations.

## Component

- mcp-compose (primary)
- Potentially environments_mcp_server SSE handling

## User-Visible Symptoms (Claude Desktop)

1. User is chatting normally, asking Claude to perform conda operations
2. After ~17 tool calls, Claude shows "thinking" spinner but never responds
3. No error message is displayed - just indefinite waiting
4. After ~4 minutes, Claude may show "tool didn't return a result"
5. User tries another request - fails with internal error
6. Chat is completely frozen - no MCP tools work
7. User must restart Claude Desktop to recover
8. Conversation context may be lost

## Environment

| Component | Version |
|-----------|---------|
| mcp-compose | 0.1.11 |
| anaconda-mcp | 1.26.0 |
| Python | 3.13 |
| OS | macOS Darwin 25.2.0 |
| Claude Desktop | Latest |
| Transport | STDIO (upstream), Streamable HTTP (internal) |

## Steps to Reproduce

1. Configure Claude Desktop with anaconda-mcp:
```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/path/to/python",
      "args": ["-m", "anaconda_mcp", "serve", "--delay", "15"]
    }
  }
}
```

2. Start Claude Desktop, open new chat

3. Create a conda environment:
   > "Create conda environment called test-hang"

4. Install packages one by one (each as separate message):
   - pyyaml
   - requests
   - urllib3
   - certifi
   - charset-normalizer
   - idna
   - six
   - python-dateutil
   - pytz
   - packaging
   - attrs

5. Observe hang around package 11-14 (request ~17)

## Expected Result

All package installations complete successfully. Claude responds to each request.

## Actual Result

1. First ~16 requests succeed normally
2. Request ~17 (e.g., "install attrs") hangs - no response
3. After 4 minutes, Claude shows timeout
4. All subsequent requests fail with error:
   ```
   Error executing tool: unhandled errors in a TaskGroup (1 sub-exception)
   ```
5. Must restart Claude Desktop to recover

## Root Cause (Identified)

MCP log shows SSE stream disconnects after exactly 30 seconds:
```
17:39:55 - GET http://localhost:4041/mcp "HTTP/1.1 200 OK"   <- SSE stream opened
17:39:55 - POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
... 30 SECONDS - NO RESPONSE ARRIVES ...
17:40:25 - GET stream disconnected, reconnecting in 1000ms... <- TIMEOUT
```

The response stops being forwarded after ~17 requests. The 30-second timeout is when the client gives up waiting.

## Evidence Files

| File | Description |
|------|-------------|
| `mcp_log_20260317_174021.log` | MCP log showing SSE disconnect message |
| `diagnostics_20260317_174021.txt` | Live capture during hang showing ESTABLISHED connections |
| `claude_desktop_hang_chat_3.log` | User-visible chat showing hang |

## Key Log Evidence

**SSE stream disconnect (from MCP log):**
```
17:40:25 - mcp.client.streamable_http - INFO - GET stream disconnected, reconnecting in 1000ms...
```

**TaskGroup error (post-hang):**
```
{"jsonrpc":"2.0","id":18,"result":{"content":[{"type":"text","text":"Error executing tool conda_list_environments: unhandled errors in a TaskGroup (1 sub-exception)"}],"isError":true}}
```

**Connection state during hang (from lsof):**
```
python3.1 1352  localhost:59613->localhost:4041 (ESTABLISHED)  <- mcp-compose
python3.1 1508  localhost:4041 (LISTEN)                        <- server healthy
```

## Suggested Investigation

1. **mcp.client.streamable_http** - Find SSE stream timeout configuration
2. **mcp_compose/tool_proxy.py** - TaskGroup error handling
3. Why responses stop being forwarded after ~17 sessions
4. Why reconnection doesn't recover pending requests

## Suggested Fixes

1. Add keepalive/heartbeat during long operations
2. Increase SSE read timeout (configurable)
3. Improve TaskGroup error isolation (don't poison all requests)
4. Fix reconnection to recover pending requests

## Related Issues

| Issue | Relationship |
|-------|--------------|
| DESK-1355 | Same category (mcp-compose proxy hang). PR #28 improved threshold from ~4 to ~17 calls. DESK-1355 was triggered by **tool errors in correct format**; this issue occurs during **successful operations**. Both result in frozen Claude Desktop chat. |

## Workaround

None. User must restart Claude Desktop after hang occurs.

---

## Attachments Checklist

- [ ] `mcp_log_20260317_174021.log`
- [ ] `diagnostics_20260317_174021.txt`
- [ ] `claude_desktop_hang_chat_3.log`
- [ ] Link to full technical analysis (if internal wiki available)

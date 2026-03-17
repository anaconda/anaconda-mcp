# Evidence Index: MCP Proxy Hang

Catalog of all evidence files for KI-011.

## Key Evidence (Attach to Jira)

| File | Date | What It Proves |
|------|------|----------------|
| `diagnostics_20260317_174021.txt` | 2026-03-17 | **Live capture during hang** - shows ESTABLISHED connections, process state |
| `mcp_log_20260317_174021.log` | 2026-03-17 | **SSE disconnect message** - "GET stream disconnected, reconnecting in 1000ms..." |
| `claude_desktop_hang_chat_3.log` | 2026-03-17 | User-visible hang experience |

## Diagnostic Captures

### diagnostics_20260317_174021.txt

**Captured**: While Claude Desktop was hanging (before closing)

**Key findings**:
```
=== Port 4041 connections ===
python3.1 1352  localhost:59613->localhost:4041 (ESTABLISHED)  <- mcp-compose client
python3.1 1352  localhost:59611->localhost:4041 (ESTABLISHED)  <- second connection
python3.1 1508  localhost:4041 (LISTEN)                        <- server healthy
python3.1 1508  localhost:4041->localhost:59613 (ESTABLISHED)  <- server accepting
python3.1 1508  localhost:4041->localhost:59611 (ESTABLISHED)  <- server accepting

=== Netstat port 4041 ===
tcp4  127.0.0.1.59607  127.0.0.1.4041  TIME_WAIT   <- Recent closed sessions
tcp4  127.0.0.1.59610  127.0.0.1.4041  TIME_WAIT
```

**Proves**:
- Connections were ESTABLISHED during hang (not CLOSED)
- Downstream server was healthy (LISTEN)
- Multiple sessions had been created (TIME_WAIT from previous)

## MCP Logs

### mcp_log_20260317_174021.log

**The smoking gun** - SSE stream timeout:
```
17:39:55 - GET http://localhost:4041/mcp "HTTP/1.1 200 OK"   <- SSE stream opened
17:39:55 - POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
... 30 SECONDS ...
17:40:25 - GET stream disconnected, reconnecting in 1000ms... <- TIMEOUT!
```

**Proves**:
- Exactly 30 seconds between stream open and disconnect
- Reconnection is attempted but doesn't recover

### claude_desktop_hang_mcp_3_actual.log

Earlier capture showing full request sequence and TaskGroup errors.

### claude_desktop_hang_mcp_2.log

Shows TaskGroup error pattern post-hang:
```
id:17 - install attrs -> HUNG
id:18 - "unhandled errors in a TaskGroup (1 sub-exception)"
id:19 - "unhandled errors in a TaskGroup (1 sub-exception)"
```

### claude_desktop_hang_mcp_1.log

First reproduction MCP log with protocol flow analysis.

## Chat Logs

### claude_desktop_hang_chat_3.log

User experience during third reproduction:
- list envs -> OK
- create env -> OK
- install pyyaml through packaging -> OK
- install attrs -> "tool didn't return a result"
- list envs -> error
- list envs retry -> error

### claude_desktop_hang_chat_2.log

Second reproduction chat log.

### claude_desktop_hang_chat.log

First reproduction chat log.

## Scripts

### capture-hang-diagnostics.sh

Automated script to capture evidence during hang:
- lsof output for port 4041
- netstat connection states
- Process list
- Open files for relevant PIDs
- Current MCP log copy

**Usage**: Run while Claude Desktop is hanging, before closing it.

### test-mcp-compose-direct.sh

Direct curl test bypassing Claude Desktop.

### test-env-mcp-direct.sh

Tests environments_mcp_server directly (proves server is not the issue).

## Log Excerpts

### Successful Request Pattern
```
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"     <- Session init
Received session ID: abc123
POST http://localhost:4041/mcp "HTTP/1.1 202 Accepted"
GET http://localhost:4041/mcp "HTTP/1.1 200 OK"      <- SSE stream
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"     <- Tool result
DELETE http://localhost:4041/mcp "HTTP/1.1 200 OK"   <- Cleanup
Message from server: {"jsonrpc":"2.0","id":N,"result":...}
```

### Failed Request Pattern
```
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
Received session ID: xyz789
POST http://localhost:4041/mcp "HTTP/1.1 202 Accepted"
GET http://localhost:4041/mcp "HTTP/1.1 200 OK"
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
... 30 SECONDS SILENCE ...
GET stream disconnected, reconnecting in 1000ms...
# MISSING: second POST 200, DELETE 200, Message from server
```

### Post-Hang Error Pattern
```
Message from client: {"method":"tools/call",...,"id":18}
Message from server: {"jsonrpc":"2.0","id":18,"result":{"content":[{"type":"text","text":"Error executing tool: unhandled errors in a TaskGroup (1 sub-exception)"}],"isError":true}}
```

## Evidence Timeline

| Time | Event | File |
|------|-------|------|
| 17:36:XX | Session started | mcp_log |
| 17:37-17:39 | Requests 1-16 succeed | mcp_log |
| 17:39:55 | Request 17 starts | mcp_log |
| 17:39:55 | SSE stream opened | mcp_log |
| 17:40:21 | Diagnostics captured | diagnostics_*.txt |
| 17:40:25 | SSE stream timeout (30s) | mcp_log |
| 17:40:25 | "GET stream disconnected" | mcp_log |
| 17:41+ | Requests 18+ fail | mcp_log |

## File Locations

All evidence in: `tests/qa/_ai_docs/bug_details/proxy_hang/`

```
proxy_hang/
├── JIRA-BUG-REPORT.md          <- Copy to Jira
├── INVESTIGATION-GUIDE.md      <- How to debug
├── TECHNICAL-ANALYSIS.md       <- Root cause + diagrams
├── EVIDENCE-INDEX.md           <- This file
├── KI-011-mcp-compose-proxy-hang.md  <- Master document
│
├── diagnostics_20260317_174021.txt   <- KEY: Live capture
├── mcp_log_20260317_174021.log       <- KEY: SSE disconnect
│
├── claude_desktop_hang_chat.log
├── claude_desktop_hang_chat_2.log
├── claude_desktop_hang_chat_3.log
├── claude_desktop_hang_mcp_1.log
├── claude_desktop_hang_mcp_2.log
├── claude_desktop_hang_mcp_3.log
├── claude_desktop_hang_mcp_3_actual.log
│
├── echo_server.py              <- Minimal repro attempt (didn't trigger bug)
├── proxy.toml
└── test_hang.sh
```

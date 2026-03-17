# KI-011: mcp-compose Proxy Hang After ~17 Sequential Tool Calls

**Master Document** - Links to detailed documentation.

## Quick Links

| Document | Purpose |
|----------|---------|
| [JIRA-BUG-REPORT.md](./JIRA-BUG-REPORT.md) | Copy-paste ready for Jira submission |
| [INVESTIGATION-GUIDE.md](./INVESTIGATION-GUIDE.md) | Debug config, cleanup, reproduction steps |
| [TECHNICAL-ANALYSIS.md](./TECHNICAL-ANALYSIS.md) | Root cause analysis with Mermaid diagrams |
| [EVIDENCE-INDEX.md](./EVIDENCE-INDEX.md) | Catalog of all log files and diagnostics |

## Summary

mcp-compose proxy stops forwarding responses after approximately 17 sequential tool calls. The SSE stream disconnects after 30 seconds of waiting for a response that never arrives. All subsequent requests fail with TaskGroup errors until restart.

## Status

| Field | Value |
|-------|-------|
| Jira | [DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409) |
| Related | DESK-1355 (partial fix, improved threshold from ~4 to ~17) |
| Severity | High |
| Component | mcp-compose / MCP SDK SSE handling |
| Root Cause | Response stops arriving after ~17 sessions; 30s SSE timeout fires |
| Workaround | None - restart required |

## Root Cause (Identified 2026-03-17)

After ~17 tool calls, the response stops being forwarded from environments_mcp_server to the client. The 30-second SSE read timeout fires, and mcp-compose logs:

```
GET stream disconnected, reconnecting in 1000ms...
```

Reconnection doesn't recover the pending request. All subsequent requests fail with:

```
unhandled errors in a TaskGroup (1 sub-exception)
```

**Key evidence**: Live capture during hang shows connections were ESTABLISHED, server was healthy (LISTEN). The timeout fires because the response never arrives, not because the operation is slow.

See [TECHNICAL-ANALYSIS.md](./TECHNICAL-ANALYSIS.md) for detailed diagrams and code investigation areas.

## Quick Reproduction

1. Configure Claude Desktop with anaconda-mcp
2. Create conda environment
3. Install packages one by one: pyyaml, requests, urllib3, certifi, charset-normalizer, idna, six, python-dateutil, pytz, packaging, attrs...
4. Observe hang around package 11-14 (~17th tool call)

See [INVESTIGATION-GUIDE.md](./INVESTIGATION-GUIDE.md) for detailed steps and debug configuration.

## Key Evidence

| File | What It Proves |
|------|----------------|
| `diagnostics_20260317_174021.txt` | Connections ESTABLISHED during hang, server healthy |
| `mcp_log_20260317_174021.log` | "GET stream disconnected" exactly 30s after stream opened |

See [EVIDENCE-INDEX.md](./EVIDENCE-INDEX.md) for complete catalog.

## Related Issues

| Issue | Summary | Relationship |
|-------|---------|--------------|
| DESK-1355 | Chat Session Freezes | Same issue; PR #28 improved threshold from ~4 to ~17 |
| KI-025 | Asyncio Thread Violation | Different bug - `create_environment` fails with PYTHONASYNCIODEBUG=1 |

## Environment

- mcp-compose: 0.1.11
- anaconda-mcp: 1.26.0
- Python: 3.13
- OS: macOS
- Transport: STDIO (upstream), Streamable HTTP (internal)

## Files in this Directory

```
proxy_hang/
├── KI-011-mcp-compose-proxy-hang.md   <- This file (master)
├── JIRA-BUG-REPORT.md                 <- For Jira
├── INVESTIGATION-GUIDE.md             <- Debug/repro guide
├── TECHNICAL-ANALYSIS.md              <- Root cause + diagrams
├── EVIDENCE-INDEX.md                  <- Evidence catalog
│
├── diagnostics_20260317_174021.txt    <- KEY: Live capture during hang
├── mcp_log_20260317_174021.log        <- KEY: SSE disconnect log
│
├── claude_desktop_hang_chat*.log      <- Chat logs
├── claude_desktop_hang_mcp_*.log      <- MCP server logs
│
├── echo_server.py                     <- Minimal repro attempt
├── proxy.toml                         <- Config for echo server
└── test_hang.sh                       <- Test script
```

## Next Steps

1. **File Jira bug** using [JIRA-BUG-REPORT.md](./JIRA-BUG-REPORT.md)
2. **Attach key evidence**:
   - `diagnostics_20260317_174021.txt`
   - `mcp_log_20260317_174021.log`
3. **Request investigation** of:
   - SSE stream timeout in mcp.client.streamable_http
   - TaskGroup error isolation in mcp_compose/tool_proxy.py
   - Why responses stop being forwarded after ~17 sessions
4. **Re-open DESK-1355** with new evidence (Claude Desktop IS affected)

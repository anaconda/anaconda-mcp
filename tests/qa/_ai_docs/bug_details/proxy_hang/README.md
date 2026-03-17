# Proxy Hang Bug Reproduction

This directory contains a minimal reproduction for the mcp-compose proxy hang bug.

## Bug Summary

mcp-compose proxy stops forwarding responses after ~17-18 rapid sequential tool calls when tools take time to execute (~0.8s+). The downstream server processes all requests successfully, but responses are not delivered to the client.

## Files

- `echo_server.py` - Minimal MCP server with a single `ping` tool (configurable delay)
- `proxy.toml` - mcp-compose config to proxy to echo_server
- `test_hang.sh` - Script to reproduce the hang
- `KI-011-mcp-compose-proxy-hang.md` - Full bug report

## Reproduction Steps

### Terminal 1: Start the proxy

```bash
cd /path/to/anaconda-mcp
python -m mcp_compose serve --config tests/qa/_ai_docs/bug_details/proxy_hang/proxy.toml
```

The echo_server starts with DELAY=0.8s by default (simulating a tool that takes time).

### Terminal 2: Run the test

```bash
cd /path/to/anaconda-mcp
./tests/qa/_ai_docs/bug_details/proxy_hang/test_hang.sh
```

## Expected vs Actual

**Expected:** All 25 iterations complete successfully.

**Actual:**
```
[1/25] echo_ping... OK
...
[17/25] echo_ping... OK
[18/25] echo_ping... TIMEOUT
[19/25] echo_ping... TIMEOUT
...
```

## Configuration

Environment variables for `echo_server.py`:
- `DELAY=0.8` - Delay in seconds before returning (default: 0.8)
- `DELAY=0` - No delay (instant return, bug does NOT reproduce)

Environment variables for `test_hang.sh`:
- `ITERATIONS=25` - Number of calls (default: 25)
- `TIMEOUT=10` - Timeout per call in seconds (default: 10)

## Notes

- mcp-compose version: 0.1.11
- PR #28 improved threshold from ~4 to ~17-18, but did not fully fix
- Bug only reproduces when tool execution takes time (DELAY > 0)
- Instant tools (DELAY=0) do not trigger the bug
- The downstream `echo_server.py` handles 50+ direct calls without issue
- Bug is in proxy layer response forwarding, likely related to connection/session timing

## Important

This minimal reproduction with echo_server does **NOT** reliably trigger the bug. The bug reproduces reliably with `environments_mcp_server`. This suggests the issue may be related to:
- Response size/complexity
- Multiple tool registrations
- Specific async patterns in the downstream server

For reliable reproduction, use the scripts in `tests/qa/_ai_docs/scripts/`:
- `test-env-mcp-direct.sh` - Tests environments_mcp_server directly (PASS)
- `test-mcp-compose-direct.sh` - Tests through mcp-compose proxy (FAIL at ~18)

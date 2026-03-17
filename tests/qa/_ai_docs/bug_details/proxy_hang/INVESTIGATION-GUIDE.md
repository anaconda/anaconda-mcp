# Investigation Guide: MCP Proxy Hang

**Jira**: [DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409)

How to debug, reproduce, and capture evidence for the mcp-compose proxy hang issue.

## Quick Reference

| What | Command/Location |
|------|------------------|
| MCP Log | `~/Library/Logs/Claude/mcp-server-anaconda-mcp.log` |
| Capture script | `tests/qa/_ai_docs/scripts/capture-hang-diagnostics.sh` |
| Internal port | 4041 (environments_mcp_server) |
| Hang threshold | ~17 tool calls |

## Debug Configuration

### Claude Desktop Config

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/opt/miniconda3/envs/YOUR_ENV/bin/python",
      "args": ["-m", "anaconda_mcp", "serve", "--delay", "15"],
      "env": {
        "ANACONDA_MCP_PYTHON_EXECUTABLE": "/opt/miniconda3/envs/YOUR_ENV/bin/python",
        "MCP_COMPOSE_CONFIG_DIR": "/opt/miniconda3/envs/YOUR_ENV/lib/python3.13/site-packages/anaconda_mcp",
        "PYTHONUNBUFFERED": "1",
        "LOG_LEVEL": "DEBUG",
        "MCP_COMPOSE_LOG_LEVEL": "DEBUG",
        "CONDA_MCP_SERVER_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

**Warning**: Do NOT use `PYTHONASYNCIODEBUG=1` - it causes a separate issue (KI-012) with environment creation.

## Process Cleanup

**Critical**: Always clean up before testing. Leftover processes can cause earlier hangs.

```bash
# Kill all MCP-related processes
pkill -f "mcp_compose"
pkill -f "environments_mcp_server"
pkill -f "anaconda_mcp serve"

# Verify port is clear
lsof -i :4041
# Should return empty

# Check for remaining processes
ps aux | grep anaconda-mcp
# Should show no "serve" processes (Cursor Helper plugins are OK)
```

### Full Cleanup Sequence

1. Quit Claude Desktop completely
2. Run cleanup commands above
3. Clear old logs: `rm ~/Library/Logs/Claude/mcp-server-anaconda-mcp.log`
4. Restart Claude Desktop
5. Test - threshold should be ~17 calls

## Reproducing the Hang

### Method 1: Manual (Claude Desktop)

1. Start Claude Desktop
2. Open new chat
3. "Create conda environment called test-hang-N" (increment N each time)
4. Install packages one at a time:
   ```
   install pyyaml to it
   install requests to it
   install urllib3 to it
   install certifi to it
   install charset-normalizer to it
   install idna to it
   install six to it
   install python-dateutil to it
   install pytz to it
   install packaging to it
   install attrs to it        <- Usually hangs here
   install jsonschema to it
   install toml to it
   install click to it
   install tqdm to it
   ```
5. Observe hang around package 11-14

### Method 2: Automated Tests

```bash
cd /path/to/anaconda-mcp

# HTTP transport
pytest tests/qa/http_tools/test_guard_happy_path_hang.py -v

# STDIO transport
pytest tests/qa/stdio_tools/test_guard_happy_path_hang_stdio.py -v
```

## Capturing Evidence During Hang

### While Claude Desktop is Hanging (DON'T close it yet!)

Run the capture script:
```bash
/path/to/anaconda-mcp/tests/qa/_ai_docs/scripts/capture-hang-diagnostics.sh
```

Or manually:
```bash
# Check connection states
lsof -i :4041
netstat -an | grep 4041

# Check processes
ps aux | grep -E "anaconda_mcp|mcp_compose|environments_mcp"

# Check MCP log for the disconnect message
tail -50 ~/Library/Logs/Claude/mcp-server-anaconda-mcp.log
```

### What to Look For

**In lsof output:**
```
# DURING hang (connections still active):
localhost:XXXXX->localhost:4041 (ESTABLISHED)
localhost:4041 (LISTEN)

# AFTER 30-second timeout (connections closed):
localhost:4041 (LISTEN)   <- Only listener remains
```

**In MCP log:**
```
# The smoking gun - SSE stream disconnect:
GET stream disconnected, reconnecting in 1000ms...

# Post-hang errors:
unhandled errors in a TaskGroup (1 sub-exception)
```

## Key Diagnostic Commands

### Check if downstream server is alive
```bash
lsof -i :4041
# Should show LISTEN if server is running
```

### Check connection states
```bash
netstat -an | grep 4041
# Look for ESTABLISHED, TIME_WAIT, CLOSED
```

### Watch connections in real-time
```bash
watch -n 1 'lsof -i :4041; echo "---"; netstat -an | grep 4041'
```

### Find process IDs
```bash
pgrep -f "anaconda_mcp serve"
pgrep -f "environments_mcp_server"
```

### Check open files for a process
```bash
lsof -p <PID> | head -50
```

## Log Analysis

### Finding the Hung Request

```bash
# Find tool calls in MCP log
grep "tools/call" ~/Library/Logs/Claude/mcp-server-anaconda-mcp.log

# Find the disconnect message
grep "stream disconnected" ~/Library/Logs/Claude/mcp-server-anaconda-mcp.log

# Find TaskGroup errors
grep "TaskGroup" ~/Library/Logs/Claude/mcp-server-anaconda-mcp.log
```

### Request Pattern to Look For

**Successful request:**
```
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"    <- Session init
POST http://localhost:4041/mcp "HTTP/1.1 202 Accepted"
GET http://localhost:4041/mcp "HTTP/1.1 200 OK"     <- SSE stream
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"    <- Tool result
DELETE http://localhost:4041/mcp "HTTP/1.1 200 OK"  <- Session cleanup
Message from server: {"jsonrpc":"2.0","id":N,"result":...}
```

**Hung request (missing final steps):**
```
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
POST http://localhost:4041/mcp "HTTP/1.1 202 Accepted"
GET http://localhost:4041/mcp "HTTP/1.1 200 OK"
POST http://localhost:4041/mcp "HTTP/1.1 200 OK"
... 30 SECONDS ...
GET stream disconnected, reconnecting in 1000ms...  <- TIMEOUT
# Missing: second POST 200, DELETE 200, Message from server
```

## Troubleshooting

### Hang occurs earlier than expected (~17)

**Cause**: Leftover processes from previous session

**Fix**: Full cleanup (see above)

### "Non-thread-safe operation" error on create_environment

**Cause**: `PYTHONASYNCIODEBUG=1` in config

**Fix**: Remove that environment variable (see KI-012)

### Can't reproduce the hang

- Ensure you're doing operations that hit the downstream server (not cached)
- Try `install_packages` (triggers conda operations) rather than `list_environments`
- Make sure previous test didn't leave corrupted state - do full cleanup

## Files Reference

| File | Purpose |
|------|---------|
| `capture-hang-diagnostics.sh` | Automated evidence capture |
| `test-mcp-compose-direct.sh` | Direct curl test (no Claude Desktop) |
| `test-env-mcp-direct.sh` | Test environments_mcp_server directly |

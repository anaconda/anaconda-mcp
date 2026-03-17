# MCP Debugging and Process Cleanup

## Process Cleanup

When testing MCP functionality, especially after hangs or errors, lingering processes can affect subsequent tests. Always clean up before testing.

### Quick Cleanup Commands

```bash
# Kill all MCP-related processes
pkill -f "mcp_compose"
pkill -f "environments_mcp_server"
pkill -f "anaconda_mcp serve"

# Verify cleanup
lsof -i :4041              # Should return empty
ps aux | grep anaconda-mcp # Should show no "serve" processes
```

### Full Cleanup Sequence

1. **Quit MCP clients** (Claude Desktop, Cursor, etc.)

2. **Kill server processes:**
   ```bash
   pkill -f "anaconda_mcp serve"
   pkill -f "mcp_compose"
   pkill -f "environments_mcp_server"
   ```

3. **Verify port is clear:**
   ```bash
   lsof -i :4041
   # Expected: empty output
   ```

4. **Check for remaining processes:**
   ```bash
   ps aux | grep anaconda-mcp
   ```

   **OK to keep** (IDE extension hosts):
   ```
   Cursor Helper (Plugin): extension-host ... anaconda-mcp
   ```

   **Must kill** (server processes):
   ```
   /opt/miniconda3/.../python anaconda-mcp serve --config ...
   ```

5. **Kill specific PIDs if needed:**
   ```bash
   kill <PID>
   ```

6. **Restart client and test**

## Why Cleanup Matters

After a hang (see KI-011), resources are not properly released:
- Connections/sessions persist across client restarts
- Each restart inherits leaked state
- Threshold for next hang is lowered
- Only killing processes fully resets state

## Debug Logging Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/opt/miniconda3/envs/<your-env>/bin/python",
      "args": ["-m", "anaconda_mcp", "serve", "--delay", "15"],
      "env": {
        "ANACONDA_MCP_PYTHON_EXECUTABLE": "/opt/miniconda3/envs/<your-env>/bin/python",
        "MCP_COMPOSE_CONFIG_DIR": "/opt/miniconda3/envs/<your-env>/lib/python3.13/site-packages/anaconda_mcp",

        "PYTHONUNBUFFERED": "1",
        "PYTHONFAULTHANDLER": "1",

        "LOG_LEVEL": "DEBUG",
        "MCP_COMPOSE_LOG_LEVEL": "DEBUG",
        "MCP_LOG_LEVEL": "DEBUG",
        "CONDA_MCP_SERVER_LOG_LEVEL": "DEBUG",

        "HTTPX_LOG_LEVEL": "DEBUG",
        "HTTPCORE_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Log Locations

| Log | Location |
|-----|----------|
| Claude Desktop MCP | `~/Library/Logs/Claude/mcp-server-anaconda-mcp.log` |
| mcp-compose temp configs | `/tmp/mcp_compose_*.toml` |

## Post-Hang Diagnostics

```bash
# Check if downstream server is alive
lsof -i :4041
# Expected: LISTEN state = server healthy

# Check connection states
netstat -an | grep 4041
# Look for CLOSED connections = resource leak

# Check for zombie processes
ps aux | grep -E "mcp|conda"
```

## Common Issues

### Hang occurs earlier than expected (~14-17 calls)

**Cause**: Leftover processes from previous hang

**Fix**: Full cleanup sequence (above)

### "unhandled errors in a TaskGroup" errors

**Cause**: Process state corrupted after hang

**Fix**: Kill all MCP processes and restart

### Port 4041 already in use

**Cause**: Previous server instance still running

**Fix**:
```bash
lsof -i :4041
kill <PID shown>
```

### "Non-thread-safe operation invoked on an event loop" error

**Cause**: `PYTHONASYNCIODEBUG=1` exposes latent thread-safety bug in environments_mcp_server

**Fix**: Remove `PYTHONASYNCIODEBUG=1` from environment configuration

**Note**: This flag is useful for debugging asyncio issues but causes `create_environment` to fail. See [KI-012](../bug_details/asyncio_thread/KI-012-asyncio-event-loop-thread-violation.md).

## Related Documentation

- [KI-011: mcp-compose Proxy Hang](../bug_details/proxy_hang/KI-011-mcp-compose-proxy-hang.md)
- [KI-012: Asyncio Event Loop Thread Violation](../bug_details/asyncio_thread/KI-012-asyncio-event-loop-thread-violation.md)

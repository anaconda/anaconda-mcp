# Configuration Testing Guide

## Purpose

This guide explains **what to test** and **why** for each configuration option. Use CONFIGURATION.md as reference for option details.

---

## Testing Priority

| Priority | Config Area | Why Test |
|----------|-------------|----------|
| P0 | Transport (STDIO/HTTP) | Core functionality |
| P0 | Claude Desktop paths | OS-specific, user-facing |
| P1 | Environment variables | User customization |
| P1 | Config file overrides | Advanced usage |
| P2 | Telemetry settings | Privacy compliance |

---

## P0: Transport Configuration

### STDIO Transport (Default)

**What**: Claude Desktop spawns anaconda-mcp as subprocess

**Why Test**: This is the default experience for most users

**Test Scenario**:
1. Run `anaconda-mcp claude-desktop setup-config` (no transport flag)
2. Restart Claude Desktop
3. Ask Claude to list environments

**Pass Criteria**:
- Config uses `"command"` and `"args"` (not `"url"`)
- Claude Desktop can communicate with server
- Tools respond correctly

**Fail Indicators**:
- "Server not responding" in Claude Desktop
- Config has wrong Python path

---

### HTTP Transport

**What**: User starts server manually, Claude connects via URL

**Why Test**: Alternative for shared servers, debugging

**Test Scenario**:
1. Start server: `anaconda-mcp serve --port 8888`
2. Configure: `anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888`
3. Restart Claude Desktop
4. Ask Claude to list environments

**Pass Criteria**:
- Server shows "Listening on port 8888"
- Config uses `"url": "http://localhost:8888/mcp"`
- Tools respond correctly

**Fail Indicators**:
- "Connection refused" errors
- Port already in use
- Config still has STDIO format

---

## P0: Claude Desktop Config Paths

**What**: OS-specific config file locations

**Why Test**: Wrong path = Claude Desktop won't find config

| OS | Expected Path |
|----|---------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

**Test Scenario**:
1. Run `anaconda-mcp claude-desktop path`
2. Verify path matches OS
3. Run `anaconda-mcp claude-desktop setup-config`
4. Verify file created at correct location

**Pass Criteria**:
- Path command returns OS-appropriate path
- Config file actually created there
- Claude Desktop reads the config

**Fail Indicators**:
- Path doesn't exist
- Wrong OS path returned
- Permission denied errors

---

## P1: Environment Variables

### ANACONDA_MCP_LOG_LEVEL

**What**: Controls log verbosity (DEBUG, INFO, WARNING, ERROR)

**Why Test**: Users need DEBUG for troubleshooting

**Test Scenario**:
```bash
# Test DEBUG level
ANACONDA_MCP_LOG_LEVEL=DEBUG anaconda-mcp serve --port 8888

# Test default (INFO)
anaconda-mcp serve --port 8889
```

**Pass Criteria**:
- DEBUG shows detailed MCP protocol messages
- INFO shows only startup/connection messages
- Invalid values handled gracefully

---

### ANACONDA_MCP_SEND_METRICS

**What**: Enable/disable telemetry

**Why Test**: Privacy compliance, enterprise requirement

**Test Scenario**:
```bash
# Disable telemetry
ANACONDA_MCP_SEND_METRICS=false anaconda-mcp serve

# Enable telemetry (default)
anaconda-mcp serve
```

**Pass Criteria**:
- `false` = no network calls to telemetry endpoint
- `true` = metrics sent (verify in DEBUG logs)
- Server works regardless of setting

**How to Verify**:
- Use `ANACONDA_MCP_LOG_LEVEL=DEBUG` to see telemetry calls
- Or use network monitor to check outbound connections

---

### ANACONDA_MCP_PYTHON_EXECUTABLE

**What**: Override Python interpreter path in generated configs

**Why Test**: Users with multiple Python installations

**Test Scenario**:
```bash
# Set custom Python path
export ANACONDA_MCP_PYTHON_EXECUTABLE=/opt/conda/bin/python
anaconda-mcp claude-desktop setup-config

# Check generated config
anaconda-mcp claude-desktop show --json
```

**Pass Criteria**:
- Generated config uses specified Python path
- Path appears in `"command"` field for STDIO
- Invalid path should warn (not crash)

---

## P1: Config File Overrides

### Custom Config File

**What**: Use custom TOML config instead of default

**Why Test**: Enterprise customization, testing

**Test Scenario**:
```bash
# Create custom config
cat > /tmp/custom.toml << 'EOF'
[composer]
name = "test-server"
port = 9999
log_level = "DEBUG"

[transport]
stdio_enabled = false
streamable_http_enabled = true
EOF

# Start with custom config
anaconda-mcp serve --config /tmp/custom.toml
```

**Pass Criteria**:
- Server uses port 9999 (not default 2391)
- Server name shows as "test-server"
- HTTP enabled, STDIO disabled

**Fail Indicators**:
- Config file not found error
- Invalid TOML syntax error
- Values not applied

---

### Port Override

**What**: `--port` CLI flag overrides config file

**Why Test**: CLI should take precedence

**Test Scenario**:
```bash
# Config says port 2391, CLI says 7777
anaconda-mcp serve --port 7777
```

**Pass Criteria**:
- Server listens on 7777
- Logs show correct port

---

## P2: Telemetry Configuration

### ANACONDA_MCP_ENVIRONMENT

**What**: Sets environment tag for telemetry (production, staging, development)

**Why Test**: Ensures metrics go to correct destination

**Test Scenario**:
```bash
ANACONDA_MCP_ENVIRONMENT=staging anaconda-mcp serve
```

**Pass Criteria**:
- Telemetry tagged with "staging"
- No functional difference in server behavior

---

## Quick Test Checklist

### Smoke Test (5 min)
- [ ] `anaconda-mcp claude-desktop path` returns valid OS path
- [ ] `anaconda-mcp claude-desktop setup-config` creates config
- [ ] `anaconda-mcp serve --port 8888` starts without error
- [ ] `ANACONDA_MCP_LOG_LEVEL=DEBUG` shows verbose output

### Full Config Test (20 min)
- [ ] STDIO transport works end-to-end
- [ ] HTTP transport works end-to-end
- [ ] Custom port override works
- [ ] Custom config file works
- [ ] Telemetry can be disabled
- [ ] Invalid config values handled gracefully

---

## Common Issues

| Symptom | Likely Cause | Config to Check |
|---------|--------------|-----------------|
| "Server not found" in Claude | Wrong Python path | `ANACONDA_MCP_PYTHON_EXECUTABLE` |
| Port conflict on start | Another process using port | `--port` flag |
| No logs appearing | Log level too high | `ANACONDA_MCP_LOG_LEVEL` |
| Config not updating | Backup file being read | Remove `.backup` files |
| HTTP not working | Transport disabled | `streamable_http_enabled` in TOML |

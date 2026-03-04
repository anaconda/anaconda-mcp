# Configuration Testing Guide

## Purpose

Component-level testing of configuration options via CLI. These tests do **not** require Claude Desktop - they validate configuration behavior directly.

For end-to-end testing with Claude Desktop, see [E2E_USER_FLOWS.md](./E2E_USER_FLOWS.md).

---

## Scope

| This Guide Covers | E2E Flows Cover |
|-------------------|-----------------|
| Env var behavior via CLI | Full Claude Desktop integration |
| Config file parsing | User asks Claude, Claude responds |
| CLI flag precedence | Transport works end-to-end |
| OS-specific paths (verification) | Tool execution via AI |

---

## Test Scenarios

### ENV-001: Log Level

**What**: `ANACONDA_MCP_LOG_LEVEL` controls verbosity

**Test**:
```bash
# DEBUG - verbose output
ANACONDA_MCP_LOG_LEVEL=DEBUG anaconda-mcp serve --port 8888 &
sleep 3 && kill %1

# WARNING - minimal output
ANACONDA_MCP_LOG_LEVEL=WARNING anaconda-mcp serve --port 8889 &
sleep 3 && kill %1
```

**Pass**: DEBUG shows MCP protocol details, WARNING shows minimal logs

---

### ENV-002: Telemetry Control

**What**: `ANACONDA_MCP_SEND_METRICS` enables/disables telemetry

**Test**:
```bash
# Disabled
ANACONDA_MCP_LOG_LEVEL=DEBUG ANACONDA_MCP_SEND_METRICS=false anaconda-mcp serve &
sleep 3 && kill %1
# Check logs for telemetry calls

# Enabled (default)
ANACONDA_MCP_LOG_LEVEL=DEBUG anaconda-mcp serve &
sleep 3 && kill %1
```

**Pass**: `false` shows no telemetry initialization, `true` shows telemetry calls in DEBUG logs

---

### ENV-003: Python Executable Override

**What**: `ANACONDA_MCP_PYTHON_EXECUTABLE` overrides Python path in generated configs

**Test**:
```bash
# Set custom path
export ANACONDA_MCP_PYTHON_EXECUTABLE=/usr/bin/python3
anaconda-mcp claude-desktop setup-config
anaconda-mcp claude-desktop show --json | grep "command"
```

**Pass**: Generated config shows `/usr/bin/python3` in command field

---

### ENV-004: Environment Mode

**What**: `ANACONDA_MCP_ENVIRONMENT` sets API environment (production/staging)

**Test**:
```bash
ANACONDA_MCP_LOG_LEVEL=DEBUG ANACONDA_MCP_ENVIRONMENT=staging anaconda-mcp serve &
sleep 3 && kill %1
```

**Pass**: Logs show staging domain for Anaconda API calls

---

### CFG-001: Custom Config File

**What**: `--config` flag loads custom TOML configuration

**Test**:
```bash
# Create custom config
cat > /tmp/test-config.toml << 'EOF'
[composer]
name = "custom-test"
port = 9999
log_level = "DEBUG"

[transport]
stdio_enabled = false
streamable_http_enabled = true
EOF

# Start with custom config
anaconda-mcp serve --config /tmp/test-config.toml &
sleep 3

# Verify port
curl -s http://localhost:9999/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

kill %1
```

**Pass**: Server starts on port 9999, responds to API calls

---

### CFG-002: CLI Flag Precedence

**What**: CLI flags override config file values

**Test**:
```bash
# Config says 9999, CLI says 7777
anaconda-mcp serve --config /tmp/test-config.toml --port 7777 &
sleep 3

# Should be on 7777, not 9999
curl -s http://localhost:7777/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

kill %1
```

**Pass**: Server listens on CLI-specified port (7777), not config port (9999)

---

### CFG-003: Startup Delay

**What**: `--delay` adds startup delay before server initialization

**Test**:
```bash
time (anaconda-mcp serve --delay 5 &
  sleep 1
  kill %1 2>/dev/null)
```

**Pass**: Server waits ~5 seconds before initialization logs appear

---

### PATH-001: OS-Specific Config Paths

**What**: Claude Desktop config path varies by OS

**Test**:
```bash
anaconda-mcp claude-desktop path
```

**Expected by OS**:
| OS | Expected Path |
|----|---------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

**Pass**: Returned path matches OS

---

### PATH-002: Config File Creation

**What**: `setup-config` creates file at correct location

**Test**:
```bash
# Get expected path
CONFIG_PATH=$(anaconda-mcp claude-desktop path)

# Remove if exists
rm -f "$CONFIG_PATH"

# Create config
anaconda-mcp claude-desktop setup-config

# Verify created
ls -la "$CONFIG_PATH"
```

**Pass**: File exists at expected path

---

## Quick Checklist

### Smoke Test (5 min)
- [ ] `anaconda-mcp claude-desktop path` returns valid OS path
- [ ] `anaconda-mcp serve --port 8888` starts without error
- [ ] `ANACONDA_MCP_LOG_LEVEL=DEBUG` shows verbose output
- [ ] `anaconda-mcp --help` works with extra env vars set

### Full Config Test (15 min)
- [ ] ENV-001: Log level changes output
- [ ] ENV-002: Telemetry can be disabled
- [ ] ENV-003: Python executable override works
- [ ] CFG-001: Custom config file loads
- [ ] CFG-002: CLI flags override config
- [ ] CFG-003: Startup delay works
- [ ] PATH-001: Correct OS path returned
- [ ] PATH-002: Config created at correct location

---

## Troubleshooting

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| Server won't start | Port in use | `lsof -i :PORT` |
| No debug logs | Wrong env var | Verify `ANACONDA_MCP_LOG_LEVEL=DEBUG` |
| Config not updating | Backup interference | Remove `.backup` files |
| Wrong Python in config | Env var not set | Check `ANACONDA_MCP_PYTHON_EXECUTABLE` |

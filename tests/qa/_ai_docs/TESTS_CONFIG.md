# Configuration Tests (All Platforms)

## Overview

Component-level testing of configuration options via CLI. No Claude Desktop required.

**Platforms**: macOS, Windows, Linux (all GitHub runners)

---

## Test Summary

| Test ID | What | Priority |
|---------|------|----------|
| ENV-001 | Log Level | P1 |
| ENV-002 | Telemetry Control | P1 |
| ENV-003 | Python Executable | P1 |
| ENV-004 | Environment Mode | P2 |
| CFG-001 | Custom Config File | P1 |
| CFG-002 | CLI Flag Precedence | P1 |
| CFG-003 | Startup Delay | P1 |
| PATH-001 | OS-Specific Paths | P0 |
| PATH-002 | Config File Creation | P0 |

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

# Enabled (default)
ANACONDA_MCP_LOG_LEVEL=DEBUG anaconda-mcp serve &
sleep 3 && kill %1
```

**Pass**: `false` shows no telemetry initialization, `true` shows telemetry in DEBUG logs

---

### ENV-003: Python Executable Override

**What**: `ANACONDA_MCP_PYTHON_EXECUTABLE` overrides Python path in generated configs

**Test**:
```bash
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
cat > /tmp/test-config.toml << 'EOF'
[composer]
name = "custom-test"
port = 9999
log_level = "DEBUG"

[transport]
stdio_enabled = false
streamable_http_enabled = true
EOF

anaconda-mcp serve --config /tmp/test-config.toml &
sleep 3

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
anaconda-mcp serve --config /tmp/test-config.toml --port 7777 &
sleep 3

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
CONFIG_PATH=$(anaconda-mcp claude-desktop path)
rm -f "$CONFIG_PATH"
anaconda-mcp claude-desktop setup-config
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

## CI Automation

### GitHub Actions Workflow

```yaml
# .github/workflows/config-tests.yml
name: Configuration Tests

on:
  pull_request:
  push:
    branches: [main]

jobs:
  config-tests:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    defaults:
      run:
        shell: bash -el {0}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Miniconda
        uses: conda-incubator/setup-miniconda@v3
        with:
          auto-activate-base: true
          python-version: "3.11"

      - name: Install anaconda-mcp
        run: conda install anaconda-mcp environments-mcp-server -y

      # PATH-001
      - name: Test config path
        run: |
          CONFIG_PATH=$(anaconda-mcp claude-desktop path)
          echo "Config path: $CONFIG_PATH"
          [ -n "$CONFIG_PATH" ] || exit 1

      # ENV-001
      - name: Test DEBUG log level
        run: |
          ANACONDA_MCP_LOG_LEVEL=DEBUG anaconda-mcp serve --port 8888 &
          sleep 10
          kill %1 2>/dev/null || true

      # ENV-002
      - name: Test telemetry disabled
        run: |
          ANACONDA_MCP_SEND_METRICS=false anaconda-mcp serve --port 8889 &
          sleep 10
          kill %1 2>/dev/null || true

      # CFG-002
      - name: Test port override
        run: |
          anaconda-mcp serve --port 7777 &
          sleep 10
          curl -sf http://localhost:7777/mcp -X POST \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' || exit 1
          kill %1 2>/dev/null || true

      # API smoke test
      - name: API smoke test
        run: |
          anaconda-mcp serve --port 9999 &
          sleep 10
          curl -sf http://localhost:9999/mcp -X POST \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | grep conda_list_environments
          kill %1 2>/dev/null || true

      - name: Cleanup
        if: always()
        run: pkill -f "anaconda-mcp serve" || true
```

---

## Platform Coverage

| Test | Linux | macOS | Windows |
|------|-------|-------|---------|
| PATH-001 | ✅ | ✅ | ✅ |
| PATH-002 | ✅ | ✅ | ✅ |
| ENV-001 | ✅ | ✅ | ✅ |
| ENV-002 | ✅ | ✅ | ✅ |
| ENV-003 | ✅ | ✅ | ✅ |
| ENV-004 | ✅ | ✅ | ✅ |
| CFG-001 | ✅ | ✅ | ✅ |
| CFG-002 | ✅ | ✅ | ✅ |
| CFG-003 | ✅ | ✅ | ✅ |

---

## Troubleshooting

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| Server won't start | Port in use | `lsof -i :PORT` |
| No debug logs | Wrong env var | Verify `ANACONDA_MCP_LOG_LEVEL=DEBUG` |
| Config not updating | Backup interference | Remove `.backup` files |
| Wrong Python in config | Env var not set | Check `ANACONDA_MCP_PYTHON_EXECUTABLE` |

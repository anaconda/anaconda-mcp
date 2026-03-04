# CLI Flows (All Platforms)

## Overview

CLI-only flows that can run on any platform without Claude Desktop.

**Platforms**: macOS, Windows (Win365, GitHub runners), Linux (GitHub runners)

---

## Flow Summary

| Flow ID | Name | Priority | CI Automatable |
|---------|------|----------|----------------|
| CLI-001 | Server Discovery | P1 | Yes |
| CLI-002 | Advanced Options | P1 | Yes |
| CLI-003 | Config Management | P0 | Yes |
| CLI-004 | Regression CLI | P0 | Yes |
| CLI-005 | Negative Scenarios | P1 | Yes |

---

## CLI-001: Server Discovery

**Purpose**: Test CLI commands for server discovery and composition.

**Steps**:

```bash
# Phase 1: Discover
anaconda-mcp discover
# [EXPECTED] Lists discovered MCP servers

anaconda-mcp discover --output-format json
# [EXPECTED] Valid JSON output

# Phase 2: Compose
anaconda-mcp compose
# [EXPECTED] Shows composed server information

anaconda-mcp compose --conflict-resolution prefix
# [EXPECTED] Tools prefixed with server name

anaconda-mcp compose --output-format json
# [EXPECTED] Valid JSON output

# Phase 3: Verbose Logging
anaconda-mcp -v serve --port 8888 &
sleep 5
kill %1
# [EXPECTED] DEBUG level logs displayed
```

---

## CLI-002: Advanced Options

**Purpose**: Test advanced CLI options and flags.

**Steps**:

```bash
# Phase 1: Custom Config
cat > /tmp/custom-mcp.toml << 'EOF'
[composer]
name = "test-server"
port = 9876
[transport]
stdio_enabled = false
streamable_http_enabled = true
EOF

anaconda-mcp serve --config /tmp/custom-mcp.toml &
sleep 5
curl -sf http://localhost:9876/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
kill %1
# [EXPECTED] Server on port 9876, tools listed

# Phase 2: Startup Delay
time (anaconda-mcp serve --delay 3 --port 8887 &
  sleep 5
  kill %1 2>/dev/null)
# [EXPECTED] ~3 second delay visible

# Phase 3: Skip Backup
anaconda-mcp claude-desktop setup-config --no-backup --force
# [EXPECTED] No backup file created

# Phase 4: Show Server Config
anaconda-mcp claude-desktop show --name anaconda-mcp
# [EXPECTED] Shows only anaconda-mcp config
```

---

## CLI-003: Config Management

**Purpose**: Test Claude Desktop config management via CLI.

**Steps**:

```bash
# Phase 1: Show Config
anaconda-mcp claude-desktop show
# [EXPECTED] Displays mcpServers configuration

anaconda-mcp claude-desktop show --json
# [EXPECTED] Valid JSON output

# Phase 2: Setup and Verify
anaconda-mcp claude-desktop setup-config
anaconda-mcp claude-desktop show | grep anaconda-mcp
# [EXPECTED] anaconda-mcp entry present

# Phase 3: Force Overwrite
anaconda-mcp claude-desktop setup-config --transport streamable-http --port 9999 --force
anaconda-mcp claude-desktop show --json | grep "9999"
# [EXPECTED] Port 9999 in config

# Phase 4: Remove Config
anaconda-mcp claude-desktop remove-config
anaconda-mcp claude-desktop show
# [EXPECTED] anaconda-mcp removed

# Phase 5: Restore
anaconda-mcp claude-desktop setup-config
# [EXPECTED] STDIO config restored
```

---

## CLI-004: Regression CLI Tests

**Purpose**: CLI-only regression tests for known issues.

**Steps**:

```bash
# KI-004: Extra Environment Variables
export OPENAI_API_KEY=test123
export RANDOM_VAR=value
anaconda-mcp --help
# [EXPECTED] No pydantic ValidationError

anaconda-mcp serve --port 8886 &
sleep 5
kill %1
# [EXPECTED] Server starts without crash

unset OPENAI_API_KEY RANDOM_VAR
```

---

## CLI-005: Negative Scenarios (API)

**Purpose**: Validate error handling via direct API calls.

**Setup**:
```bash
anaconda-mcp serve --port 2391 &
sleep 10
```

**Tests**:

```bash
# Duplicate environment
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"conda_create_environment","arguments":{"name":"base"}}}'
# [EXPECTED] Error: environment already exists

# Non-existent environment
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"conda_delete_environment","arguments":{"name":"nonexistent-xyz"}}}'
# [EXPECTED] Error: environment not found

# Invalid tool
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"invalid_tool"}}'
# [EXPECTED] Error code: -32601

# Malformed JSON
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d 'not valid json'
# [EXPECTED] Error code: -32700
```

**Cleanup**:
```bash
kill %1
```

---

## CI Automation (Phase 2)

Workflow template: [ci_workflows/cli-tests.yml](./ci_workflows/cli-tests.yml)

Copy to `.github/workflows/` when ready to implement.

---

## Platform Coverage

| Flow | Linux | macOS | Windows |
|------|-------|-------|---------|
| CLI-001 | ✅ | ✅ | ✅ |
| CLI-002 | ✅ | ✅ | ✅ |
| CLI-003 | ✅ | ✅ | ✅ |
| CLI-004 | ✅ | ✅ | ✅ |
| CLI-005 | ✅ | ✅ | ✅ |

---

## Test Execution Order

### Every PR (CI)
1. **CLI-004** - Regression (KI-004)
2. **CLI-001** - Server discovery
3. **CLI-002** - Advanced options
4. **CLI-003** - Config management

### Release Testing
5. **CLI-005** - Negative scenarios

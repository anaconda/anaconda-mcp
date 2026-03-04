# Anaconda MCP - E2E User Flows (Optimized)

## Overview

10 E2E flows (happy paths) + manual dev mode testing (negative scenarios). Each flow is designed for both manual testing and AI-assisted execution.

**Related Documents**:
- [E2E_COVERAGE_MAP.md](./E2E_COVERAGE_MAP.md) - Coverage mapping and gap analysis
- [FEATURE_TREE.md](./FEATURE_TREE.md) - Complete feature hierarchy
- [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) - Known bugs and quirks

---

## Flow Summary

| Flow ID | Name | Priority | Features Covered |
|---------|------|----------|------------------|
| CORE-001 | Full Setup & Tools | P0 | 8 |
| CORE-002 | HTTP Transport | P0 | 4 |
| CORE-003 | Config Management | P0 | 5 |
| CLI-001 | Server Discovery | P1 | 3 |
| CLI-002 | Advanced Options | P1 | 4 |
| AUTH-001 | Full Auth Cycle | P1 | 3 |
| AUTH-002 | Anonymous Mode | P1 | 1 |
| CONFIG-001 | Environment Variables | P1 | 4 |
| GUARD-001 | Guardrails | P0 | 3 |
| REGRESS-001 | Known Issues | P0 | 4 |

**Note**: Error/exception testing moved to Manual Dev Mode Testing (see below).

---

## P0 Flows (Critical Path)

### CORE-001: Full Setup & Tools

**Purpose**: End-to-end happy path covering installation, setup, and all 5 environment tools.

**Features Covered**:
- [x] Package Installation
- [x] Claude Desktop STDIO Setup
- [x] Get Config Path
- [x] List Environments
- [x] Create Environment
- [x] Install Packages
- [x] Remove Packages
- [x] Delete Environment

**Preconditions**:
- [PRE] Python 3.10+ installed
- [PRE] Claude Desktop installed
- [PRE] No existing anaconda-mcp config

**Steps**:

```
Phase 1: Installation
```
1. Install package: `pip install anaconda-mcp` (or conda install)
2. Verify installation: `anaconda-mcp --help`
3. [EXPECTED] Help shows commands: serve, compose, discover, claude-desktop

```
Phase 2: Claude Desktop Setup
```
4. Get config path: `anaconda-mcp claude-desktop path`
5. [EXPECTED] Shows OS-specific path (e.g., ~/Library/Application Support/Claude/...)
6. Setup config: `anaconda-mcp claude-desktop setup-config`
7. [EXPECTED] Config created successfully, backup created if existed
8. Restart Claude Desktop

```
Phase 3: Environment Tools
```
9. In Claude Desktop, ask: "List my conda environments"
10. [EXPECTED] Claude uses `conda_list_environments`, shows environment list

11. Ask: "Create a new conda environment called e2e-test-env with Python 3.11"
12. [EXPECTED] Claude uses `conda_create_environment`, environment created

13. Ask: "Install numpy and requests in e2e-test-env"
14. [EXPECTED] Claude uses `conda_install_packages`, packages installed

15. Ask: "Remove requests from e2e-test-env"
16. [EXPECTED] Claude uses `conda_remove_packages`, package removed

17. Ask: "Delete the e2e-test-env environment"
18. Confirm deletion when prompted
19. [EXPECTED] Claude uses `conda_delete_environment`, environment deleted

```
Phase 4: Verification
```
20. Ask: "List my conda environments"
21. [EXPECTED] e2e-test-env no longer appears

**Cleanup**: None needed (environment deleted in test)

---

### CORE-002: HTTP Transport

**Purpose**: Test HTTP transport mode with server lifecycle.

**Features Covered**:
- [x] Start Server (with port option)
- [x] HTTP Transport Setup
- [x] HTTP Transport Connection
- [x] Server Not Running Error

**Preconditions**:
- [PRE] anaconda-mcp installed
- [PRE] Port 8888 available
- [PRE] Claude Desktop installed

**Steps**:

```
Phase 1: Server Start
```
1. Terminal 1: `anaconda-mcp serve --port 8888`
2. [EXPECTED] Server starts, logs "Listening on http://127.0.0.1:8888"
3. [EXPECTED] Downstream server auto-starts on port 4041

```
Phase 2: HTTP Setup
```
4. Terminal 2: `anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888`
5. [EXPECTED] Config shows URL: http://localhost:8888/mcp
6. Restart Claude Desktop

```
Phase 3: Verify Connection
```
7. In Claude Desktop, ask: "List my conda environments"
8. [EXPECTED] Response received via HTTP transport

```
Phase 4: Server Down Error
```
9. Terminal 1: Stop server (Ctrl+C)
10. In Claude Desktop, ask: "List my conda environments"
11. [EXPECTED] Error indicates server unreachable

**Cleanup**:
- `anaconda-mcp claude-desktop remove-config`
- Re-setup STDIO if needed: `anaconda-mcp claude-desktop setup-config`

---

### CORE-003: Config Management

**Purpose**: Test all Claude Desktop configuration management features.

**Features Covered**:
- [x] Show Config
- [x] Force Overwrite
- [x] JSON Output
- [x] Remove Config
- [x] Backup Creation

**Preconditions**:
- [PRE] anaconda-mcp installed
- [PRE] Existing config in Claude Desktop

**Steps**:

```
Phase 1: Show Config
```
1. `anaconda-mcp claude-desktop show`
2. [EXPECTED] Displays full mcpServers configuration
3. `anaconda-mcp claude-desktop show --json`
4. [EXPECTED] Output is valid JSON format

```
Phase 2: Force Overwrite
```
5. `anaconda-mcp claude-desktop setup-config --transport streamable-http --port 9999 --force`
6. [EXPECTED] Backup file created with timestamp
7. [EXPECTED] Config updated to HTTP transport on port 9999
8. `anaconda-mcp claude-desktop show`
9. [EXPECTED] Shows new HTTP configuration

```
Phase 3: Remove Config
```
10. `anaconda-mcp claude-desktop remove-config`
11. [EXPECTED] anaconda-mcp entry removed
12. `anaconda-mcp claude-desktop show`
13. [EXPECTED] anaconda-mcp no longer in config (or empty mcpServers)

```
Phase 4: Restore
```
14. `anaconda-mcp claude-desktop setup-config`
15. [EXPECTED] STDIO config restored

**Cleanup**: Ensure STDIO config is restored

---

### GUARD-001: Guardrails

**Purpose**: Verify non-negotiable guardrails are enforced.

**Features Covered**:
- [x] Channel Ordering Respected
- [x] Hard Fail on Missing Package
- [x] Delete Confirmation Required

**Preconditions**:
- [PRE] anaconda-mcp configured in Claude Desktop
- [PRE] Custom `.condarc` with channel order (for channel test)

**Steps**:

```
Phase 1: Channel Ordering
```
1. Configure `.condarc`:
   ```yaml
   channels:
     - defaults
     - conda-forge
   ```
2. Create test env: `conda create -n guard-channel-test python=3.11 -y`
3. Ask Claude: "Install a package that exists in both defaults and conda-forge in guard-channel-test"
4. [EXPECTED] Package installed from `defaults` (first channel)
5. Verify source: `conda list -n guard-channel-test <package>`

```
Phase 2: Hard Fail on Missing Package
```
6. Ask Claude: "Install nonexistent-package-xyz123 in guard-channel-test"
7. [EXPECTED] Operation fails with clear error
8. [EXPECTED] Error explains package not on configured channels
9. [EXPECTED] No pip fallback attempted

```
Phase 3: Delete Confirmation
```
10. Ask Claude: "Delete the guard-channel-test environment"
11. [EXPECTED] Claude asks for explicit confirmation before proceeding
12. Confirm deletion
13. [EXPECTED] Environment deleted only after confirmation
14. Verify: `conda env list | grep guard-channel-test` returns empty

**Cleanup**: Environment deleted in test

---

### REGRESS-001: Known Issues

**Purpose**: Regression tests for previously fixed issues.

**Features Covered**:
- [x] Environment Name Correctly Reported (KI-002)
- [x] Environment Deletion Actually Works (KI-001)
- [x] Extra Environment Variables Don't Crash (KI-004)
- [x] Install Package by Environment Name (KI-003)

**Preconditions**:
- [PRE] anaconda-mcp configured

**Steps**:

```
Phase 1: Extra Env Vars (KI-004)
```
1. Set extra env vars: `export OPENAI_API_KEY=test123 RANDOM_VAR=value`
2. Run: `anaconda-mcp --help`
3. [EXPECTED] No pydantic ValidationError, help displays normally
4. Run: `anaconda-mcp serve` (then Ctrl+C after startup)
5. [EXPECTED] Server starts without crash

```
Phase 2: Environment Name (KI-002)
```
6. Create env: `conda create -n regress-name-test python=3.11 -y`
7. Ask Claude: "List my conda environments"
8. [EXPECTED] Environment appears as "regress-name-test" (not "base")

```
Phase 3: Install by Name (KI-003)
```
9. Ask Claude: "Install numpy in the regress-name-test environment"
10. [EXPECTED] Environment found by name (not path)
11. [EXPECTED] Package installs successfully

```
Phase 4: Deletion Actually Works (KI-001)
```
12. Verify env exists: `conda env list | grep regress-name-test`
13. [EXPECTED] Environment listed
14. Ask Claude: "Delete the regress-name-test environment"
15. Confirm deletion
16. Verify deleted: `conda env list | grep regress-name-test`
17. [EXPECTED] Environment NOT listed (actually deleted)

**Cleanup**: Environment deleted in test

---

## P1 Flows (Extended Coverage)

### CLI-001: Server Discovery

**Purpose**: Test CLI commands for server discovery and composition.

**Features Covered**:
- [x] Discover Servers
- [x] Compose Servers
- [x] Verbose Logging

**Preconditions**:
- [PRE] anaconda-mcp installed
- [PRE] In a directory with pyproject.toml (or use repo root)

**Steps**:

```
Phase 1: Discover
```
1. `anaconda-mcp discover`
2. [EXPECTED] Lists discovered MCP servers
3. `anaconda-mcp discover --output-format json`
4. [EXPECTED] Valid JSON output

```
Phase 2: Compose
```
5. `anaconda-mcp compose`
6. [EXPECTED] Shows composed server information
7. `anaconda-mcp compose --conflict-resolution prefix`
8. [EXPECTED] Tools prefixed with server name
9. `anaconda-mcp compose --output-format json`
10. [EXPECTED] Valid JSON output

```
Phase 3: Verbose Logging
```
11. `anaconda-mcp -v serve` (then Ctrl+C after startup)
12. [EXPECTED] DEBUG level logs displayed
13. [EXPECTED] More detailed startup information

**Cleanup**: None

---

### CLI-002: Advanced Options

**Purpose**: Test advanced CLI options and flags.

**Features Covered**:
- [x] Custom Config (--config)
- [x] Startup Delay (--delay)
- [x] Skip Backup (--no-backup)
- [x] Show Server Config (--name)

**Preconditions**:
- [PRE] anaconda-mcp installed
- [PRE] Custom config file created

**Steps**:

```
Phase 1: Custom Config
```
1. Create custom config `/tmp/custom-mcp.toml` with different port (e.g., 9876)
2. `anaconda-mcp serve --config /tmp/custom-mcp.toml`
3. [EXPECTED] Server starts on custom port 9876
4. Ctrl+C to stop

```
Phase 2: Startup Delay
```
5. `time anaconda-mcp serve --delay 3` (then Ctrl+C)
6. [EXPECTED] ~3 second delay before server starts
7. [EXPECTED] Logs show delay was applied

```
Phase 3: Skip Backup
```
8. `anaconda-mcp claude-desktop setup-config --no-backup --force`
9. [EXPECTED] Config updated without creating backup file
10. Verify no new backup created in Claude config directory

```
Phase 4: Show Server Config
```
11. `anaconda-mcp claude-desktop show --name anaconda-mcp`
12. [EXPECTED] Shows only anaconda-mcp server config (not full file)

**Cleanup**: Restore default config: `anaconda-mcp claude-desktop setup-config --force`

---

### AUTH-001: Full Auth Cycle

**Purpose**: Test complete authentication flow.

**Features Covered**:
- [x] Manual Login
- [x] Token Management
- [x] Auto Login Behavior

**Preconditions**:
- [PRE] Anaconda account exists
- [PRE] Not currently logged in

**Steps**:

```
Phase 1: Manual Login
```
1. Ensure logged out (clear keyring if needed)
2. Run: `anaconda login`
3. Complete browser authentication
4. [EXPECTED] Login success message
5. [EXPECTED] Token stored in system keyring

```
Phase 2: Token Persistence
```
6. Start new terminal session
7. `anaconda-mcp serve` (then Ctrl+C)
8. [EXPECTED] Server starts without login prompt
9. [EXPECTED] Telemetry initialized (if enabled)

```
Phase 3: Auto Login Behavior
```
10. Clear token from keyring
11. `anaconda-mcp serve`
12. [EXPECTED] Browser opens automatically for login (non-blocking)
13. [EXPECTED] Server continues to start without waiting
14. Ctrl+C to stop

**Cleanup**: Re-login if needed: `anaconda login`

---

### AUTH-002: Anonymous Mode

**Purpose**: Test operation without authentication.

**Features Covered**:
- [x] Anonymous Mode (public channels only)

**Preconditions**:
- [PRE] anaconda-mcp configured
- [PRE] No Anaconda login (logged out)

**Steps**:

1. Ensure logged out: Clear any existing tokens
2. `anaconda-mcp serve` (ignore login prompt, Ctrl+C to stop)
3. Or use Claude Desktop with STDIO setup
4. Ask Claude: "List my conda environments"
5. [EXPECTED] Tool works with public channels
6. [EXPECTED] No crash or hard auth requirement
7. Ask Claude: "Create environment anon-test with Python 3.11"
8. [EXPECTED] Environment created using public channels

**Cleanup**: `conda remove -n anon-test --all -y`

---

### CONFIG-001: Environment Variables

**Purpose**: Test all environment variable configurations.

**Features Covered**:
- [x] Log Level (ANACONDA_MCP_LOG_LEVEL)
- [x] Disable Telemetry (ANACONDA_MCP_SEND_METRICS)
- [x] Environment Mode (ANACONDA_MCP_ENVIRONMENT)
- [x] Python Executable (ANACONDA_MCP_PYTHON_EXECUTABLE)

**Preconditions**:
- [PRE] anaconda-mcp installed

**Steps**:

```
Phase 1: Log Level
```
1. `ANACONDA_MCP_LOG_LEVEL=DEBUG anaconda-mcp serve` (Ctrl+C)
2. [EXPECTED] DEBUG level logs displayed
3. `ANACONDA_MCP_LOG_LEVEL=WARNING anaconda-mcp serve` (Ctrl+C)
4. [EXPECTED] Only WARNING and above displayed

```
Phase 2: Disable Telemetry
```
5. `ANACONDA_MCP_SEND_METRICS=false anaconda-mcp serve` (Ctrl+C)
6. [EXPECTED] No telemetry initialization logs
7. [EXPECTED] Server starts normally

```
Phase 3: Environment Mode
```
8. `ANACONDA_MCP_ENVIRONMENT=staging anaconda-mcp serve` (Ctrl+C)
9. [EXPECTED] Uses staging domain for Anaconda API
10. [EXPECTED] Logs may show staging configuration

```
Phase 4: Python Executable
```
11. Create alternate env: `conda create -n alt-python python=3.11 -y`
12. Get path: `conda run -n alt-python which python`
13. `ANACONDA_MCP_PYTHON_EXECUTABLE=/path/to/alt-python anaconda-mcp serve` (Ctrl+C)
14. [EXPECTED] Downstream servers spawned with specified Python

**Cleanup**: `conda remove -n alt-python --all -y`

---

---

## Test Environment Cleanup Script

```bash
#!/bin/bash
# Run after all E2E tests to clean up

echo "Cleaning up test environments..."

# Core flows
conda remove -n e2e-test-env --all -y 2>/dev/null

# Guard flows
conda remove -n guard-channel-test --all -y 2>/dev/null

# Regression flows
conda remove -n regress-name-test --all -y 2>/dev/null

# Auth flows
conda remove -n anon-test --all -y 2>/dev/null

# Config flows
conda remove -n alt-python --all -y 2>/dev/null

# Error flows
conda remove -n error-test-env --all -y 2>/dev/null

# Remove temp config
rm -f /tmp/custom-mcp.toml 2>/dev/null

echo "Cleanup complete!"
```

---

## Deployment-Specific Flows (P1/P2)

### SHARED-001: Shared Server Deployment

**Purpose**: Test network deployment with remote client access.

**Features Covered**:
- [x] HTTP Transport with `--host 0.0.0.0`
- [x] Remote client connection
- [x] Network accessibility

**Priority**: P1 (Release testing)

**Preconditions**:
- [PRE] anaconda-mcp installed on server machine
- [PRE] Network access between server and client
- [PRE] Firewall allows port 8888

**Steps**:

```
Phase 1: Start Shared Server
```
1. On server machine: `anaconda-mcp serve --host 0.0.0.0 --port 8888`
2. [EXPECTED] Server binds to all interfaces
3. [EXPECTED] Logs show "Listening on http://0.0.0.0:8888"

```
Phase 2: Remote Client Connection
```
4. On client machine, configure Claude Desktop:
   ```json
   {
     "mcpServers": {
       "anaconda-mcp": {
         "url": "http://<server-ip>:8888/mcp",
         "transport": "streamable-http"
       }
     }
   }
   ```
5. Restart Claude Desktop on client
6. Ask Claude: "List my conda environments"
7. [EXPECTED] Response shows server's conda environments

```
Phase 3: Verify Server-Side Execution
```
8. Ask Claude: "Create environment shared-test with Python 3.11"
9. On server, verify: `conda env list | grep shared-test`
10. [EXPECTED] Environment exists on SERVER (not client)

**Cleanup**:
- Server: `conda remove -n shared-test --all -y`
- Client: Remove server config from Claude Desktop

---

### DOCKER-001: Docker Deployment

**Purpose**: Test containerized deployment and ephemeral behavior.

**Features Covered**:
- [x] Docker image build
- [x] Container execution
- [x] Ephemeral storage (environments not persisted)

**Priority**: P2 (Major release testing)

**Preconditions**:
- [PRE] Docker installed
- [PRE] `ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN` set (for build)

**Steps**:

```
Phase 1: Build Image
```
1. `make docker-build` or `docker build -t anaconda-mcp .`
2. [EXPECTED] Image builds successfully

```
Phase 2: Run Container (HTTP)
```
3. `docker run -it -p 8000:8000 --rm anaconda-mcp`
4. [EXPECTED] Server starts inside container
5. [EXPECTED] Logs show "Listening on http://0.0.0.0:8000"

```
Phase 3: Connect and Test
```
6. Configure Claude Desktop with HTTP transport to localhost:8000
7. Ask Claude: "List conda environments"
8. [EXPECTED] Shows container's conda environments (minimal)

```
Phase 4: Verify Ephemeral Nature
```
9. Ask Claude: "Create environment docker-test with Python 3.11"
10. [EXPECTED] Environment created inside container
11. Stop container (Ctrl+C)
12. Start new container: `docker run -it -p 8000:8000 --rm anaconda-mcp`
13. Ask Claude: "List conda environments"
14. [EXPECTED] docker-test environment is GONE (ephemeral)

**Cleanup**: None (container is ephemeral)

**Note**: Docker deployment is for dev/testing only. Environments are NOT persisted.

---

## Test Execution Order

### Tier 1: Every PR (Local Native)
1. **REGRESS-001** - Verify known issues first
2. **CORE-001** - Full happy path
3. **GUARD-001** - Guardrails

### Tier 2: Release Testing (Local + Extended)
4. **CORE-002** - HTTP transport
5. **CORE-003** - Config management
6. **AUTH-001** - Authentication
7. **AUTH-002** - Anonymous mode
8. **CONFIG-001** - Environment variables
9. **CLI-001** - Server discovery
10. **CLI-002** - Advanced options
11. **SHARED-001** - Shared server deployment
12. **Manual Dev Mode** - Negative scenarios (see below)

### Tier 3: Major Release (All Deployments)
13. **DOCKER-001** - Docker deployment

---

## Manual Dev Mode Testing (Negative Scenarios)

**Purpose**: Quick validation of error handling without full E2E overhead.

**Priority**: P2 (after E2E happy paths are covered)

**When**: Release testing, after E2E flows pass

### Setup Dev Mode

```bash
# Terminal 1: Start server in dev mode
cd /path/to/anaconda-mcp
conda activate anaconda-mcp-dev
PYTHONPATH=src python -m anaconda_mcp serve --port 2391

# Terminal 2: Use curl for direct API calls
```

### Negative Scenarios Checklist

Test each scenario with direct API call, verify error response:

#### Tool Errors
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

# Non-existent package
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"conda_install_packages","arguments":{"env_name":"base","packages":["fake-pkg-xyz"]}}}'
# [EXPECTED] Error: package not found
```

#### Protocol Errors
```bash
# Invalid tool name
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"invalid_tool"}}'
# [EXPECTED] Error code: -32601 (Method not found)

# Missing required params
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"conda_create_environment","arguments":{}}}'
# [EXPECTED] Error code: -32602 (Invalid params)

# Malformed JSON
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d 'not valid json'
# [EXPECTED] Error code: -32700 (Parse error)
```

### Quick Checklist

| Scenario | Command | Expected Error | Verified |
|----------|---------|----------------|----------|
| Duplicate env | create "base" | Already exists | [ ] |
| Missing env | delete "xyz" | Not found | [ ] |
| Missing package | install "fake" | Not found | [ ] |
| Invalid tool | call "invalid" | -32601 | [ ] |
| Missing params | create {} | -32602 | [ ] |
| Bad JSON | malformed | -32700 | [ ] |
| Server down | any call | Connection refused | [ ] |

### When to Automate (P3 - Future)

Move to API automation when:
- E2E flows stable and passing
- Time available for automation investment
- Need regression protection for error handling

---

## Quick Smoke Test (5 minutes)

For rapid validation, run only:

1. **CORE-001** (Phases 1-2 only: Install + Setup)
2. **REGRESS-001** (Phase 1 only: Extra env vars)
3. Quick tool check: Ask Claude "List my conda environments"

If these pass, the core system is functional.

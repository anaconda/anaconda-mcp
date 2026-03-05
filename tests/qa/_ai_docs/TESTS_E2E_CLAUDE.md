# E2E Flows (macOS Only)

> **Clients**: Claude Desktop (STDIO) or Cursor (HTTP). See [TEST_MATRIX.md](./TEST_MATRIX.md) for transport/client mapping.

## Prerequisites

**Before running any test flow**, complete these steps:

### 1. Determine Test Configuration

Record the configuration you are testing:

| Setting | Your Value |
|---------|------------|
| Python version | _______ (3.10, 3.11, 3.12, or 3.13) |
| Transport mode | STDIO (HTTP not supported with Claude Desktop - see KI-009) |
| anaconda-mcp version | _______ (run: `conda list \| grep anaconda-mcp`) |
| environments-mcp-server version | _______ (run: `conda list \| grep environments-mcp`) |

See [TEST_MATRIX.md](./TEST_MATRIX.md) for recommended combinations.

### 2. Setup Environment

Follow [QUICK_START.md](./QUICK_START.md):

1. Install from conda channels OR source (Option A or B)
2. Configure your client:

**For STDIO (Claude Desktop)**:
```bash
anaconda-mcp claude-desktop setup-config
# Restart Claude Desktop (Cmd+Q, then reopen)
```

**For HTTP (Cursor)**:
```bash
# Start server first
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
# Add config to ~/.cursor/mcp.json (see QUICK_START.md)
# Restart Cursor
```

### 3. Verify Ready State

**All tests start from this state:**
- Claude Desktop is running
- Anaconda MCP server is connected (check for tools icon in Claude)
- You can ask Claude: "List my conda environments" and get a response

If this doesn't work, troubleshoot per [KNOWN_ISSUES.md](./KNOWN_ISSUES.md#troubleshooting) before proceeding.

---

## Flow Summary

| Flow ID | Name | Priority |
|---------|------|----------|
| CORE-001 | Full Tools Flow | P0 |
| GUARD-001 | Guardrails | P0 |
| AUTH-001 | Anonymous Mode | P1 |
| AUTH-002 | Authenticated Mode | P1 |
| REGRESS-001 | Known Issues | P0 |

---

## CORE-001: Full Tools Flow

**Purpose**: E2E happy path covering all 6 tools.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "List my conda environments" | Uses `conda_list_environments` |
| 2 | Ask: "Create environment e2e-test with Python 3.11" | Uses `conda_create_environment` |
| 3 | Ask: "Install numpy in e2e-test" | Uses `conda_install_packages` |
| 4 | Ask: "What packages are in e2e-test?" | Uses `conda_list_environment_packages` |
| 5 | Ask: "Remove numpy from e2e-test" | Uses `conda_remove_packages` |
| 6 | Ask: "Delete e2e-test environment" | Uses `conda_remove_environment` |
| 7 | Ask: "List my conda environments" | e2e-test not in list |

---

## GUARD-001: Guardrails

**Purpose**: Verify guardrail behaviors.

### Prep
```bash
conda create -n guard-test python=3.11 -y
```

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "Install nonexistent-package-xyz123 in guard-test" | Error, no pip fallback |
| 2 | Ask: "Delete guard-test environment" | Claude asks confirmation |
| 3 | Confirm deletion | Environment removed |

---

## AUTH-001: Anonymous Mode

**Purpose**: Test without authentication.

### Prep
```bash
anaconda logout 2>/dev/null || true
```

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "List my conda environments" | Works with public channels |
| 2 | Ask: "Create environment anon-test with Python 3.11" | Environment created |

### Cleanup
```bash
conda remove -n anon-test --all -y
```

---

## AUTH-002: Authenticated Mode

**Purpose**: Test with Anaconda authentication (enables private channels + telemetry).

### Prep
```bash
# Login to Anaconda (browser will open)
anaconda login

# Verify logged in
anaconda whoami
# [EXPECTED] Shows your username

# Restart Claude Desktop to pick up auth state
# Cmd+Q, then reopen Claude Desktop
```

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "List my conda environments" | Works |
| 2 | Ask: "Create environment auth-test with Python 3.11" | Environment created |
| 3 | Ask: "Install numpy in auth-test" | Package installed |
| 4 | Check server logs for telemetry | "Initializing telemetry" message present |

### Verify Telemetry (optional)
```bash
# Run server with debug logging to see telemetry
ANACONDA_MCP_LOG_LEVEL=DEBUG anaconda-mcp serve --port 8888 2>&1 | grep -i telemetry
# [EXPECTED] "Initializing telemetry" appears
```

### Cleanup
```bash
conda remove -n auth-test --all -y
```

---

## REGRESS-001: Known Issues

**Purpose**: Regression tests for fixed bugs.

### Prep
```bash
conda create -n regress-test python=3.11 -y
```

| Step | Issue | Action | Expected |
|------|-------|--------|----------|
| 1 | KI-002 | Ask: "List my conda environments" | Shows "regress-test" (not "base") |
| 2 | KI-003 | Ask: "Install numpy in regress-test" | Found by name, installs |
| 3 | KI-001 | Ask: "Delete regress-test" | Actually deleted |
| 4 | KI-001 | Run: `conda env list \| grep regress-test` | Empty (gone) |

---

## Test Execution Order

1. REGRESS-001 - Verify fixed issues first
2. CORE-001 - Full happy path
3. GUARD-001 - Guardrails
4. AUTH-001 - Anonymous mode
5. AUTH-002 - Authenticated mode

---

## Cleanup

```bash
conda remove -n e2e-test --all -y 2>/dev/null
conda remove -n guard-test --all -y 2>/dev/null
conda remove -n regress-test --all -y 2>/dev/null
conda remove -n anon-test --all -y 2>/dev/null
```

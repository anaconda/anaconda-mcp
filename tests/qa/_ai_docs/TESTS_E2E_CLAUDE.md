# E2E Flows - Claude Desktop (macOS Only)

## Overview

End-to-end flows requiring Claude Desktop interaction. Must run manually on macOS.

## Prerequisites

See [QUICK_START.md](./QUICK_START.md) for installation.

---

## Flow Summary

| Flow ID | Name | Transport | Priority |
|---------|------|-----------|----------|
| CORE-001 | Full Setup & Tools | STDIO | P0 |
| CORE-002 | Full Setup & Tools | HTTP | P0 |
| GUARD-001 | Guardrails | Both | P0 |
| AUTH-001 | Anonymous Mode | Both | P1 |
| REGRESS-001 | Known Issues | Both | P0 |

---

## CORE-001: Full Setup & Tools (STDIO)

**Purpose**: E2E happy path with STDIO transport.

### Setup
```bash
anaconda-mcp claude-desktop setup-config
# Restart Claude Desktop
```

### Test
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

## CORE-002: Full Setup & Tools (HTTP)

**Purpose**: E2E happy path with HTTP transport.

### Setup
```bash
# Terminal 1: Start server (keeps running)
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888

# Terminal 2: Configure Claude Desktop
anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888
# Restart Claude Desktop
```

### Test
Same as CORE-001 steps 1-6.

### Cleanup
```bash
# Stop server (Ctrl+C in Terminal 1)
anaconda-mcp claude-desktop setup-config  # Restore STDIO
```

---

## GUARD-001: Guardrails

**Purpose**: Verify guardrail behaviors.

### Setup
Choose transport:
- **STDIO**: `anaconda-mcp claude-desktop setup-config`
- **HTTP**: Start server + `anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888`

### Test
| Step | Action | Expected |
|------|--------|----------|
| 1 | Create: `conda create -n guard-test python=3.11 -y` | Environment ready |
| 2 | Ask: "Install nonexistent-package-xyz123 in guard-test" | Error, no pip fallback |
| 3 | Ask: "Delete guard-test environment" | Claude asks confirmation |
| 4 | Confirm deletion | Environment removed |

---

## AUTH-001: Anonymous Mode

**Purpose**: Test without authentication.

### Setup
```bash
# Clear auth tokens
anaconda logout 2>/dev/null || true
```

Choose transport:
- **STDIO**: `anaconda-mcp claude-desktop setup-config`
- **HTTP**: Start server + configure

### Test
| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "List my conda environments" | Works with public channels |
| 2 | Ask: "Create environment anon-test with Python 3.11" | Environment created |

### Cleanup
```bash
conda remove -n anon-test --all -y
```

---

## REGRESS-001: Known Issues

**Purpose**: Regression tests for fixed bugs.

### Setup
Choose transport (STDIO or HTTP).

### Test
| Step | Issue | Action | Expected |
|------|-------|--------|----------|
| 1 | KI-002 | Create `conda create -n regress-test python=3.11 -y` | - |
| 2 | KI-002 | Ask: "List my conda environments" | Shows "regress-test" (not "base") |
| 3 | KI-003 | Ask: "Install numpy in regress-test" | Found by name, installs |
| 4 | KI-001 | Ask: "Delete regress-test" | Actually deleted |
| 5 | KI-001 | Verify: `conda env list \| grep regress-test` | Empty (gone) |

---

## Test Execution Order

### Every PR
1. REGRESS-001 (both transports)
2. CORE-001 (STDIO)
3. GUARD-001

### Release Testing
4. CORE-002 (HTTP)
5. AUTH-001

---

## Cleanup Script

```bash
conda remove -n e2e-test --all -y 2>/dev/null
conda remove -n guard-test --all -y 2>/dev/null
conda remove -n regress-test --all -y 2>/dev/null
conda remove -n anon-test --all -y 2>/dev/null
anaconda-mcp claude-desktop setup-config  # Restore STDIO
```

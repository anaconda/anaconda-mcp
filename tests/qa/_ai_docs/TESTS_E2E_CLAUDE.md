# E2E Flows - Claude Desktop (macOS Only)

## Prerequisites

See [QUICK_START.md](./QUICK_START.md) for:
- Installation (conda channels or source)
- Starting server (STDIO or HTTP)
- Configuring Claude Desktop

**Before each test**: Activate conda environment
```bash
conda activate anaconda-mcp-testing
```

---

## Test Variables

| Variable | Options |
|----------|---------|
| Transport | STDIO, HTTP |
| Python | 3.10, 3.11, 3.12, 3.13 |

Run each test flow with different combinations per [TEST_MATRIX.md](./TEST_MATRIX.md).

---

## Flow Summary

| Flow ID | Name | Priority |
|---------|------|----------|
| CORE-001 | Full Tools Flow | P0 |
| GUARD-001 | Guardrails | P0 |
| AUTH-001 | Anonymous Mode | P1 |
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

---

## Cleanup

```bash
conda remove -n e2e-test --all -y 2>/dev/null
conda remove -n guard-test --all -y 2>/dev/null
conda remove -n regress-test --all -y 2>/dev/null
conda remove -n anon-test --all -y 2>/dev/null
```

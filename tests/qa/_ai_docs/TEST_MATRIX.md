# Test Matrix

## Facts

### What We Support

| Dimension | Values | Source |
|-----------|--------|--------|
| **OS** | Linux, macOS, Windows | `pyproject.toml`, `consts.py` |
| **Python** | 3.10, 3.11, 3.12, 3.13 | `pyproject.toml`: `>=3.10,<3.14` |
| **Transport** | STDIO, HTTP | `claude_desktop.py` |
| **Client** | Claude Desktop | Only supported client |
| **Deployment** | Local, Shared Server, Docker | Documentation |

### What We Have

| Environment | OS | Claude Desktop | Available |
|-------------|-----|----------------|-----------|
| QA Machine | macOS | Yes | Always |
| GitHub Runner | Linux | No | CI |
| GitHub Runner | Windows | No | CI |
| Win365 | Windows | No | On request |

### What Differs by OS

| Component | OS-Specific? |
|-----------|--------------|
| Config path | **Yes** - different per OS |
| Server logic | No |
| MCP protocol | No |
| Authentication | No |
| Tools | No |

**Outcome**: OS testing needed mainly for config path verification.

### What Differs by Python Version

| Concern | Risk |
|---------|------|
| 3.10 (minimum) | Boundary - must verify |
| 3.11 | CI baseline - tested |
| 3.12 | Middle - low risk |
| 3.13 (maximum) | Boundary - must verify |

**Outcome**: Test boundaries (3.10, 3.13) + CI baseline (3.11). Skip 3.12.

---

## Test Strategy by Platform

### Phase 1: Manual Validation (macOS)

Run all tests manually on macOS first to validate flows work:

| Step | What | Document |
|------|------|----------|
| 1 | Run CLI tests manually | TESTS_CLI.md |
| 2 | Run Config tests manually | TESTS_CONFIG.md |
| 3 | Fix/adjust flows if needed | Update docs |
| 4 | Run E2E Claude tests | TESTS_E2E_CLAUDE.md |

**Why macOS first**: Has Claude Desktop + can validate all flows before automation.

### Phase 2: Automate CLI/Config (CI Runners)

After manual validation passes, automate on CI:

| Platform | What to Automate |
|----------|------------------|
| Linux runner | TESTS_CLI.md, TESTS_CONFIG.md |
| Windows runner | TESTS_CLI.md, TESTS_CONFIG.md |
| macOS runner | TESTS_CLI.md, TESTS_CONFIG.md |

### Phase 3: Release Testing (macOS Manual)

Before release, run full E2E manually on macOS:

| What | Document |
|------|----------|
| Full E2E with Claude Desktop | TESTS_E2E_CLAUDE.md |

### Platform Capabilities

| Platform | CLI Tests | Config Tests | E2E Claude |
|----------|-----------|--------------|------------|
| macOS (manual) | ✅ | ✅ | ✅ |
| macOS (CI) | ✅ | ✅ | ❌ No Claude |
| Linux (CI) | ✅ | ✅ | ❌ No Claude |
| Windows (CI) | ✅ | ✅ | ❌ No Claude |
| Win365 | ✅ | ✅ | ❌ No Claude |

---

## Summary

### Must Have (P0)

| What | Where | Why |
|------|-------|-----|
| Full E2E flows | macOS | Only platform with Claude Desktop |
| CLI smoke tests | All 3 OS | Verify OS-specific paths work |
| Python 3.11 | CI | Current baseline |
| STDIO transport | macOS E2E | Default user experience |
| HTTP transport | macOS E2E | Alternative setup |

### Nice to Have (P1)

| What | Where | Why |
|------|-------|-----|
| Python 3.10 | Linux CI | Minimum boundary |
| Python 3.13 | Linux CI | Maximum boundary |
| Shared Server flow | macOS | Enterprise scenario |
| Extended CLI tests | All 3 OS | More coverage |

### Depends on Time / Ask Product (P2)

| What | Question |
|------|----------|
| Docker deployment | Is this GA scope or dev-only? |
| Python 3.12 | Skip if time limited (covered by 3.11) |
| Multi-client testing | Enterprise priority? |

---

## Recommended Matrix

### Every PR (CI)

| OS | Python | What to Run |
|----|--------|-------------|
| Linux | 3.11 | TESTS_CLI.md, TESTS_CONFIG.md |
| Windows | 3.11 | TESTS_CLI.md, TESTS_CONFIG.md |
| macOS | 3.11 | TESTS_CLI.md, TESTS_CONFIG.md |

### Before Release (Manual)

| OS | Python | What to Run |
|----|--------|-------------|
| macOS | 3.11 | TESTS_E2E_CLAUDE.md (all flows) |
| Linux | 3.10 | TESTS_CLI.md (boundary check) |
| Linux | 3.13 | TESTS_CLI.md (boundary check) |

### If Time Permits

| What | When |
|------|------|
| Shared Server flow | Release |
| Docker flow | Major release |

---

## CI Workflow

```yaml
# .github/workflows/tests.yml
jobs:
  cli-tests:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ['3.11']
    steps:
      - uses: conda-incubator/setup-miniconda@v3
      - run: conda install anaconda-mcp environments-mcp-server -y
      - run: |
          anaconda-mcp --help
          anaconda-mcp claude-desktop path
          anaconda-mcp discover
          anaconda-mcp serve --port 8888 &
          sleep 10
          curl -sf http://localhost:8888/mcp -X POST \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

  # Release only
  boundary-tests:
    if: github.ref == 'refs/heads/main'
    strategy:
      matrix:
        python: ['3.10', '3.13']
    runs-on: ubuntu-latest
    steps:
      - uses: conda-incubator/setup-miniconda@v3
        with:
          python-version: ${{ matrix.python }}
      - run: conda install anaconda-mcp -y
      - run: anaconda-mcp --help
```

---

## Quick Reference

| Question | Answer |
|----------|--------|
| Which OS for E2E? | macOS only |
| Which OS for CLI? | All 3 |
| Which Python versions? | 3.10, 3.11, 3.13 |
| Skip Python 3.12? | Yes |
| Test Docker? | Only if time permits |
| Test Shared Server? | Release only |

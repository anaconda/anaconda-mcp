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

## Test Types

| Type | Document | Requires Claude | Automatable |
|------|----------|-----------------|-------------|
| E2E Claude | TESTS_E2E_CLAUDE.md | Yes | No |
| CLI | TESTS_CLI.md | No | Yes |
| Config | TESTS_CONFIG.md | No | Yes |
| API Tools | TESTS_API_TOOLS.md | No | Yes |

### API Tool Tests (New)

Direct API calls to each MCP tool - validates tool functionality without Claude Desktop.

**Setup**:
```bash
# Start server in dev mode
anaconda-mcp serve --port 8888 &
```

**Test each tool via curl**:
```bash
# conda_list_environments
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"conda_list_environments","arguments":{}}}'

# conda_create_environment
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"conda_create_environment","arguments":{"name":"api-test-env","python_version":"3.11"}}}'

# conda_install_packages
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"conda_install_packages","arguments":{"env_name":"api-test-env","packages":["numpy"]}}}'

# conda_remove_packages
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"conda_remove_packages","arguments":{"env_name":"api-test-env","packages":["numpy"]}}}'

# conda_delete_environment
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"conda_delete_environment","arguments":{"name":"api-test-env"}}}'
```

---

## Available Environments

| Environment | OS | Claude Desktop | Use For |
|-------------|-----|----------------|---------|
| QA macOS | macOS | ✅ Yes | E2E Claude, CLI, Config, API Tools |
| Win365 | Windows | ❌ No | CLI, Config, API Tools |
| GitHub Runner | Linux/Windows | ❌ No | Automation (Phase 2) |

---

## Test Strategy

### Phase 1: Manual Testing (Priority 1)

**Goal**: Validate all test flows work before automation.

| Platform | Python | Test Types | Document |
|----------|--------|------------|----------|
| macOS | 3.11 | CLI, Config | TESTS_CLI.md, TESTS_CONFIG.md |
| macOS | 3.11 | E2E Claude | TESTS_E2E_CLAUDE.md |
| Win365 | 3.10 | CLI, Config, API Tools | TESTS_CLI.md, TESTS_CONFIG.md, TESTS_API_TOOLS.md |

**Why different Python versions**:
- macOS with 3.11 = CI baseline
- Win365 with 3.10 = minimum boundary
- Better coverage across platforms

### Phase 2: Automation (If Time Allows)

After manual validation passes:

| Platform | Python | What to Automate |
|----------|--------|------------------|
| Linux runner | 3.11 | CLI, Config, API Tools |
| Windows runner | 3.11 | CLI, Config, API Tools |
| Linux runner | 3.13 | CLI (boundary check) |

### Phase 3: Release Testing

| Platform | Python | What |
|----------|--------|------|
| macOS | 3.11 | Full E2E Claude (manual) |

---

## Efficient Test Matrix

By distributing test types across platforms with different Python versions:

| What | Where | Python | Coverage |
|------|-------|--------|----------|
| E2E Claude | macOS | 3.11 | Full AI integration |
| API Tools | Win365 | 3.10 | Tool functionality + min Python |
| CLI/Config | Both | 3.10, 3.11 | OS paths + Python versions |

**Result**:
- 2 Python versions tested (3.10, 3.11)
- 2 OS tested (macOS, Windows)
- All tool functionality validated (via API on Win365)
- AI integration validated (via Claude on macOS)

### Optional (If Time)
| What | Where | Python |
|------|-------|--------|
| API Tools | Linux runner | 3.13 |

This adds Python 3.13 boundary without duplicating other tests.

---

## Platform Capabilities

| Test Type | macOS | Win365 | Linux CI | Windows CI |
|-----------|-------|--------|----------|------------|
| E2E Claude | ✅ | ❌ | ❌ | ❌ |
| CLI | ✅ | ✅ | ✅ | ✅ |
| Config | ✅ | ✅ | ✅ | ✅ |
| API Tools | ✅ | ✅ | ✅ | ✅ |

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

# Test Matrix

## Available Resources

| Resource | OS | Claude Desktop | Cursor | Python |
|----------|-----|----------------|--------|--------|
| QA Engineer 1 | macOS | Yes | Yes | Can install any |
| QA Engineer 2 | macOS | Yes | Yes | Can install any |
| QA Engineer 3 (?) | macOS | Yes | Yes | Can install any |
| Win365 | Windows | No | No | Can install any |
| GitHub Runners | Linux/Windows | No | No | CI matrix |

## Supported Versions

| Dimension | Values |
|-----------|--------|
| Python | 3.10, 3.11, 3.12, 3.13 |
| Transport | STDIO, HTTP |
| OS | Linux, macOS, Windows |

## Transport / Client Matrix

| Transport | Claude Desktop | Cursor | API (curl) |
|-----------|----------------|--------|------------|
| STDIO | Yes | Yes | N/A |
| HTTP | **No** (KI-009) | Yes | Yes |

> **Note**: Claude Desktop only supports STDIO transport. HTTP transport testing requires Cursor or direct API calls.

---

## Phase 1: Manual Testing (2 QA Engineers)

### E2E Tests (macOS only)

| QA | Client | Python | Transport | Document |
|----|--------|--------|-----------|----------|
| QA 1 | Claude Desktop | 3.10 | STDIO | TESTS_E2E_CLAUDE.md |
| QA 2 | Cursor | 3.11 | HTTP | TESTS_E2E_CLAUDE.md |

**Coverage**: 2 Python versions + 2 transports + 2 clients

**Optional (if 3rd QA or time)**:
| QA | Client | Python | Transport |
|----|--------|--------|-----------|
| QA 3 | Claude Desktop | 3.13 | STDIO |

### CLI, Config, API-Tools Tests

Split across platforms for OS coverage:

| QA | Platform | Python | Tests |
|----|----------|--------|-------|
| QA 1 | macOS | 3.10 | TESTS_CLI.md, TESTS_CONFIG.md |
| QA 2 | Win365 | 3.11 | TESTS_CLI.md, TESTS_CONFIG.md, TESTS_API_TOOLS.md |

**Coverage**: 2 OS + 2 Python versions + all test types

---

## Phase 1 Summary

| What | Who | Where | Client | Python | Transport |
|------|-----|-------|--------|--------|-----------|
| E2E STDIO | QA 1 | macOS | Claude Desktop | 3.10 | STDIO |
| E2E HTTP | QA 2 | macOS | Cursor | 3.11 | HTTP |
| CLI + Config | QA 1 | macOS | - | 3.10 | - |
| CLI + Config + API Tools | QA 2 | Win365 | - | 3.11 | - |

**Total coverage from Phase 1**:
- ✅ Python 3.10, 3.11
- ✅ STDIO (Claude Desktop), HTTP (Cursor) transport
- ✅ macOS, Windows
- ✅ All test types

---

## Phase 2: Automation (If Time Allows)

After manual testing passes, automate on CI runners:

| Runner | Python | Tests |
|--------|--------|-------|
| Linux | 3.11 | CLI, Config, API-Tools |
| Windows | 3.11 | CLI, Config, API-Tools |
| Linux | 3.13 | CLI (boundary check) |

**Additional coverage**:
- ✅ Linux OS
- ✅ Python 3.13 boundary

---

## Quick Reference

### Minimum (2 QAs, Phase 1 only)

| Coverage | How |
|----------|-----|
| Python 3.10 | QA 1 on macOS |
| Python 3.11 | QA 2 on macOS + Win365 |
| STDIO | QA 1 E2E |
| HTTP | QA 2 E2E |
| macOS | QA 1 + QA 2 E2E |
| Windows | QA 2 on Win365 |

### Extended (Phase 2)

| Coverage | How |
|----------|-----|
| Python 3.13 | Linux runner |
| Linux | GitHub runner |

### Skip

| What | Why |
|------|-----|
| Python 3.12 | Between boundaries, covered by 3.11 |
| macOS runner | Already tested manually |

---

## Test Assignment

### QA 1 (macOS, Python 3.10)

```
1. Install Python 3.10
2. Run TESTS_E2E_CLAUDE.md (STDIO transport)
3. Run TESTS_CLI.md
4. Run TESTS_CONFIG.md
```

### QA 2 (macOS + Win365, Python 3.11)

```
macOS:
1. Install Python 3.11
2. Run TESTS_E2E_CLAUDE.md (HTTP transport)

Win365:
3. Install Python 3.11
4. Run TESTS_CLI.md
5. Run TESTS_CONFIG.md
6. Run TESTS_API_TOOLS.md
```

### Optional QA 3 (macOS, Python 3.13)

```
1. Install Python 3.13
2. Run TESTS_E2E_CLAUDE.md (STDIO transport)
```

---

## Outcome

| Phase | Effort | Coverage |
|-------|--------|----------|
| Phase 1 | 2 QAs, ~1 day | Python 3.10-3.11, macOS+Windows, all transports |
| Phase 2 | CI setup | +Linux, +Python 3.13 |

**Minimum actions, maximum coverage**.

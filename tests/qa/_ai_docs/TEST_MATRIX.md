# Test Matrix

## Scope Assumptions

| Assumption | Decision |
|------------|----------|
| Installation source | anaconda-mcp=1.0.0.rc.1, environments-mcp-server=1.0.0.rc.1; anaconda-connector resolved as transitive dep (see [Q1](./OPEN_QUESTIONS.md#q1-installation-source)) |
| Platform coverage | macOS + Windows for manual; Linux via CI (see [Q2](./OPEN_QUESTIONS.md#q2-cliapiconfig-platform-coverage)) |
| Auth scope | Anonymous + Authenticated basic (see [Q3](./OPEN_QUESTIONS.md#q3-authentication--related-features)) |
| Python versions | All supported: 3.10, 3.11, 3.12, 3.13 (see [Q4](./OPEN_QUESTIONS.md#q4-python-version-coverage)) |

## Available Resources

| Resource | OS | Claude Desktop | Cursor | Python | Notes |
|----------|-----|----------------|--------|--------|-------|
| QA Engineer 1 | macOS | Yes | Yes | Can install any | Main QA, full capacity |
| QA Engineer 2 | macOS + Win365 | Yes | Yes (macOS) | Can install any | Main QA, full capacity |
| QA Engineer 3 | Windows (preferred) | Yes | No | Can install any | Additional QA, ~2h capacity |
| GitHub Runners | Linux/Windows | No | No | CI matrix | CI only |

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

> **Constraint**: Cursor is not available on Windows or Linux — Cursor-based E2E requires macOS. Claude Desktop is available on Windows (lower priority), covered by QA 3.

---

## Phase 1: Manual Testing (3 QA Engineers)

### E2E Tests

| QA | OS | Client | Python | Transport | Document |
|----|-----|--------|--------|-----------|----------|
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | TESTS_E2E.md |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | TESTS_E2E.md |
| QA 1 | macOS | Claude Desktop | 3.12 | STDIO | TESTS_E2E.md |
| QA 1 | macOS | Claude Desktop | 3.13 | STDIO | TESTS_E2E.md |
| QA 2 | macOS | Cursor | 3.12 | STDIO | TESTS_E2E.md |
| QA 2 | macOS | Cursor | 3.13 | HTTP | TESTS_E2E.md |
| QA 3 | Windows | Claude Desktop | 3.13 | STDIO | TESTS_E2E.md |

> Each E2E run includes both `AUTH-001` (anonymous) and `AUTH-002` (authenticated) test cases.

**Coverage**: All 4 Python versions (via QA 1) + all transports + both clients + macOS & Windows

**Optional** (if time allows):

| QA | OS | Client | Python | Transport | Document |
|----|-----|--------|--------|-----------|----------|
| QA 2 | macOS | Claude Code | 3.10 | HTTP | TESTS_E2E.md |
| QA 3 | Windows | Claude Desktop | 3.10 | STDIO | TESTS_E2E.md |

### Regression Tests (Known Issues)

Run as part of the scheduled E2E session for that configuration — no extra setup.

| Test | QA | Config | Rationale |
|------|----|--------|-----------|
| REGRESS-002 (KI-003) | QA 2 | Cursor, HTTP, 3.13 | Confirmed reproduction environment |
| REGRESS-002 (KI-003) | QA 1 | Claude Desktop, STDIO, 3.10 | STDIO transport + 3.10 boundary |
| REGRESS-002 (KI-003) | QA 2 | Claude Code, HTTP, 3.10 | Observe Claude Code behavior on known regression |

### CLI, Config, API-Tools Tests

Owned by QA 2, split across platforms for OS coverage:

| QA | Platform | Python | Tests |
|----|----------|--------|-------|
| QA 2 | macOS | 3.10 | TESTS_CLI.md, TESTS_CONFIG.md |
| QA 2 | Win365 | 3.13 | TESTS_CLI.md, TESTS_CONFIG.md, TESTS_API_TOOLS.md |

> `TESTS_CONFIG.md` includes `ENV-002` (telemetry control), which requires an authenticated session.

**Coverage**: 2 OS + 2 Python boundary versions + all low-level test types

---

## Phase 1 Summary

| What | Who | OS | Client | Python | Transport |
|------|-----|----|--------|--------|-----------|
| E2E STDIO | QA 1 | macOS | Claude Desktop | 3.10, 3.11, 3.12, 3.13 | STDIO |
| E2E STDIO | QA 1 | macOS | Cursor | 3.13 | STDIO |
| E2E HTTP | QA 2 | macOS | Cursor | 3.13 | HTTP |
| E2E STDIO | QA 3 | Windows | Claude Desktop | 3.13 | STDIO |
| CLI + Config | QA 2 | macOS | - | 3.10 | - |
| CLI + Config + API Tools | QA 2 | Win365 | - | 3.13 | - |

**Total coverage from Phase 1**:
- ✅ Python 3.10, 3.11, 3.12, 3.13 (all supported versions, via E2E)
- ✅ Python 3.10, 3.13 (boundaries) for low-level tests
- ✅ STDIO (Claude Desktop + Cursor) and HTTP (Cursor) transport
- ✅ Both clients: Claude Desktop + Cursor
- ✅ macOS + Windows
- ✅ All test types
- ✅ Auth tested via AUTH-001/AUTH-002 (E2E) and ENV-002 (Config)

---

## Phase 2: Automation (If Time Allows)

After manual testing passes, automate on CI runners:

| Runner | Python | Tests |
|--------|--------|-------|
| Linux | 3.10 | CLI, Config, API-Tools |
| Linux | 3.13 | CLI, Config, API-Tools |

**Additional coverage**:
- ✅ Linux OS
- ✅ Python 3.10 + 3.13 boundaries on Linux

---

## Quick Reference

### Phase 1 (3 QAs)

| Coverage | How |
|----------|-----|
| Python 3.10 | QA 1 E2E (Claude Desktop STDIO) + QA 2 low-level (macOS) |
| Python 3.11 | QA 1 E2E (Claude Desktop STDIO) |
| Python 3.12 | QA 1 E2E (Claude Desktop STDIO) |
| Python 3.13 | QA 1 E2E (Claude Desktop + Cursor STDIO) + QA 2 E2E (HTTP) + QA 3 E2E (Windows) + QA 2 low-level (Win365) |
| STDIO | QA 1 (Claude Desktop + Cursor) + QA 3 (Claude Desktop, Windows) |
| HTTP | QA 2 (Cursor, macOS) |
| macOS | QA 1 + QA 2 |
| Windows | QA 3 E2E + QA 2 low-level (Win365) |
| Auth (anon + login flow) | All QAs via AUTH-001/002 in E2E + QA 2 via ENV-002 (Config) |

### Extended (Phase 2)

| Coverage | How |
|----------|-----|
| Linux OS | GitHub runners |
| Python 3.10 + 3.13 on Linux | GitHub runners |

### Skip

| What | Why |
|------|-----|
| Python 3.11, 3.12 in low-level tests | Covered by E2E (QA 1); boundaries sufficient for CLI/Config/API-Tools |
| macOS runner | Already tested manually |
| Private channels / telemetry backend | Out of scope (Q3 Option C) |
| Cursor on Windows | Not available on Windows (KI-009 + platform constraint) |

---

## Test Assignment

### QA 1 — macOS, E2E focus (all Python versions × client combinations)

```
E2E — Claude Desktop, STDIO, all Python versions:
[ ] 1. Install Python 3.10 (anaconda-mcp=1.0.0.rc.1, environments-mcp-server=1.0.0.rc.1)
[ ]    Run TESTS_E2E.md — Claude Desktop, STDIO — AUTH-001 + AUTH-002
[ ]    Run REGRESS-002 (KI-003) — see TESTS_E2E.md

[ ] 2. Install Python 3.11 (same versions)
[ ]    Run TESTS_E2E.md — Claude Desktop, STDIO — AUTH-001 + AUTH-002

[ ] 3. Install Python 3.12 (same versions)
[ ]    Run TESTS_E2E.md — Claude Desktop, STDIO — AUTH-001 + AUTH-002

[ ] 4. Install Python 3.13 (same versions)
[ ]    Run TESTS_E2E.md — Claude Desktop, STDIO — AUTH-001 + AUTH-002

E2E — Cursor, STDIO (different client, same Python 3.13 env):
[ ] 5. Run TESTS_E2E.md — Cursor, STDIO — AUTH-001 + AUTH-002
```

### QA 2 — macOS + Win365, E2E (HTTP/Cursor once) + all low-level tests

```
macOS — E2E:
[ ] 1. Install Python 3.13 (anaconda-mcp=1.0.0.rc.1, environments-mcp-server=1.0.0.rc.1)
[ ]    Run TESTS_E2E.md — Cursor, HTTP — AUTH-001 + AUTH-002
[ ]    Run REGRESS-002 (KI-003) — see TESTS_E2E.md

macOS — Low-level (Python 3.10):
[ ] 2. Install Python 3.10 (same versions)
[ ]    Run TESTS_CLI.md
[ ]    Run TESTS_CONFIG.md — includes ENV-002 (telemetry, requires login)

Win365 — Low-level (Python 3.13):
[ ] 3. Install Python 3.13 (same versions)
[ ]    Run TESTS_CLI.md
[ ]    Run TESTS_CONFIG.md — includes ENV-002 (telemetry, requires login)
[ ]    Run TESTS_API_TOOLS.md
```

### QA 3 — Windows, E2E only (~2 working hours)

```
[ ] 1. Install Python 3.13 on Windows
[ ]    Install Claude Desktop on Windows
[ ]    Install anaconda-mcp=1.0.0.rc.1, environments-mcp-server=1.0.0.rc.1 (Windows)
[ ] 2. Run TESTS_E2E.md — Claude Desktop, STDIO — AUTH-001 + AUTH-002
```

---

## Outcome

| Phase | Effort | Coverage |
|-------|--------|----------|
| Phase 1 | 2 main QAs + 1 additional QA (~2h) | Python 3.10–3.13 (all 4 via E2E), macOS + Windows, all transports, both clients, Anon+Auth |
| Phase 2 | CI setup | +Linux, Python 3.10+3.13 on Linux |

**Minimum actions, maximum coverage**.

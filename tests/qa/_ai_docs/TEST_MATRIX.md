# Test Matrix

## Scope Assumptions

| Assumption | Decision |
|------------|----------|
| Installation source | Conda channels, latest release (see [Q1](./OPEN_QUESTIONS.md#q1-installation-source)) |
| Platform coverage | macOS + Windows for manual; Linux via CI (see [Q2](./OPEN_QUESTIONS.md#q2-cliapiconfig-platform-coverage)) |
| Auth scope | Anonymous + Authenticated basic (see [Q3](./OPEN_QUESTIONS.md#q3-authentication--related-features)) |
| Python versions | Boundaries: 3.10 + 3.13 (see [Q4](./OPEN_QUESTIONS.md#q4-python-version-coverage)) |

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

> **Constraint**: E2E testing is macOS only — Claude Desktop and Cursor are not available on Windows or Linux.

---

## Phase 1: Manual Testing (2 QA Engineers)

### E2E Tests (macOS only)

| QA | Client | Python | Transport | Document |
|----|--------|--------|-----------|----------|
| QA 1 | Claude Desktop | 3.10 | STDIO | TESTS_E2E.md |
| QA 2 | Cursor | 3.13 | HTTP | TESTS_E2E.md |

> Each E2E test document includes both `AUTH-001` (anonymous) and `AUTH-002` (authenticated) test cases.

**Coverage**: 2 Python boundary versions + 2 transports + 2 clients

**Optional (if 3rd QA or time)**:
| QA | Client | Python | Transport |
|----|--------|--------|-----------|
| QA 3 | Cursor | 3.13 | STDIO |

### CLI, Config, API-Tools Tests

Split across platforms for OS coverage:

| QA | Platform | Python | Tests |
|----|----------|--------|-------|
| QA 1 | macOS | 3.10 | TESTS_CLI.md, TESTS_CONFIG.md |
| QA 2 | Win365 | 3.13 | TESTS_CLI.md, TESTS_CONFIG.md, TESTS_API_TOOLS.md |

> `TESTS_CONFIG.md` includes `ENV-002` (telemetry control), which requires an authenticated session.

**Coverage**: 2 OS + 2 Python boundary versions + all test types

---

## Phase 1 Summary

| What | Who | Where | Client | Python | Transport |
|------|-----|-------|--------|--------|-----------|
| E2E STDIO | QA 1 | macOS | Claude Desktop | 3.10 | STDIO |
| E2E HTTP | QA 2 | macOS | Cursor | 3.13 | HTTP |
| CLI + Config | QA 1 | macOS | - | 3.10 | - |
| CLI + Config + API Tools | QA 2 | Win365 | - | 3.13 | - |

**Total coverage from Phase 1**:
- ✅ Python 3.10, 3.13 (boundaries)
- ✅ STDIO (Claude Desktop), HTTP (Cursor) transport
- ✅ macOS, Windows
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

### Minimum (2 QAs, Phase 1 only)

| Coverage | How |
|----------|-----|
| Python 3.10 | QA 1 on macOS |
| Python 3.13 | QA 2 on macOS + Win365 |
| STDIO | QA 1 E2E (Claude Desktop) |
| HTTP | QA 2 E2E (Cursor) |
| macOS | QA 1 + QA 2 E2E |
| Windows | QA 2 on Win365 |
| Auth (anon + login flow) | QA 1 via AUTH-001/002 in E2E |

### Extended (Phase 2)

| Coverage | How |
|----------|-----|
| Linux OS | GitHub runners |
| Python 3.10 + 3.13 on Linux | GitHub runners |

### Skip

| What | Why |
|------|-----|
| Python 3.11 | Between boundaries, covered by 3.10 + 3.13 |
| Python 3.12 | Between boundaries, covered by 3.10 + 3.13 |
| macOS runner | Already tested manually |
| Private channels / telemetry backend | Out of scope (Q3 Option C) |

---

## Test Assignment

### QA 1 (macOS, Python 3.10)

```
1. Install Python 3.10 from conda channels (latest release)
2. Run TESTS_E2E.md (STDIO transport) — includes AUTH-001 + AUTH-002
3. Run TESTS_CLI.md
4. Run TESTS_CONFIG.md — includes ENV-002 (telemetry, requires login)
```

### QA 2 (macOS + Win365, Python 3.13)

```
macOS:
1. Install Python 3.13 from conda channels (latest release)
2. Run TESTS_E2E.md (HTTP transport) — includes AUTH-001 + AUTH-002

Win365:
3. Install Python 3.13 from conda channels (latest release)
4. Run TESTS_CLI.md
5. Run TESTS_CONFIG.md — includes ENV-002 (telemetry, requires login)
6. Run TESTS_API_TOOLS.md
```

### Optional QA 3 (macOS, Python 3.13)

```
1. Install Python 3.13 from conda channels (latest release)
2. Run TESTS_E2E.md (STDIO transport) — includes AUTH-001 + AUTH-002
```

---

## Outcome

| Phase | Effort | Coverage |
|-------|--------|----------|
| Phase 1 | 2 QAs, ~1 day | Python 3.10+3.13 (boundaries), macOS+Windows, all transports, Anon+Auth |
| Phase 2 | CI setup | +Linux, Python 3.10+3.13 on Linux |

**Minimum actions, maximum coverage**.

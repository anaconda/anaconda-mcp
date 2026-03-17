# Test Progress — RC2, Iteration 1

> ← [Testing Overview](./TEST_PROGRESS.md) · Matrix: [TEST_MATRIX_rc2.md](../_planning/TEST_MATRIX_rc2.md) · All bugs: [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119)

**Versions**: `anaconda-mcp=1.0.0.rc.2` · `environments-mcp-server=1.0.0.rc.2` · `anaconda-connector` (transitive, resolved at install time)

**Status**: 🔶 In progress

---

## E2E Progress

| QA | OS | Client | Python | Transport | Status | Result | Notes |
|----|----|--------|--------|-----------|--------|--------|-------|
| QA 2 | macOS | Claude Desktop | 3.13 | STDIO | 🔶 In progress | 5 passed / 3 failed / 0 unexecuted | DESK-1401; DESK-1402; DESK-1403 |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | ⬜ Not started | — | |
| QA 1 | Windows | Claude Desktop | 3.10 | STDIO | ⬜ Not started | — | |
| QA 2 | Windows | Claude Desktop | 3.13 | STDIO | ⬜ Not started | — | |

---

## Regression Tests Progress

| Test | QA | Config | Status | Result |
|------|----|--------|--------|--------|
| AUTH-001a | QA 1 | macOS, Claude Desktop, 3.13 | ✅ Done | Passed — anonymous user correctly gets 403 on `repo.anaconda.cloud` |

---

## Fixes Verified This Iteration

| ID | Title | Verification |
|----|-------|-------------|
| [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342) | Environment operations fail by name — wrong prefix resolved | ✅ Confirmed fixed (covered by REGRESS-002 / CORE-001) |
| [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) | Private channel requests routed to wrong URL | ✅ URL routing confirmed correct; superseded by DESK-1401 |
| [DESK-1405](https://anaconda.atlassian.net/browse/DESK-1405) | RC2 installation fails with Python 3.10 / 3.11 / 3.12 | ✅ Confirmed fixed 2026-03-16 |

---

## Bugs Found This Iteration

| ID | Title | Severity | Platform | Date |
|----|-------|----------|----------|------|
| [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) | `conda_create_environment` returns 403 despite valid authentication | Major | macOS | 2026-03-13 |
| [DESK-1402](https://anaconda.atlassian.net/browse/DESK-1402) | Tool "not loaded yet" on first call to `conda_install_packages` | Medium | macOS | 2026-03-13 |
| [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) | `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS=false` parsed as truthy | Low | macOS | 2026-03-13 |
| [DESK-1405](https://anaconda.atlassian.net/browse/DESK-1405) | RC2 installation fails with Python 3.10 / 3.11 / 3.12 | High | macOS | 2026-03-16 |
| [DESK-1408](https://anaconda.atlassian.net/browse/DESK-1408) | Claude Desktop 1.1.6679 — MCP server launch/kill loop, `tools/call` never dispatched | High | macOS | 2026-03-16 |

> Current status of each bug is tracked in Jira under [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119).

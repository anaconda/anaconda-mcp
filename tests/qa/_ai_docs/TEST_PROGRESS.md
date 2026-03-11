# Test Progress

## Summary

- **Last updated**: 2026-03-10
- **Bugs filed**: 10 (4 major / 1 moderate / 5 minor)

| Phase | What | Status |
|-------|------|--------|
| Phase 1 | Manual testing — E2E| 🔶 In progress |
| Phase 2 | Test automation — CLI, Config, API-Tools| 🔶 In progress (tests added for DESK-1355; used to validate proposed fix) |

---
## Bugs
- [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341)
- [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342)
- [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344)
- [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355)
- [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356)
- [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358)
- [DESK-1359](https://anaconda.atlassian.net/browse/DESK-1359)
- [DESK-1363](https://anaconda.atlassian.net/browse/DESK-1363)
- [DESK-1364](https://anaconda.atlassian.net/browse/DESK-1364)
- [DESK-1366](https://anaconda.atlassian.net/browse/DESK-1366)
---

## Phase 1: E2E Progress

See [TEST_MATRIX.md](./TEST_MATRIX.md) for full assignment rationale.

| QA | OS | Client | Python | Transport | Suite | Status | Result | Notes |
|----|----|--------|--------|-----------|-------|--------|--------|-------|
| QA 2 | macOS | Cursor | 3.13 | HTTP | TESTS_E2E.md | ✅ Done | 3 passed / 3 failed / 1 blocked | DESK-1358; DESK-1342; DESK-1355; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | TESTS_E2E.md | ✅ Done  | 3 passed / 4 failed | DESK-1358; DESK-1342; DESK-1341  |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | TESTS_E2E.md | ✅ Done | 4 passed / 2 failed | DESK-1342; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.12 | STDIO | TESTS_E2E.md | ✅ Done | 4 passed / 2 failed | DESK-1342; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.13 | STDIO | TESTS_E2E.md | ✅ Done | 3 passed / 3 failed | DESK-1358; DESK-1342 |
| QA 2 | macOS | Cursor | 3.12 | STDIO | TESTS_E2E.md | ✅ Done | 2 passed / 3 failed / 1 blocked | DESK-1538; DESK-1539; DESK-1355; DESK-1341|
| QA 2 | macOS | Claude Code | 3.10 | HTTP | TESTS_E2E.md | ✅ Done | 3 passed / 3 failed / 1 blocked | DESK-1358; DESK-1342; DESK-1355; DESK-1341 |
| QA 1 | Windows | Claude Desktop | 3.13 | STDIO | TESTS_E2E.md | 🔶 Partial | 0 passed / 1 failed / 5 unexecuted | DESK-1344; DESK-1363; DESK-1364; DESK-1365 |
| QA ? | Windows | Claude Desktop | 3.10 | STDIO | TESTS_E2E.md | ⬜ Not started  | 0 passed / 0 failed / 6 unexecuted | |


---

## Regression Tests Progress

| Test | QA | Config | Status | Result |
|------|----|--------|--------|--------|
| REGRESS-002 (KI-003) | QA 2 | Cursor, HTTP, 3.13 | ✅ Done | KI-003 confirmed — DESK-1342 filed |
| REGRESS-002 (KI-003) | QA 1 | Claude Desktop, STDIO, 3.10 | 🔶 Partial | Run via GUARD-001; full REGRESS-002 pending |
| REGRESS-002 (KI-003) | QA 2 | Claude Code, HTTP, 3.10 | ✅ Done | KI-003 confirmed — DESK-1342 filed |
| AUTH-001a | all configs | — | ⛔ Blocked | [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) — config-independent, run in any suite once unblocked |

---

## Bugs Filed This Cycle

| ID | Title | Severity | KI | Found in |
|----|-------|----------|----|----------|
| [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342) | Environment Operations Fail by Name — Wrong Prefix Resolved | Minor | [KI-003](./KNOWN_ISSUES.md#ki-003-environment-operations-fail-by-name--wrong-prefix-resolved) | QA 2 · macOS · Cursor · 3.13 · HTTP |
| [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341) | Incorrect behavior for conda_install_packages when package does not exist | Minor | [KI-010](./KNOWN_ISSUES.md#ki-010-false-environment-not-found-when-installing-nonexistent-package) | QA 1 · macOS · Claude Desktop · 3.10 · STDIO |
| [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344) | `anaconda-mcp` command not recognized on Windows despite correct installation | Major | [PI-001](./KNOWN_ISSUES.md#pi-001-anaconda-mcp-cli-not-executable-on-windows--missing-exe-wrapper) | QA 3 · Windows · Claude Desktop · 3.13 · STDIO |
| [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355) | mcp-compose proxy hangs and corrupts session on tool error | Major | [KI-011](./KNOWN_ISSUES.md#ki-011-mcp-compose-proxy-hangs-and-corrupts-session-on-tool-error) | QA 2 · macOS · Cursor · 3.13 · HTTP; QA 2 · macOS · Claude Code · 3.10 · HTTP — **donew** |
| [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356) | HTTP setup wizard suggests wrong server command — starts STDIO mode instead of HTTP | Minor | [KI-008](./KNOWN_ISSUES.md#ki-008-http-setup-suggests-wrong-server-command) | Manual testing |
| [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) | Private channel requests routed to conda.anaconda.org instead of repo.anaconda.cloud — credentials never reached | Major | [KI-005](./KNOWN_ISSUES.md#ki-005-channel-credentials-not-picked-up) | Manual testing |
| [DESK-1359](https://anaconda.atlassian.net/browse/DESK-1359) | MCP server initialization hangs when port 4041 is occupied by a non-responsive process | Medium | [KI-012](./KNOWN_ISSUES.md#ki-012-mcp-server-initialization-hangs-when-port-4041-is-occupied-by-a-non-responsive-process) | Manual testing · macOS · Cursor · 3.12 · STDIO |
| [DESK-1363](https://anaconda.atlassian.net/browse/DESK-1363) | [Windows] claude-desktop setup-config writes config to wrong location and doesn't restart Claude Desktop | Minor | — | QA 1 · Windows · Claude Desktop · 3.13 · STDIO |
| [DESK-1364](https://anaconda.atlassian.net/browse/DESK-1364) | Generic error message for: conda_create_environment | Minor | — | QA 1 · Windows · Claude Desktop · 3.13 · STDIO |
| [DESK-1366](https://anaconda.atlassian.net/browse/DESK-1366) | `logger.exception()` causes server hang after ~15 calls | Major | [KI-015](./KNOWN_ISSUES.md#ki-015-loggerexception-causes-server-hang-after-15-calls) | QA 2 · macOS · anaconda-mcp-dev · 3.13 · HTTP/STDIO |

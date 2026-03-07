# Test Progress

## Summary

- **Last updated**: 2026-03-06
- **Bugs filed**: 6 (3 - minor, 1 - medium, 2 - high)

| Phase | What | Status |
|-------|------|--------|
| Phase 1 | Manual testing — E2E| 🔶 In progress |
| Phase 2 | Test automation — CLI, Config, API-Tools| 🔶 Started (API-Tools automation begun to cases from found bugs) |

---
## Bugs
- [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341)
- [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342)
- [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344)
- [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355)
- [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356)
- [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358)
---

## Phase 1: E2E Progress

See [TEST_MATRIX.md](./TEST_MATRIX.md) for full assignment rationale.

| QA | OS | Client | Python | Transport | Suite | Status | Result | Notes |
|----|----|--------|--------|-----------|-------|--------|--------|-------|
| QA 2 | macOS | Cursor | 3.13 | HTTP | TESTS_E2E.md | ✅ Done | 4 passed / 2 failed | DESK-1342; DESK-1355 triggered |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | TESTS_E2E.md | 🔶 Partial | 1 failed / 5 not run | GUARD-001 run; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | TESTS_E2E.md | ⬜ Not started | — | |
| QA 1 | macOS | Claude Desktop | 3.12 | STDIO | TESTS_E2E.md | ⬜ Not started | — | |
| QA 1 | macOS | Claude Desktop | 3.13 | STDIO | TESTS_E2E.md | ⬜ Not started | — | |
| QA 1 | macOS | Cursor | 3.12 | STDIO | TESTS_E2E.md | ⬜ Not started | — | |
| QA 3 | Windows | Claude Desktop | 3.13 | STDIO | TESTS_E2E.md | 🔶 In progress | — | DESK-1344; PI-001 hit during setup |

### Optional (if time allows)

| QA | OS | Client | Python | Transport | Suite | Status | Result | Notes |
|----|----|--------|--------|-----------|-------|--------|--------|-------|
| QA 2 | macOS | Claude Code | 3.10 | HTTP | TESTS_E2E.md | ✅ Done | 4 passed / 2 failed | DESK-1342; KI-011 equivalent observed |
| QA 3 | Windows | Claude Desktop | 3.10 | STDIO | TESTS_E2E.md | ⬜ Not started | — | |

---

## Regression Tests Progress

| Test | QA | Config | Status | Result |
|------|----|--------|--------|--------|
| REGRESS-002 (KI-003) | QA 2 | Cursor, HTTP, 3.13 | ✅ Done | KI-003 confirmed — DESK-1342 filed |
| REGRESS-002 (KI-003) | QA 1 | Claude Desktop, STDIO, 3.10 | 🔶 Partial | Run via GUARD-001; full REGRESS-002 pending |
| REGRESS-002 (KI-003) | QA 2 | Claude Code, HTTP, 3.10 | ⬜ Not started | — |
| AUTH-001a | all configs | — | ⛔ Blocked | [KI-005](./KNOWN_ISSUES.md#ki-005-channel-credentials-not-picked-up) / [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) — config-independent, run in any suite once unblocked |

---

## Phase 1: Low-Level Tests Progress

| QA | Platform | Python | Suite | Status |
|----|----------|--------|-------|--------|
| QA 2 | macOS | 3.10 | TESTS_CLI.md | ⬜ Not started |
| QA 2 | macOS | 3.10 | TESTS_CONFIG.md | ⬜ Not started |
| QA 2 | Win365 | 3.13 | TESTS_CLI.md | ⬜ Not started |
| QA 2 | Win365 | 3.13 | TESTS_CONFIG.md | ⬜ Not started |
| QA 2 | Win365 | 3.13 | TESTS_API_TOOLS.md | ⬜ Not started |

---

## Bugs Filed This Cycle

| ID | Title | Severity | KI | Found in |
|----|-------|----------|----|----------|
| [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342) | Environment Operations Fail by Name — Wrong Prefix Resolved | Minor | [KI-003](./KNOWN_ISSUES.md#ki-003-environment-operations-fail-by-name--wrong-prefix-resolved) | QA 2 · macOS · Cursor · 3.13 · HTTP |
| [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341) | Incorrect behavior for conda_install_packages when package does not exist | Minor | [KI-010](./KNOWN_ISSUES.md#ki-010-false-environment-not-found-when-installing-nonexistent-package) | QA 1 · macOS · Claude Desktop · 3.10 · STDIO |
| [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344) | `anaconda-mcp` command not recognized on Windows despite correct installation | High | [PI-001](./KNOWN_ISSUES.md#pi-001-anaconda-mcp-cli-not-executable-on-windows--missing-exe-wrapper) | QA 3 · Windows · Claude Desktop · 3.13 · STDIO |
| [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355) | mcp-compose proxy hangs and corrupts session on tool error | High | [KI-011](./KNOWN_ISSUES.md#ki-011-mcp-compose-proxy-hangs-and-corrupts-session-on-tool-error) | QA 2 · macOS · Cursor · 3.13 · HTTP; QA 2 · macOS · Claude Code · 3.10 · HTTP |
| [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356) | HTTP setup wizard suggests wrong server command — starts STDIO mode instead of HTTP | High | [KI-008](./KNOWN_ISSUES.md#ki-008-http-setup-suggests-wrong-server-command) | Manual testing |
| [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) | Private channel requests routed to conda.anaconda.org instead of repo.anaconda.cloud — credentials never reached | Medium | [KI-005](./KNOWN_ISSUES.md#ki-005-channel-credentials-not-picked-up) | Manual testing |

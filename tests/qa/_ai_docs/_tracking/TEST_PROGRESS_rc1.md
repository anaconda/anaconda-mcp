# Test Progress — RC1 (Phase 1)

> ← [Testing Overview](./TEST_PROGRESS.md) · Matrix: [TEST_MATRIX.md](../_planning/TEST_MATRIX.md) · All bugs: [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119)

**Versions**: `anaconda-mcp=1.0.0.rc.1` · `environments-mcp-server=1.0.0.rc.1` · `anaconda-connector` (transitive)

**Status**: ✅ Complete

---

## E2E Progress

| QA | OS | Client | Python | Transport | Status | Result | Notes |
|----|----|--------|--------|-----------|--------|--------|-------|
| QA 2 | macOS | Cursor | 3.13 | HTTP | ✅ Done | 3 passed / 3 failed / 1 blocked | DESK-1358; DESK-1342; DESK-1355; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | ✅ Done | 3 passed / 4 failed | DESK-1358; DESK-1342; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | ✅ Done | 4 passed / 2 failed | DESK-1342; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.12 | STDIO | ✅ Done | 4 passed / 2 failed | DESK-1342; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.13 | STDIO | ✅ Done | 3 passed / 3 failed | DESK-1358; DESK-1342 |
| QA 2 | macOS | Cursor | 3.12 | STDIO | ✅ Done | 2 passed / 3 failed / 1 blocked | DESK-1538; DESK-1539; DESK-1355; DESK-1341 |
| QA 2 | macOS | Claude Code | 3.10 | HTTP | ✅ Done | 3 passed / 3 failed / 1 blocked | DESK-1358; DESK-1342; DESK-1355; DESK-1341 |
| QA 1 | Windows | Claude Desktop | 3.13 | STDIO | ✅ Done | 0 passed / 6 failed | DESK-1390; DESK-1364; DESK-1389; DESK-1365; DESK-1391 |
| QA 2 | Windows | Claude Desktop | 3.10 | STDIO | 🔶 Partial | 0 passed / 1 failed / 5 unexecuted | DESK-1384; DESK-1385; DESK-1386; DESK-1363 |

---

## Regression Tests Progress

| Test | QA | Config | Status | Result |
|------|----|--------|--------|--------|
| REGRESS-002 (KI-003) | QA 2 | Cursor, HTTP, 3.13 | ✅ Done | KI-003 confirmed — DESK-1342 filed |
| REGRESS-002 (KI-003) | QA 1 | Claude Desktop, STDIO, 3.10 | 🔶 Partial | Run via GUARD-001; full REGRESS-002 pending |
| REGRESS-002 (KI-003) | QA 2 | Claude Code, HTTP, 3.10 | ✅ Done | KI-003 confirmed — DESK-1342 filed |

---

## Issues Found in RC1

### Bugs

| ID | Title | Severity | Platform |
|----|-------|----------|----------|
| [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341) | Incorrect error message when installing nonexistent package | Minor | macOS |
| [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342) | Environment operations fail by name — wrong prefix resolved | High | macOS |
| [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344) | `anaconda-mcp` command not recognized on Windows | Major | Windows |
| [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355) | Chat session freezes after tool error (mcp-compose proxy hang) | High | macOS |
| [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356) | HTTP setup wizard suggests wrong server command | Minor | macOS |
| [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) | Private channel requests routed to wrong URL | Medium | macOS |
| [DESK-1359](https://anaconda.atlassian.net/browse/DESK-1359) | Stale process port conflicts produce no actionable diagnostic | Medium | macOS |
| [DESK-1363](https://anaconda.atlassian.net/browse/DESK-1363) | `claude-desktop setup-config` writes config to wrong location (Windows) | Minor | Windows |
| [DESK-1364](https://anaconda.atlassian.net/browse/DESK-1364) | Generic error message for `conda_create_environment` | Minor | macOS |
| [DESK-1365](https://anaconda.atlassian.net/browse/DESK-1365) | Invalid argument error on install/remove/remove-env (Windows) | Major | Windows |
| [DESK-1366](https://anaconda.atlassian.net/browse/DESK-1366) | `logger.exception()` causes server hang after ~15 tool calls | High | macOS |
| [DESK-1384](https://anaconda.atlassian.net/browse/DESK-1384) | `create_environment` fails with Pydantic `frozen_instance` error | High | Windows |
| [DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385) | First `conda_list_environments` always hangs on Windows | High | Windows |
| [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386) | Retry also fails when logged in (Windows) | High | Windows |
| [DESK-1389](https://anaconda.atlassian.net/browse/DESK-1389) | "Not defined" error for `conda_create_environment` (Windows) | Minor | Windows |
| [DESK-1390](https://anaconda.atlassian.net/browse/DESK-1390) | Existing environment not found in `conda_remove_environment` (Windows) | Major | Windows |
| [DESK-1391](https://anaconda.atlassian.net/browse/DESK-1391) | Unable to install package from `repo.anaconda.cloud` (Windows) | Major | Windows |

### Feature Requests

| ID | Title | Priority | Status |
|----|-------|----------|--------|
| [DESK-1392](https://anaconda.atlassian.net/browse/DESK-1392) | Expose `channels` as explicit schema parameter in `conda_install_packages` and `conda_create_environment` | Low | New |
| [DESK-1393](https://anaconda.atlassian.net/browse/DESK-1393) | Auth Toolset — new `auth_status` + `auth_check_channel` tools for session and channel access visibility | Low | New |
| [DESK-1394](https://anaconda.atlassian.net/browse/DESK-1394) | 403 Auth Interceptor — automatic diagnostic chain on channel access failure | Medium | New |

> Current status of each issue is tracked in Jira under [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119).

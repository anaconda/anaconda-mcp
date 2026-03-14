# Test Progress

## Summary

- **Last updated**: 2026-03-13
- **Bugs filed**: 14 active bugs (3 today) · 6 fixed/closed · 3 feature requests

| Phase | What | Status |
|-------|------|--------|
| Phase 1 | Manual testing — E2E (RC1) | ✅ Done |
| Phase 2 | Manual testing — E2E (RC2) | 🔶 In progress |
| Phase 3 | Test automation — CLI, Config, API-Tools | 🔶 In progress |

---

## 🔐 Auth Diagnostics — Feature Requests (High Visibility)

During troubleshooting of [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) (MCP subprocess does not inherit `anaconda-auth` credentials), three related improvements were identified and filed. Per Product Owner guidance, these are proposed for **reclassification from Bug → Task**, to be prioritized and scheduled independently.

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| [DESK-1392](https://anaconda.atlassian.net/browse/DESK-1392) | Expose `channels` as explicit schema parameter in `conda_install_packages` and `conda_create_environment` | New | Enables agent to pass channel URLs; prerequisite for testing private channel flows via MCP |
| [DESK-1393](https://anaconda.atlassian.net/browse/DESK-1393) | Auth Toolset — new `auth_status` + `auth_check_channel` tools for session and channel access visibility | REVIEW | **Proactive** auth check before install; proposed solution in [PR #26](https://github.com/anaconda/anaconda-mcp/pull/26); helps distinguish authenticated vs unauthenticated flows |
| [DESK-1394](https://anaconda.atlassian.net/browse/DESK-1394) | 403 Auth Interceptor — automatic diagnostic chain on channel access failure | New | **Reactive** complement to DESK-1393; intercepts raw 403 errors and returns structured diagnosis (not logged in / token config missing / subscription issue) |

**DESK-1393 priority note**: The `auth_status` / `auth_check_channel` toolset is the most impactful of the three for near-term testability. It makes authenticated vs anonymous user flows clearly distinguishable at the MCP level, which is otherwise impossible to verify without terminal-side inspection. Even a simplified version (as in PR #26) would significantly unblock AUTH-001a and AUTH-002 test suites.

---

## Windows Testing — Scope Decision Required

Windows E2E results show significantly higher instability than macOS. The table below summarizes the blockers:

| ID | Summary | Impact |
|----|---------|--------|
| [DESK-1363](https://anaconda.atlassian.net/browse/DESK-1363) | `claude-desktop setup-config` writes config to wrong location, doesn't restart Claude Desktop | Setup broken — manual workaround required before any test can run |
| [DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385) | First `conda_list_environments` call always hangs on Windows (cold-start timeout) | Every Windows session starts with a failed first call (~4 min wait) |
| [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386) | After first-call hang, retry also fails when user is logged in | Logged-in users cannot use the product after startup until restarted |
| [DESK-1365](https://anaconda.atlassian.net/browse/DESK-1365) | Invalid argument error on `conda_install_packages`, `conda_remove_packages`, `conda_remove_environment` (Windows) | Core operations fail |
| [DESK-1389](https://anaconda.atlassian.net/browse/DESK-1389) | "Not defined" error message for `conda_create_environment` (Windows) | Unhelpful error surfaced to agent |
| [DESK-1390](https://anaconda.atlassian.net/browse/DESK-1390) | Existing environment not found using `conda_remove_environment` (Windows) | Remove tool broken |
| [DESK-1391](https://anaconda.atlassian.net/browse/DESK-1391) | Unable to install package from `repo.anaconda.cloud` (Windows) | Install tool broken |

**Recommendation**: Windows user flows are not stable enough for this release. DESK-1385 and DESK-1386 alone make the product unusable for any Windows user on first launch. If Windows is **not in scope** for this release, document these as known limitations in release notes. If Windows **is in scope**, DESK-1385 and DESK-1386 must be treated as release blockers.

---

## Bugs

### Fixed (RC2)

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342) | Environment operations fail by name — wrong prefix resolved | Done | Fixed in RC2 |
| [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355) | Chat session freezes after tool error with no recovery (mcp-compose proxy hang) | Done | Fixed in mcp-compose 0.1.11; [PR #24](https://github.com/anaconda/anaconda-mcp/pull/24) |
| [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) | Private channel requests routed to `conda.anaconda.org` instead of `repo.anaconda.cloud` | Done | Replaced by [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) |
| [DESK-1366](https://anaconda.atlassian.net/browse/DESK-1366) | `logger.exception()` causes MCP server hang after ~15 tool calls | Done | Fixed |
| [DESK-1384](https://anaconda.atlassian.net/browse/DESK-1384) | `create_environment` fails with Pydantic `frozen_instance` error when `environment_root_path` provided | Done | Fixed |
| [DESK-1364](https://anaconda.atlassian.net/browse/DESK-1364) | Generic error message for `conda_create_environment` | Closed: No Action | — |

### Today's Bugs (2026-03-13)

| ID | Title | Status | Platform | Severity |
|----|-------|--------|----------|----------|
| [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) | `conda_create_environment` returns 403 Forbidden despite valid authentication | New | macOS | Major |
| [DESK-1402](https://anaconda.atlassian.net/browse/DESK-1402) | Tool "not loaded yet" error on first call to `conda_install_packages` | New | macOS | Medium |
| [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) | `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS=false` parsed as truthy | New | macOS | Low |

### Other Open

| ID | Title | Status | Platform | Severity |
|----|-------|--------|----------|----------|
| [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341) | Incorrect error message for `conda_install_packages` when package does not exist | New | macOS | Minor |
| [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344) | `anaconda-mcp` command not recognized on Windows despite correct installation | New | Windows | Major |
| [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356) | HTTP setup wizard suggests wrong server command — starts STDIO mode instead of HTTP | New | macOS | Minor |
| [DESK-1359](https://anaconda.atlassian.net/browse/DESK-1359) | Stale process port conflicts on MCP server restart produce no actionable diagnostic | New | macOS | Medium |
| [DESK-1363](https://anaconda.atlassian.net/browse/DESK-1363) | [Windows] `claude-desktop setup-config` writes config to wrong location and doesn't restart Claude Desktop | New | Windows | Minor |
| [DESK-1365](https://anaconda.atlassian.net/browse/DESK-1365) | [Windows] Invalid argument error on `conda_install_packages` / `conda_remove_packages` / `conda_remove_environment` | New | Windows | Major |
| [DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385) | [Windows] First `conda_list_environments` call always hangs — cold-start timeout | New | Windows | High |
| [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386) | [Windows] After first-call hang, retry also fails when user is logged in | New | Windows | High |
| [DESK-1389](https://anaconda.atlassian.net/browse/DESK-1389) | [Windows] "Not defined" error message for `conda_create_environment` | New | Windows | Minor |
| [DESK-1390](https://anaconda.atlassian.net/browse/DESK-1390) | [Windows] Existing environment not found using `conda_remove_environment` | New | Windows | Major |
| [DESK-1391](https://anaconda.atlassian.net/browse/DESK-1391) | [Windows] Unable to install package from `repo.anaconda.cloud` | New | Windows | Major |

---

## Phase 2: E2E RC2 Progress

See [TEST_MATRIX_rc2.md](./TEST_MATRIX_rc2.md) for assignment rationale. Test definitions: [tests/](./tests/)

| QA | OS | Client | Python | Transport | Status | Result | Notes |
|----|----|--------|--------|-----------|--------|--------|-------|
| QA 2 | macOS | Claude Desktop | 3.13 | STDIO | 🔶 In progress | 5 passed / 3 failed / 0 unexecuted | DESK-1401; DESK-1402; DESK-1403 |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | ⬜ Not started | 0 passed / 0 failed / 2 unexecuted| |
| QA 1 | Windows | Claude Desktop | 3.10 | STDIO | ⬜ Not started | 0 passed / 0 failed / 5 unexecuted |  |
| QA 2 | Windows | Claude Desktop | 3.13 | STDIO | ⬜ Not started | 0 passed / 0 failed / 3 unexecuted| |

---

## Phase 1: E2E Progress (RC1)

See [TEST_MATRIX.md](./TEST_MATRIX.md) for full assignment rationale.

| QA | OS | Client | Python | Transport | Status | Result | Notes |
|----|----|--------|--------|-----------|--------|--------|-------|
| QA 2 | macOS | Cursor | 3.13 | HTTP | ✅ Done | 3 passed / 3 failed / 1 blocked | DESK-1358; DESK-1342; DESK-1355; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | ✅ Done | 3 passed / 4 failed | DESK-1358; DESK-1342; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | ✅ Done | 4 passed / 2 failed | DESK-1342; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.12 | STDIO | ✅ Done | 4 passed / 2 failed | DESK-1342; DESK-1341 |
| QA 1 | macOS | Claude Desktop | 3.13 | STDIO | ✅ Done | 3 passed / 3 failed | DESK-1358; DESK-1342 |
| QA 2 | macOS | Cursor | 3.12 | STDIO | ✅ Done | 2 passed / 3 failed / 1 blocked | DESK-1538; DESK-1539; DESK-1355; DESK-1341 |
| QA 2 | macOS | Claude Code | 3.10 | HTTP | ✅ Done | 3 passed / 3 failed / 1 blocked | DESK-1358; DESK-1342; DESK-1355; DESK-1341 |
| QA 1 | Windows | Claude Desktop | 3.13 | STDIO | ✅ Done | 0 passed / 6 failed / 0 unexecuted | DESK-1390; DESK-1364; DESK-1389; DESK-1365; DESK-1391 |
| QA 2 | Windows | Claude Desktop | 3.10 | STDIO | 🔶 Partial | 0 passed / 1 failed / 5 unexecuted | DESK-1384; DESK-1385; DESK-1386; DESK-1363 |

---

## Regression Tests Progress

| Test | QA | Config | Status | Result |
|------|----|--------|--------|--------|
| REGRESS-002 (KI-003) | QA 2 | Cursor, HTTP, 3.13 | ✅ Done | KI-003 confirmed — DESK-1342 filed |
| REGRESS-002 (KI-003) | QA 1 | Claude Desktop, STDIO, 3.10 | 🔶 Partial | Run via GUARD-001; full REGRESS-002 pending |
| REGRESS-002 (KI-003) | QA 2 | Claude Code, HTTP, 3.10 | ✅ Done | KI-003 confirmed — DESK-1342 filed |
| AUTH-001a | QA 1 | macOS, Claude Desktop, 3.13 (RC2) | ✅ Done | Passed — anonymous user correctly gets 403 auth error on `repo.anaconda.cloud` |

---

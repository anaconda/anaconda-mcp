# Testing Overview

Central entry point for all test planning, execution progress, and cross-cutting concerns.

---

## Testing Stages

| Stage | Versions | Matrix | Progress | Status |
|-------|----------|--------|----------|--------|
| **RC1 — Phase 1** | `anaconda-mcp=1.0.0.rc.1` · `environments-mcp-server=1.0.0.rc.1` · `anaconda-connector` (transitive) | [TEST_MATRIX.md](../_planning/TEST_MATRIX.md) | [TEST_PROGRESS_rc1.md](./TEST_PROGRESS_rc1.md) | ✅ Complete |
| **RC2 — Iteration 1** | `anaconda-mcp=1.0.0.rc.2` · `environments-mcp-server=1.0.0.rc.2` · `anaconda-connector` (transitive) | [TEST_MATRIX_rc2.md](../_planning/TEST_MATRIX_rc2.md) | [TEST_PROGRESS_rc2_iter1.md](./TEST_PROGRESS_rc2_iter1.md) | 🔶 In progress |
| **RC2 — Iteration 2** | `anaconda-mcp=1.0.0.rc.2` · `environments-mcp-server=1.0.0.rc.2` · `anaconda-connector-*=0.1.11` (pinned) | [TEST_MATRIX_rc2_iter2.md](../_planning/TEST_MATRIX_rc2_iter2.md) | [TEST_PROGRESS_rc2_iter2.md](./TEST_PROGRESS_rc2_iter2.md) | ⬜ Not started |

### Stage Summaries

**RC1 — Phase 1**
Full-breadth exploration: all 4 Python versions, both transports (STDIO + HTTP), multiple clients (Claude Desktop, Cursor, Claude Code), macOS + Windows. Goal: discover bugs and establish baseline. Filed 10+ bugs; confirmed KI-003 (env name resolution), KI-011 (mcp-compose proxy hang), KI-009 (Claude Desktop/HTTP incompatibility).

**RC2 — Iteration 1**
Reduced matrix targeting the primary user scenario (Claude Desktop, STDIO, macOS + Windows). Goal: verify RC2 fixes, test new features (SETUP-001, CHAN-001), expand auth coverage. Auth improvements partially blocked by DESK-1401; Windows execution deferred due to instability.

**RC2 — Iteration 2**
Pinned connector packages (`anaconda-connector-*=0.1.11`). Goal: validate connector auth improvements across all 4 Python versions on macOS; Windows excluded. AUTH-002 is the key signal — expected to pass with the connector update.

---

## Bugs — Active Open

### macOS

| ID | Title | Severity | Affects |
|----|-------|----------|---------|
| [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) | `conda_create_environment` returns 403 despite valid authentication | Major | RC2 Iter1 |
| [DESK-1402](https://anaconda.atlassian.net/browse/DESK-1402) | Tool "not loaded yet" on first call to `conda_install_packages` | Medium | RC2 Iter1 |
| [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) | `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS=false` parsed as truthy | Low | RC2 Iter1 |
| [DESK-1408](https://anaconda.atlassian.net/browse/DESK-1408) | ~~Claude Desktop 1.1.6679 — MCP server launch/kill loop~~ | ~~High~~ | **Closed** (Claude Desktop update fixed it) |
| [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341) | Incorrect error message when installing nonexistent package | Minor | RC1+ |
| [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356) | HTTP setup wizard suggests wrong server command | Minor | RC1+ |
| [DESK-1359](https://anaconda.atlassian.net/browse/DESK-1359) | Stale process port conflicts produce no actionable diagnostic | Medium | RC1+ |

### Windows (deferred — see below)

| ID | Title | Severity |
|----|-------|----------|
| [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344) | `anaconda-mcp` command not recognized | Major |
| [DESK-1363](https://anaconda.atlassian.net/browse/DESK-1363) | `claude-desktop setup-config` writes config to wrong location | Minor |
| [DESK-1365](https://anaconda.atlassian.net/browse/DESK-1365) | Invalid argument error on install/remove/remove-env | Major |
| [DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385) | First `conda_list_environments` always hangs (cold-start timeout) | High |
| [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386) | Retry also fails when logged in (after first-call hang) | High |
| [DESK-1389](https://anaconda.atlassian.net/browse/DESK-1389) | "Not defined" error for `conda_create_environment` | Minor |
| [DESK-1390](https://anaconda.atlassian.net/browse/DESK-1390) | Existing environment not found in `conda_remove_environment` | Major |
| [DESK-1391](https://anaconda.atlassian.net/browse/DESK-1391) | Unable to install package from `repo.anaconda.cloud` | Major |

---

## 🔐 Auth Diagnostics — Feature Requests (High Visibility)

Filed during RC1/RC2 troubleshooting. Per Product Owner guidance, proposed for reclassification from Bug → Task.

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| [DESK-1392](https://anaconda.atlassian.net/browse/DESK-1392) | Expose `channels` as explicit schema parameter in install/create tools | New | Prerequisite for testing private channel flows via MCP |
| [DESK-1393](https://anaconda.atlassian.net/browse/DESK-1393) | Auth Toolset — `auth_status` + `auth_check_channel` tools | REVIEW | [PR #26](https://github.com/anaconda/anaconda-mcp/pull/26); highest impact for near-term testability |
| [DESK-1394](https://anaconda.atlassian.net/browse/DESK-1394) | 403 Auth Interceptor — automatic diagnostic chain on channel access failure | New | Reactive complement to DESK-1393 |

**Note on DESK-1393**: Makes authenticated vs anonymous flows distinguishable at the MCP level without terminal inspection. Even a simplified version significantly unblocks AUTH-001a and AUTH-002.

---

## Windows — Deferred

Windows E2E shows blockers that make the product unusable on first launch (DESK-1385, DESK-1386). Windows is excluded from RC2 Iteration 2. Re-evaluate for RC3 or GA.

| Blocker | Impact |
|---------|--------|
| DESK-1385 — first call always hangs | Every Windows session starts with a ~4 min failure |
| DESK-1386 — retry also fails when logged in | Logged-in users cannot use the product after startup |

If Windows is in scope for release, DESK-1385 and DESK-1386 are release blockers.

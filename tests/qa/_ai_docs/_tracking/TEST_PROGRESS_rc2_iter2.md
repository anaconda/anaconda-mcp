# Test Progress — RC2, Iteration 2 (Connector 0.1.11)

> ← [Testing Overview](./TEST_PROGRESS.md) · Matrix: [TEST_MATRIX_rc2_iter2.md](../_planning/TEST_MATRIX_rc2_iter2.md)
>
> **Tracking**: [DESK-1421](https://anaconda.atlassian.net/browse/DESK-1421) (this sprint) · [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119) (all bugs)

**Versions**: `anaconda-mcp=1.0.0.rc.2` · `environments-mcp-server=1.0.0.rc.2` · `anaconda-connector-core=0.1.11` · `anaconda-connector-conda=0.1.11` · `anaconda-connector-utilities=0.1.11`

**Status**: 🔶 In progress

**Date**: 2026-03-19

---

## Goals

1. **Core flow validation** across all 4 Python versions (CORE-001, CORE-001a)
2. **Bug retesting**: each QA retests their own opened bugs
   - QA 1: retest bugs filed by QA 1
   - QA 2: retest bugs filed by QA 2

---

## E2E Progress

| QA | OS | Client | Python | Transport | Strategy | Status | Result |
|----|----|--------|--------|-----------|----------|--------|--------|
| QA 2 | macOS | Claude Desktop | 3.13 | STDIO | Full suite | ✅ Completed | 8/8 passed |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | Core only | ✅ Completed | 2/2 passed |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | Core only | ⬜ Not started | — |
| QA 2 | macOS | Claude Desktop | 3.12 | STDIO | Core only | ✅ Completed | 2/2 passed |

### QA 2 · macOS · Python 3.13 — Completion Notes

**All 8 tests passed** by using workarounds and shorter flows to avoid known bugs.

| Category | Details |
|----------|---------|
| **Fixed this iteration** | DESK-1401 (403 on private channels) — resolved with connector 0.1.11 |
| **Bugs with workarounds** | DESK-1411 (port 8000 conflict) — quit Claude Desktop before `anaconda login` |
| | ~~DESK-1408~~ — **Closed**: Claude Desktop update fixed the launch/kill loop |
| | DESK-1402 — just first call of toll is with error, and it works well after that, user just have +1 tool call, not a blocker|
| | DESK-1403 (string "false" truthy) — use `""` or remove env var |
| **Bugs avoided** | DESK-1409 (proxy hang after ~17 calls) — used shorter test flows, avoided batch operations, **bug is consistently reproducible in Claude Desktop** |
| **Closed by design** | DESK-1413 (API key auth) — not a bug; interactive login is the only supported flow |

**Key takeaway**: Tests pass when using recommended flows and workarounds. Extended workflows (batch deletions, many sequential installs) may hit DESK-1409.

---

## Tests Per Config Progress

| QA | Config | CORE-001a | CORE-001 |
|----|--------|:---------:|:--------:|
| QA 2 | macOS, 3.13 | ✅ | ✅ |
| QA 1 | macOS, 3.10 | ✅ | ✅ |
| QA 1 | macOS, 3.11 | ⬜ | ⬜ |
| QA 2 | macOS, 3.12 | ✅ | ✅ |

**Legend**: ⬜ Not started · 🔶 In progress · ✅ Pass · ❌ Fail

---

## Bug Retesting Progress

Full retesting details: [DESK-1423](https://anaconda.atlassian.net/browse/DESK-1423)

### ✅ Verified Fixed (11)

| Bug ID | Summary | Reporter | Notes |
|--------|---------|----------|-------|
| [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) | `conda_create_environment` returns 403 | QA 2 | Fixed in connector 0.1.11 |
| [DESK-1384](https://anaconda.atlassian.net/browse/DESK-1384) | Pydantic frozen instance error with `environment_root_path` | QA 2 | Fixed |
| [DESK-1366](https://anaconda.atlassian.net/browse/DESK-1366) | `logger.exception()` causes server hang | QA 2 | Fixed via mcp-compose PR #28 |
| [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) | Private channel routed to conda.anaconda.org | QA 2 | Fixed |
| [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355) | Chat freezes after tool error | QA 2 | Fixed via mcp-compose PR #28 |
| [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342) | Environment operations fail by name — wrong prefix | QA 2 | Fixed |
| [DESK-1359](https://anaconda.atlassian.net/browse/DESK-1359) | Stale process port conflicts — no diagnostic | QA 2 | Retested → DONE |
| [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341) | Incorrect error for non-existent package | QA 2 | Retested → DONE |
| [DESK-1408](https://anaconda.atlassian.net/browse/DESK-1408) | Error adding package to environment | QA 2 | Claude Desktop upgrade fixed |
| [DESK-1405](https://anaconda.atlassian.net/browse/DESK-1405) | RC2 not compatible with Python 3.10/3.11/3.12 | QA 1 | Fixed |
| [DESK-1389](https://anaconda.atlassian.net/browse/DESK-1389) | Undefined error message for `conda_create_environment` | QA 1 | Retested → DONE |
| [DESK-1391](https://anaconda.atlassian.net/browse/DESK-1391) | Unable to install package from repo.anaconda.cloud | QA 1 | Fixed |

### 🔴 Reproducible (7)

| Bug ID | Summary | Reporter | Notes |
|--------|---------|----------|-------|
| [DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409) | Chat freezes after ~17 MCP tool calls | QA 2 | **High severity** — blocks extended workflows |
| [DESK-1411](https://anaconda.atlassian.net/browse/DESK-1411) | Port 8000 conflict with `anaconda login` | QA 2 | Workaround: quit Claude Desktop before login |
| [DESK-1410](https://anaconda.atlassian.net/browse/DESK-1410) | `PYTHONASYNCIODEBUG=1` breaks environment creation | QA 2 | Updated: 3.12 can't start, 3.13 as before |
| [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) | `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS=false` parsed as truthy | QA 2 | Workaround: use `""` or remove env var |
| [DESK-1402](https://anaconda.atlassian.net/browse/DESK-1402) | `conda_install_packages` "Not Loaded Yet" on first call | QA 2 | Race condition on cold start |
| [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356) | `anaconda-mcp serve` suggests STDIO instead of HTTP | QA 2 | Misleading CLI guidance |

### ⏸️ Postponed — Windows Out of Scope (6)

| Bug ID | Summary | Reporter |
|--------|---------|----------|
| [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386) | [Windows] Retry fails after first-call hang | QA 2 |
| [DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385) | [Windows] First tool call always hangs | QA 2 |
| [DESK-1363](https://anaconda.atlassian.net/browse/DESK-1363) | [Windows] `setup-config` writes to wrong location | QA 2 |
| [DESK-1390](https://anaconda.atlassian.net/browse/DESK-1390) | `conda_remove_environment` not found | QA 1 |
| [DESK-1365](https://anaconda.atlassian.net/browse/DESK-1365) | Invalid argument error on multiple conda tools | QA 1 |
| [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344) | [Windows] `anaconda-mcp` command not recognized | QA 1 |

### N/A — Not Bugs (8)

| Bug ID | Summary | Reporter | Reason |
|--------|---------|----------|--------|
| [DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413) | `conda_create_environment` "Token not found" with API key auth | QA 2 | Closed by design |
| [DESK-1364](https://anaconda.atlassian.net/browse/DESK-1364) | Generic error message for `conda_create_environment` | QA 1 | Superseded by DESK-1389 |
| [DESK-1394](https://anaconda.atlassian.net/browse/DESK-1394) | 403 Auth Interceptor | QA 2 | Feature request |
| [DESK-1393](https://anaconda.atlassian.net/browse/DESK-1393) | Auth Toolset | QA 2 | Feature request |
| [DESK-1392](https://anaconda.atlassian.net/browse/DESK-1392) | Expose `channels` parameter | QA 2 | Feature request |
| [DESK-1416](https://anaconda.atlassian.net/browse/DESK-1416) | `conda list channel` shows repo.anaconda.com | QA 1 | No longer reproduced |
| [DESK-1424](https://anaconda.atlassian.net/browse/DESK-1424) | Environment not deleted — prohibited action | QA 1 | No longer reproduced |
| [DESK-1427](https://anaconda.atlassian.net/browse/DESK-1427) | `conda_install_packages` not available | QA 1 | No longer reproduced |

---

## Fixes to Verify This Iteration

| ID | Title | Key test(s) | Verification |
|----|-------|-------------|-------------|
| [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) | `conda_create_environment` returns 403 despite valid auth | AUTH-002 (all 4 configs) | ✅ Fixed (verified with connector 0.1.11) |


---

## Bugs Found This Iteration

| ID | Title | Severity | KI | Platform | Date |
|----|-------|----------|-----|----------|------|
| [DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409) | Claude Desktop chat freezes after ~17 conda_install_packages calls (mcp-compose proxy hang) | High | KI-011 | macOS | 2026-03-17 |
| [DESK-1410](https://anaconda.atlassian.net/browse/DESK-1410) | Claude Desktop fails to create conda environment after user adds PYTHONASYNCIODEBUG=1 to MCP config | Lowest | KI-025 | macOS | 2026-03-17 |
| [DESK-1411](https://anaconda.atlassian.net/browse/DESK-1411) | Cannot run `anaconda login` while Claude Desktop with anaconda-mcp is running (port 8000 conflict) | Lowest | KI-026 | macOS | 2026-03-17 |
| [DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413) | `conda_create_environment` fails with "Token not found" when using API key auth instead of interactive login | Lowest | KI-027 | macOS | 2026-03-17 | **Closed: No Action / By Design** |

> Current status of each bug is tracked in Jira under [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119).

---

## Bug Summary

- **DESK-1401**: ✅ **FIXED** — 403 error on private channels resolved with anaconda-connector 0.1.11
- **DESK-1409**: mcp-compose proxy hang after ~17 tool calls — **blocks extended workflows**
- **DESK-1410**: Thread-safety violation exposed by PYTHONASYNCIODEBUG=1 — **workaround: remove debug flag**
- **DESK-1411**: Port 8000 conflict between mcp-compose and anaconda login — **workaround: quit Claude Desktop before login**
- **DESK-1413**: ✅ **CLOSED: BY DESIGN** — API key auth cannot work for MCP channel access (three independent architectural constraints); interactive login is the only supported flow

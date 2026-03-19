# Test Progress — RC2, Iteration 2 (Connector 0.1.11)

> ← [Testing Overview](./TEST_PROGRESS.md) · Matrix: [TEST_MATRIX_rc2_iter2.md](../_planning/TEST_MATRIX_rc2_iter2.md)
>
> **Tracking**: [DESK-1421](https://anaconda.atlassian.net/browse/DESK-1421) (this sprint) · [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119) (all bugs)

**Versions**: `anaconda-mcp=1.0.0.rc.2` · `environments-mcp-server=1.0.0.rc.2` · `anaconda-connector-core=0.1.11` · `anaconda-connector-conda=0.1.11` · `anaconda-connector-utilities=0.1.11`

**Status**: 🔶 In progress

**Date**: 2026-03-18

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
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | Core only | ⬜ Not started | — |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | Core only | ⬜ Not started | — |
| QA 2 | macOS | Claude Desktop | 3.12 | STDIO | Core only | ⬜ Not started | — |

### QA 2 · macOS · Python 3.13 — Completion Notes

**All 8 tests passed** by using workarounds and shorter flows to avoid known bugs.

| Category | Details |
|----------|---------|
| **Fixed this iteration** | DESK-1401 (403 on private channels) — resolved with connector 0.1.11 |
| **Bugs with workarounds** | DESK-1411 (port 8000 conflict) — quit Claude Desktop before `anaconda login` |
| | DESK-1408 (package install error) — bigger delay in settings |
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
| QA 1 | macOS, 3.10 | ⬜ | ⬜ |
| QA 1 | macOS, 3.11 | ⬜ | ⬜ |
| QA 2 | macOS, 3.12 | ⬜ | ⬜ |

**Legend**: ⬜ Not started · 🔶 In progress · ✅ Pass · ❌ Fail

---

## Bug Retesting Progress

Each QA retests their own opened bugs.

| QA | Bug ID | Title | Status |
|----|--------|-------|--------|
| QA 1 | — | *(list QA 1 opened bugs)* | — |
| QA 2 | — | *(list QA 2 opened bugs)* | — |

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

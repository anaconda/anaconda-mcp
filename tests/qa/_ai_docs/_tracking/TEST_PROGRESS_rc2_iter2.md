# Test Progress — RC2, Iteration 2 (Connector 0.1.11)

> <- [Testing Overview](./TEST_PROGRESS.md) · Matrix: [TEST_MATRIX_rc2_iter2.md](../_planning/TEST_MATRIX_rc2_iter2.md) · All bugs: [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119)

**Versions**: `anaconda-mcp=1.0.0.rc.2` · `environments-mcp-server=1.0.0.rc.2` · `anaconda-connector-core=0.1.11` · `anaconda-connector-conda=0.1.11` · `anaconda-connector-utilities=0.1.11`

**Status**: 🔶 In progress

**Date**: 2026-03-17

---

## E2E Progress

| QA | OS | Client | Python | Transport | Strategy | Status | Result | Notes |
|----|----|--------|--------|-----------|----------|--------|--------|-------|
| QA 2 | macOS | Claude Desktop | 3.13 | STDIO | Full suite | 🔶 In progress | — | 3 passed / 1 blocked / 5 unexecuted |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | Sufficient | ⬜ Not started | — | |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | Pairwise A | ⬜ Not started | — | |
| QA 2 | macOS | Claude Desktop | 3.12 | STDIO | Pairwise B | ⬜ Not started | — | |

---

## Tests Per Config Progress

| QA | Config | SETUP-001 | CORE-001a | CORE-001 | CORE-001b | AUTH-001a | AUTH-002 | GUARD-001 | CHAN-001 | REGRESS-002 |
|----|--------|:---------:|:---------:|:--------:|:---------:|:---------:|:--------:|:---------:|:--------:|:-----------:|
| QA 2 | macOS, 3.13 | ✅ | ✅ | ✅ | blocked | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| QA 1 | macOS, 3.10 | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | — | — | — |
| QA 1 | macOS, 3.11 | — | ⬜ | ⬜ | — | — | ⬜ | ⬜ | — | — |
| QA 2 | macOS, 3.12 | — | ⬜ | ⬜ | — | ⬜ | ⬜ | — | ⬜ | ⬜ |

**Legend**: ⬜ Not started · 🔶 In progress · ✅ Pass · ❌ Fail · — Not in scope · blocked = blocked by bug

> **Note**: CORE-001b is blocked by [KI-027/DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413) — API key auth does not work for MCP channel access.

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
| [DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413) | `conda_create_environment` fails with "Token not found" when using API key auth instead of interactive login | Lowest | KI-027 | macOS | 2026-03-17 |

> Current status of each bug is tracked in Jira under [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119).

---

## Bug Summary

- **DESK-1401**: ✅ **FIXED** — 403 error on private channels resolved with anaconda-connector 0.1.11
- **DESK-1409**: mcp-compose proxy hang after ~17 tool calls — **blocks extended workflows**
- **DESK-1410**: Thread-safety violation exposed by PYTHONASYNCIODEBUG=1 — **workaround: remove debug flag**
- **DESK-1411**: Port 8000 conflict between mcp-compose and anaconda login — **workaround: quit Claude Desktop before login**
- **DESK-1413**: API key auth doesn't work for MCP channel access — **blocks CORE-001b**; workaround: use interactive login and question: whether we plan to support such type of authentication

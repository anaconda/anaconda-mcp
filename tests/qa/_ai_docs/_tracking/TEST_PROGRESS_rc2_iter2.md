# Test Progress — RC2, Iteration 2 (Connector 0.1.11)

> ← [Testing Overview](./TEST_PROGRESS.md) · Matrix: [TEST_MATRIX_rc2_iter2.md](../_planning/TEST_MATRIX_rc2_iter2.md) · All bugs: [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119)

**Versions**: `anaconda-mcp=1.0.0.rc.2` · `environments-mcp-server=1.0.0.rc.2` · `anaconda-connector-core=0.1.11` · `anaconda-connector-conda=0.1.11` · `anaconda-connector-utilities=0.1.11`

**Status**: ⬜ Not started

---

## E2E Progress

| QA | OS | Client | Python | Transport | Strategy | Status | Result | Notes |
|----|----|--------|--------|-----------|----------|--------|--------|-------|
| QA 2 | macOS | Claude Desktop | 3.13 | STDIO | Full suite | ⬜ Not started | — | |
| QA 1 | macOS | Claude Desktop | 3.10 | STDIO | Sufficient | ⬜ Not started | — | |
| QA 1 | macOS | Claude Desktop | 3.11 | STDIO | Pairwise A | ⬜ Not started | — | |
| QA 2 | macOS | Claude Desktop | 3.12 | STDIO | Pairwise B | ⬜ Not started | — | |

---

## Tests Per Config Progress

| QA | Config | SETUP-001 | CORE-001a | CORE-001 | AUTH-001a | AUTH-002 | GUARD-001 | CHAN-001 | REGRESS-002 |
|----|--------|:---------:|:---------:|:--------:|:---------:|:--------:|:---------:|:--------:|:-----------:|
| QA 2 | macOS, 3.13 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| QA 1 | macOS, 3.10 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | — | — | — |
| QA 1 | macOS, 3.11 | — | ⬜ | ⬜ | — | ⬜ | ⬜ | — | — |
| QA 2 | macOS, 3.12 | — | ⬜ | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ |

**Legend**: ⬜ Not started · 🔶 In progress · ✅ Pass · ❌ Fail · — Not in scope

---

## Fixes to Verify This Iteration

| ID | Title | Key test(s) | Verification |
|----|-------|-------------|-------------|
| [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) | `conda_create_environment` returns 403 despite valid auth | AUTH-002 (all 4 configs) | ⬜ |
| [DESK-1405](https://anaconda.atlassian.net/browse/DESK-1405) | RC2 install fails with Python 3.10 / 3.11 / 3.12 | SETUP-001 + CORE-001 on 3.10, 3.11, 3.12 | ⬜ |

---

## Bugs Found This Iteration

| ID | Title | Severity | Platform | Date |
|----|-------|----------|----------|------|
| — | — | — | — | — |

> Current status of each bug is tracked in Jira under [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119).

# ANACONDA MCP RELEASE TESTING SUMMARY

**Release Candidate**: 1.0.0.rc.2
**Connector Version**: anaconda-connector 0.1.11
**Date**: 2026-03-17

---

## Test Type

- E2E manual regression — in progress

---

## Key Findings

With anaconda-connector 0.1.11, **anaconda-mcp server now supports both user flows**:
- Authorized user (interactive login with private channels)
- Non-authorized user (logged out with public channels)

**Main E2E flow passed for both options.** All today's findings are not related to latest changes — discovered through deeper testing.

---

## Release Decision

- RC2+anaconda-connector 0.1.11 testing in progress (based on first results - this combination works better than rc2+0.1.10)
- 1 bug fixed (DESK-1401)
- 4 new bugs filed today (edge cases, not blocking core functionality, not related to latest changes)

---

## RC2 Tested Configurations

- macOS | Python 3.13 | STDIO | Claude Desktop — in progress (3 passed, 1 blocked, 3 unexecuted)
- macOS | Python 3.10 | STDIO | Claude Desktop — not started
- macOS | Python 3.11 | STDIO | Claude Desktop — not started
- macOS | Python 3.12 | STDIO | Claude Desktop — not started

---

## Test Results (macOS, Python 3.13)

- SETUP-001 — Pass (installation verified)
- CORE-001a — Pass (full flow, logged out user)
- CORE-001 — Pass (full flow, logged in user)
- CORE-001b — Blocked (API key auth — blocked by DESK-1413)

---

## Defect Summary

- **4 new bugs filed today** (edge cases from deeper testing)
- **1 bug verified fixed** (DESK-1401)
- All bugs linked to [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119)

---

## Fixed This Iteration

- [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) — `conda_create_environment` returns 403 despite valid auth — Fixed (connector 0.1.11)

---

## Filed Today (2026-03-17)

- [DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409) — Claude Desktop chat freezes after ~17 conda_install_packages calls (High, blocks extended workflows)
- [DESK-1410](https://anaconda.atlassian.net/browse/DESK-1410) — Claude Desktop fails after user adds PYTHONASYNCIODEBUG=1 (Lowest, workaround: remove debug flag)
- [DESK-1411](https://anaconda.atlassian.net/browse/DESK-1411) — Cannot run `anaconda login` while Claude Desktop is running, port 8000 conflict (Lowest, workaround: quit Claude Desktop before login)
- [DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413) — API key auth fails with "Token not found" for MCP channel access (Lowest, workaround: use interactive login)

---

## More Details

- [DESK-1119](https://anaconda.atlassian.net/browse/DESK-1119) — All bugs
- [TEST_PROGRESS_rc2_iter2.md](./TEST_PROGRESS_rc2_iter2.md) — Detailed test progress
- [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) — Known issues catalog

CC: @Jack Evans, @Mihaela Stoica, @Vasu (EST), @Rob Sarro, @Vidya (UK - BST/GMT), @Pablo (London - BST), @Rida Zubair (Pakistan - PKT), @Inha Zaheen

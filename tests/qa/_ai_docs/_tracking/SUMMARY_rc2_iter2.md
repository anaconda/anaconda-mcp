# ANACONDA MCP RELEASE TESTING SUMMARY

**RC 1.0.0.rc.2 + connector 0.1.11** · 2026-03-18 · [DESK-1421](https://anaconda.atlassian.net/browse/DESK-1421)

---

## Status

- **First config completed: macOS / Python 3.13 — 8/8 tests passed**
- **No new bugs found**
- Remaining configs (Python 3.10, 3.11, 3.12) will be tested.
- previously opened bugs will be retested

---

## ⚠️ Attention: DESK-1409 (Proxy Hang)

[DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409) — **consistently reproducible, needs decision**

- Claude Desktop freezes after ~17 sequential tool calls
- Confirmed on: `conda_install_packages`, `conda_remove_environment` (likely affects all/many tools)
- 100% reproducible
- Triggers on batch operations ("delete all test environments"), many package installs, extended workflows
- User impact: chat freezes, restart required, context lost
- Component: mcp-compose (upstream, not anaconda-mcp)

**Decision needed:**
- Option A: Prioritize fix in mcp-compose
- Option B: Accept as limitation — 17+ sequential calls is edge case for average users

Tests passed using shorter flows, but real productive work (project setup, batch cleanup) might hit this.

---

## Fixed

- [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) — 403 on private channels (fixed with connector 0.1.11)

## Closed (By Design)

- [DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413) — API key auth cannot replace interactive login (expected per Anaconda docs)

## Minor Bugs (workarounds available)

- [DESK-1411](https://anaconda.atlassian.net/browse/DESK-1411) — port 8000 conflict → quit Claude Desktop before `anaconda login`
- [DESK-1408](https://anaconda.atlassian.net/browse/DESK-1408) — package install error → use bigger delay
- [DESK-1402](https://anaconda.atlassian.net/browse/DESK-1402) — first tool call errors → retry works
- [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) — string "false" truthy → use `""` or remove env var

---

## Links

- [DESK-1421](https://anaconda.atlassian.net/browse/DESK-1421) — release activitiees in sprint 5
- [TEST_PROGRESS_rc2_iter2.md](./TEST_PROGRESS_rc2_iter2.md) — detailed progress

CC: @Jack Evans, @Mihaela Stoica, @Vasu (EST), @Rob Sarro, @Vidya (UK - BST/GMT), @Pablo (London - BST), @Rida Zubair (Pakistan - PKT), @Inha Zaheen

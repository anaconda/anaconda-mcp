# ANACONDA MCP RELEASE TESTING SUMMARY

**RC 1.0.0.rc.2 + connector 0.1.11** · 2026-03-19 · [DESK-1421](https://anaconda.atlassian.net/browse/DESK-1421)

---

## E2E Testing — 3/4 configs done

- ✅ macOS 3.13 — 8/8 passed (QA 2)
- ✅ macOS 3.12 — 2/2 passed (QA 2)
- ✅ macOS 3.10 — 2/2 passed (QA 1)
- ⬜ macOS 3.11 — not started (QA 1)

---

## Bug Retesting — done ([DESK-1423](https://anaconda.atlassian.net/browse/DESK-1423))

### ✅ Verified Fixed (12)
- DESK-1401, DESK-1384, DESK-1366, DESK-1358, DESK-1355, DESK-1342
- DESK-1359, DESK-1341, DESK-1408, DESK-1405, DESK-1389, DESK-1391

### 🔴 Reproducible (6)
- [DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409) — chat freezes after ~17 tool calls (decision needed)
- [DESK-1411](https://anaconda.atlassian.net/browse/DESK-1411) — port 8000 conflict
- [DESK-1410](https://anaconda.atlassian.net/browse/DESK-1410) — PYTHONASYNCIODEBUG breaks env creation
- [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) — string "false" parsed as truthy
- [DESK-1402](https://anaconda.atlassian.net/browse/DESK-1402) — first tool call "Not Loaded Yet"
- [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356) — CLI suggests wrong transport mode

### ❓ Need Clarification (3)
- [DESK-1416](https://anaconda.atlassian.net/browse/DESK-1416) — may duplicate DESK-1358
- [DESK-1424](https://anaconda.atlassian.net/browse/DESK-1424) — need repro steps
- [DESK-1427](https://anaconda.atlassian.net/browse/DESK-1427) — cold-start or consistent?

### ⏸️ Postponed — Windows (6)
- DESK-1386, DESK-1385, DESK-1363, DESK-1390, DESK-1365, DESK-1344

### N/A (5)
- DESK-1413 (by design), DESK-1364 (superseded), DESK-1394/1393/1392 (feature requests)

---

## Links

- [DESK-1421](https://anaconda.atlassian.net/browse/DESK-1421) — sprint 5
- [DESK-1423](https://anaconda.atlassian.net/browse/DESK-1423) — bug retesting
- [TEST_PROGRESS_rc2_iter2.md](./TEST_PROGRESS_rc2_iter2.md) — detailed progress

CC: @Jack Evans, @Mihaela Stoica, @Vasu (EST), @Rob Sarro, @Vidya (UK - BST/GMT), @Pablo (London - BST), @Rida Zubair (Pakistan - PKT), @Inha Zaheen

# Test Matrix — RC2

## Rationale for Reduced Matrix

Based on RC1 findings (10 bugs filed, Phase 1 complete):

| Finding | Implication |
|---------|-------------|
| No transport-specific bugs | HTTP issues were config/proxy bugs, not transport layer |
| No Python-version-specific bugs | Bugs reproduced across all versions |
| Target client is Claude Desktop | STDIO transport only; HTTP is secondary |
| Windows has unique bugs | Keep Windows coverage (DESK-1344, DESK-1363) |

### What We Cut

| Dimension | RC1 | RC2 | Why |
|-----------|-----|-----|-----|
| Python versions | 3.10, 3.11, 3.12, 3.13 | 3.10, 3.13 | Boundaries sufficient; no mid-version bugs |
| Transport | STDIO + HTTP | STDIO | Target client (Claude Desktop) uses STDIO |
| Clients | Claude Desktop, Cursor, Claude Code | Claude Desktop | Target client; others use same MCP protocol |
| E2E tests per config | 6 flows | 1-3 flows | REGRESS-001 overlaps CORE-001; AUTH/GUARD config-independent |

---

## Resources

| QA | Manual | Automation |
|----|--------|------------|
| QA 1 | 66-75% | — |
| QA 2 | 25-33% | 100% |

**Manual split**: QA 1 takes majority (~3/4), QA 2 takes remainder (~1/4)

---

## E2E Test Matrix

### Configurations (4 total)

| # | OS | Client | Python | Transport | QA |
|---|-----|--------|--------|-----------|-----|
| 1 | macOS | Claude Desktop | 3.13 | STDIO | QA 1 |
| 2 | macOS | Claude Desktop | 3.10 | STDIO | QA 1 |
| 3 | Windows | Claude Desktop | 3.13 | STDIO | QA 2 |
| 4 | Windows | Claude Desktop | 3.10 | STDIO | QA 1 |

**Rationale**:
- QA 1 takes 3 configs (71%) — macOS both + Windows 3.10
- QA 2 takes 1 config (29%) — Windows 3.13 with AUTH-002

### Tests Per Configuration

| Config | CORE-001 | AUTH-002 | GUARD-001 | Total Steps |
|--------|----------|----------|-----------|-------------|
| 1 (macOS, 3.13) | Yes | Yes | Yes | 13 |
| 2 (macOS, 3.10) | Yes | — | — | 7 |
| 3 (Windows, 3.13) | Yes | Yes | — | 11 |
| 4 (Windows, 3.10) | Yes | — | — | 7 |

**Rationale**:
- CORE-001: All configs — covers all 6 tools, catches regressions
- AUTH-002: One per OS — credential pickup is OS-specific (different keychain/credential store)
- GUARD-001: macOS only — guardrails are config-independent, run once

---

## Eliminated Tests

| Test | Reason |
|------|--------|
| REGRESS-001 | Fully overlaps with CORE-001 (same tools, same flows) |
| REGRESS-002 | KI-003 regression covered by CORE-001 step 6 (delete by name) |
| AUTH-001 | Anonymous mode = CORE-001 without login; implicit coverage |
| AUTH-001a | Blocked by KI-005; still blocked in RC2 |

---

## Comparison: RC1 vs RC2

| Metric | RC1 | RC2 | Reduction |
|--------|-----|-----|-----------|
| Configurations | 9 | 4 | 56% |
| Tests per config | 6 | 1-3 | 50-83% |
| Total manual steps | ~92 | 38 | 59% |

---

## Risk Acceptance

| Eliminated Coverage | Risk | Mitigation |
|---------------------|------|------------|
| Python 3.11, 3.12 | Low | No version-specific bugs in RC1 |
| HTTP transport | Low | Target is STDIO; HTTP bugs were config issues |
| Cursor, Claude Code | Low | Same MCP protocol; client-specific bugs unlikely |
| REGRESS-001 separate run | None | CORE-001 covers same flows |

---

## Checklist

### QA 1 (3 configs)
```
macOS, Python 3.13:
[ ] Setup: Install anaconda-mcp RC2, configure Claude Desktop
[ ] CORE-001: Full tools flow
[ ] AUTH-002: Authenticated mode
[ ] GUARD-001: Guardrails

macOS, Python 3.10:
[ ] Setup: Install anaconda-mcp RC2, configure Claude Desktop
[ ] CORE-001: Full tools flow

Windows, Python 3.10:
[ ] Setup: Install anaconda-mcp RC2, configure Claude Desktop
[ ] CORE-001: Full tools flow
```

### QA 2 (1 config)
```
Windows, Python 3.13:
[ ] Setup: Install anaconda-mcp RC2, configure Claude Desktop
[ ] CORE-001: Full tools flow (if DESK-1344 fixed)
[ ] AUTH-002: Authenticated mode
```

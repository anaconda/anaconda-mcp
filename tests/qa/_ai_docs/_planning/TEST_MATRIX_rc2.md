# Test Matrix — RC2

## Rationale for Reduced Matrix

Based on RC1 findings (13 bugs filed, Phase 1 complete):

| Finding | Implication |
|---------|-------------|
| No transport-specific bugs | HTTP issues were config/proxy bugs, not transport layer |
| No Python-version-specific bugs | Bugs reproduced across all versions |
| Target client is Claude Desktop | STDIO transport only; HTTP is secondary |
| Windows has unique bugs | Keep Windows coverage (DESK-1344, DESK-1363, DESK-1385, DESK-1386) |
| **Auth state affects behavior on Windows** | DESK-1386 only manifests when logged in — RC1 missed this; Windows E2E must be run in both logged-in and logged-out states |

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

## Documentation

| Document | Purpose |
|----------|---------|
| [QA_WALKTHROUGH.md](../QA_WALKTHROUGH.md) | Test catalog and navigation |
| [tests/](../tests/) | Individual test definitions |
| [AUTH_SETUP.md](../tests/e2e/setup/AUTH_SETUP.md) | Authentication prerequisites and cleanup procedures |
| [KNOWN_ISSUES.md](../_tracking/KNOWN_ISSUES.md) | Bug details and workarounds |
| [WINDOWS_SETUP.md](../tests/e2e/setup/WINDOWS_SETUP.md) | Windows-specific setup instructions |

---

## E2E Test Matrix

### Configurations (4 total)

| # | OS | Client | Python | Transport | Auth state | QA |
|---|-----|--------|--------|-----------|------------|----|
| 1 | macOS | Claude Desktop | 3.13 | STDIO | **Both** | QA 2 |
| 2 | macOS | Claude Desktop | 3.10 | STDIO | **Both** | QA 1 |
| 3 | Windows | Claude Desktop | 3.13 | STDIO | **Both** | QA 1 |
| 4 | Windows | Claude Desktop | 3.10 | STDIO | **Both** | QA 2 |

**Auth state**: All configs now test both logged-in (CORE-001) and logged-out (CORE-001a) flows. This catches auth-state-dependent regressions discovered during RC2 testing where logged-in flow showed issues.

> **DESK-1385/1386 status**: Not confirmed fixed in RC2. Test both auth states on all configs and document failures explicitly — anaconda-connector changes may have affected behavior. See [WINDOWS_SETUP.md](../tests/e2e/setup/WINDOWS_SETUP.md#3-open-claude-desktop-and-wait-for-connection) for setup.


### Tests Per Configuration

| QA | Config | SETUP-001 | CORE-001a (logged out) | CORE-001 (logged in) | AUTH-002 | AUTH-001a | GUARD-001 | CHAN-001 | REGRESS-002 | Total |
|----|--------|-----------|------------------------|----------------------|----------|-----------|-----------|----------|-------------|-------|
| QA 2 | macOS, 3.13 | + | + | + | + | + | + | + | + | 9 |
| QA 1 | macOS, 3.10 | + | + | + | — | — | — | — | — | 3 |
| QA 1 | Windows, 3.13 | + | + | + | + | — | + | — | — | 5 |
| QA 2 | Windows, 3.10 | + | + | + | — | — | — | — | — | 3 |

> **New tests for RC2**: SETUP-001 (installation disclaimer), CHAN-001 (override_channels behavior), REGRESS-002 (DESK-1342 fix). See [tests/](./tests/) for details.
>
> **AUTH-001a unblocked**: URL routing fixed — anonymous users now correctly get 403 auth error on `repo.anaconda.cloud`. AUTH-002 still blocked by DESK-1401 (credentials not passed).

**Rationale**:
- SETUP-001: all configs — verifies terms & conditions disclaimer appears during installation (new RC2 feature)
- CORE-001a: all configs — logged-out flow catches auth-state-dependent issues discovered during RC2
- CORE-001: all configs — logged-in flow; normal user scenario
- AUTH-002: logged-in only by definition — tests credential pickup; macOS 3.13 + Windows 3.13
- AUTH-001a: macOS 3.13 only — verifies anonymous user gets 403 on private channels (unblocked in RC2)
- GUARD-001: macOS 3.13 + Windows 3.13 — guardrails are config-independent but Windows has shown enough unexpected behavior to warrant explicit coverage
- CHAN-001: macOS 3.13 only — verifies `override_channels` disabled by default (new RC2 behavior); config-independent
- REGRESS-002: macOS 3.13 only — explicit DESK-1342 fix verification (environment name operations)

---

## Bug Fix Retesting

RC1 filed 10 bugs. Fixed bugs require verification before release.

| Activity | Scope | Est. Time |
|----------|-------|-----------|
| Verify fixed bugs | Per bug: reproduce original issue, confirm fix | ~10-15 min/bug |
| Regression check | Ensure fix didn't break related functionality | Included in CORE-001 |

**Note**: Actual retesting time depends on how many bugs are fixed in RC2. Not all RC1 bugs may be fixed for this release.

---

## Eliminated Tests

| Test | Reason |
|------|--------|
| REGRESS-001 | Fully overlaps with CORE-001 (same tools, same flows) |
| AUTH-001 | Anonymous mode = CORE-001a (logged out); implicit coverage |

> **Note**: REGRESS-002 was previously eliminated but is **reinstated for RC2** to explicitly verify the DESK-1342 fix (environment name operations). See [REGRESS-002.md](./tests/e2e/REGRESS-002.md).

---

---

## Risk Acceptance

| Eliminated Coverage | Risk | Mitigation |
|---------------------|------|------------|
| Python 3.11, 3.12 | Low | No version-specific bugs in RC1 |
| HTTP transport | Low | Target is STDIO; HTTP bugs were config issues |
| Cursor, Claude Code | Low | Same MCP protocol; client-specific bugs unlikely |
| REGRESS-001 separate run | None | CORE-001 covers same flows |

> **Note on auth state**: All configs now test both logged-in and logged-out states after issues discovered during RC2 testing.

---

## Execution

See [Tests Per Configuration](#tests-per-configuration) table for assignments. Track progress in [TEST_PROGRESS.md](../_tracking/TEST_PROGRESS.md).

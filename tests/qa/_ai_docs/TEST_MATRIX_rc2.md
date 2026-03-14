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
| [INDEX.md](./INDEX.md) | Test catalog and navigation |
| [tests/](./tests/) | Individual test definitions |
| [AUTH_SETUP.md](./tests/e2e/setup/AUTH_SETUP.md) | Authentication prerequisites and cleanup procedures |
| [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) | Bug details and workarounds |
| [WINDOWS_SETUP.md](./tests/e2e/setup/WINDOWS_SETUP.md) | Windows-specific setup instructions |

---

## E2E Test Matrix

### Configurations (4 total)

| # | OS | Client | Python | Transport | Auth state | QA |
|---|-----|--------|--------|-----------|------------|----|
| 1 | macOS | Claude Desktop | 3.13 | STDIO | Logged in + **logged out if DESK-1385/1386 fixed** | QA 1 |
| 2 | macOS | Claude Desktop | 3.10 | STDIO | Logged in | QA 1 |
| 3 | Windows | Claude Desktop | 3.13 | STDIO | **Both** (see below) | QA 2 |
| 4 | Windows | Claude Desktop | 3.10 | STDIO | **Both** (see below) | QA 1 |

**Auth state on Windows**: each Windows config requires two passes — one logged out, one logged in. Required to catch regressions of [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386) (retry failure when logged in) and [DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385) (first-call hang in any state).

**Auth state on macOS**: currently safe to test logged-in only — DESK-1385/1386 trigger (GET stream disconnect) never fires on macOS as the first call completes in <1s. However, the fixes for DESK-1385/1386 will change `environments_mcp_server` startup (warmup) and telemetry error handling — code paths that run on macOS too. **Add one logged-out pass on macOS config 1 when DESK-1385/1386 fixes are included in RC2**, to catch any regressions introduced by those changes.

> **DESK-1385/1386 status**: Not confirmed fixed in RC2. Test both auth states on Windows and document failures explicitly — anaconda-connector changes may have affected behavior. See [WINDOWS_SETUP.md](./tests/e2e/setup/WINDOWS_SETUP.md#3-open-claude-desktop-and-wait-for-connection) for setup.


### Tests Per Configuration

| QA | Config | SETUP-001 | CORE-001a (logged out) | CORE-001 (logged in) | AUTH-002 | AUTH-001a | GUARD-001 | CHAN-001 | REGRESS-002 | Total |
|----|--------|-----------|------------------------|----------------------|----------|-----------|-----------|----------|-------------|-------|
| QA 2 | macOS, 3.13 | + | + | + | + | + | + | + | + | 9 |
| QA 1 | macOS, 3.10 | + | — | + | — | — | — | — | — | 2 |
| QA 1 | Windows, 3.13 | + | + | + | + | — | + | — | — | 5 |
| QA 2 | Windows, 3.10 | + | + | + | — | — | — | — | — | 3 |

> **New tests for RC2**: SETUP-001 (installation disclaimer), CHAN-001 (override_channels behavior), REGRESS-002 (DESK-1342 fix). See [tests/](./tests/) for details.
>
> **AUTH-001a unblocked**: URL routing fixed — anonymous users now correctly get 403 auth error on `repo.anaconda.cloud`. AUTH-002 still blocked by DESK-1401 (credentials not passed).

**Rationale**:
- SETUP-001: all configs — verifies terms & conditions disclaimer appears during installation (new RC2 feature)
- CORE-001a (Windows): logged-out flow — verifies DESK-1385 fix (first call must complete without hang)
- CORE-001 (Windows): logged-in flow — verifies DESK-1386 fix (retry after first-call hang must succeed); also the normal user scenario
- CORE-001/001a (macOS config 1): both auth states — catches any auth-state-dependent regressions; config 2 logged-in only (baseline coverage sufficient)
- AUTH-002: logged-in only by definition — tests credential pickup; running logged-out would duplicate CORE-001
- GUARD-001: macOS config 1 + Windows config 3 — guardrails are config-independent but Windows has shown enough unexpected behavior to warrant explicit coverage there too
- CHAN-001: macOS config 1 only — verifies `override_channels` disabled by default (new RC2 behavior); config-independent, single config sufficient
- REGRESS-002: macOS config 1 only — explicit DESK-1342 fix verification (environment name operations); critical RC2 claim

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
| AUTH-001 | Anonymous mode = CORE-001 without login; implicit coverage |
| AUTH-001a | Blocked by KI-005; still blocked in RC2 |

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
| Auth state on macOS | Low | DESK-1385/1386 trigger never fires on macOS; first call <1s |

> **Note on Windows auth state**: Not eliminated — explicitly tested in both logged-in and logged-out states. DESK-1385/1386 are not confirmed fixed, but anaconda-connector changes may affect behavior. Document failures explicitly.

---

## Checklist

### Bug Fix Retesting (both QAs)
```
[ ] Review RC2 release notes for fixed bugs
[ ] Verify each fixed bug (reproduce → confirm fix)
```

### QA 1 (3 configs)
```
macOS, Python 3.13:
[ ] Setup: Install anaconda-mcp RC2, configure Claude Desktop
[ ] SETUP-001: Installation disclaimer verification
[ ] CORE-001: Full tools flow — logged in (see [AUTH_SETUP.md](./tests/e2e/setup/AUTH_SETUP.md))
[ ] CORE-001a: Full tools flow — logged out (run cleanup after CORE-001, see [AUTH_SETUP.md](./tests/e2e/setup/AUTH_SETUP.md))
[ ] AUTH-002: Authenticated mode
[ ] AUTH-001a: Private channel denial — anonymous user gets 403 on repo.anaconda.cloud (unblocked)
[ ] GUARD-001: Guardrails (with RC2 confirmation verification)
[ ] CHAN-001: Override channels behavior (both parts A and B)
[ ] REGRESS-002: DESK-1342 fix verification

macOS, Python 3.10:
[ ] Setup: Install anaconda-mcp RC2, configure Claude Desktop
[ ] SETUP-001: Installation disclaimer verification
[ ] CORE-001: Full tools flow — logged in

Windows, Python 3.10 — logged out:
[ ] Setup: kill Claude + port 4041, log out of Anaconda, install RC2, configure Claude Desktop
[ ] SETUP-001: Installation disclaimer verification
[ ] CORE-001a: Full tools flow — logged out (verifies DESK-1385 fix — first call must succeed without hang)

Windows, Python 3.10 — logged in:
[ ] Setup: kill Claude + port 4041, log in to Anaconda, install RC2, configure Claude Desktop
[ ] CORE-001: Full tools flow — logged in (verifies DESK-1386 fix — retry after any hang must succeed)
```

### QA 2 (1 config)
```
Windows, Python 3.13 — logged out:
[ ] Setup: kill Claude + port 4041, log out of Anaconda, install RC2, configure Claude Desktop
[ ] SETUP-001: Installation disclaimer verification
[ ] CORE-001a: Full tools flow — logged out (if DESK-1344 fixed; verifies DESK-1385 fix)

Windows, Python 3.13 — logged in:
[ ] Setup: kill Claude + port 4041, log in to Anaconda, install RC2, configure Claude Desktop
[ ] CORE-001: Full tools flow — logged in (verifies DESK-1386 fix)
[ ] AUTH-002: Authenticated mode
[ ] GUARD-001: Guardrails
```

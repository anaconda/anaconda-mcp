# Test Matrix — RC2, Iteration 2 (Connector 0.1.11)

> Previous iteration: [TEST_MATRIX_rc2.md](./TEST_MATRIX_rc2.md)

## Versions Under Test

| Package | Version |
|---------|---------|
| `anaconda-mcp` | `1.0.0.rc.2` |
| `environments-mcp-server` | `1.0.0.rc.2` |
| `anaconda-connector-core` | `0.1.11` |
| `anaconda-connector-conda` | `0.1.11` |
| `anaconda-connector-utilities` | `0.1.11` |

---

## Rationale for Matrix Changes

| Decision | Reason |
|----------|--------|
| **Windows excluded** | Python version compatibility failures (DESK-1405) block stable execution; defer until root cause confirmed resolved |
| **All 4 Python versions** | DESK-1405 affected 3.10/3.11/3.12 — full coverage needed to confirm the fix holds across all versions |
| **STDIO only** | Claude Desktop is the target client; no transport-specific bugs observed |
| **Claude Desktop only** | Target client; same MCP protocol for others |
| **Auth coverage expanded** | Auth improvements expected in connector 0.1.11; AUTH-002 (previously blocked by DESK-1401) should be validated across more configs |

### Coverage Strategy

| Python | Strategy | Rationale |
|--------|----------|-----------|
| **3.13** | Full suite | Latest boundary — most representative of current users; anchor for all test results |
| **3.10** | Sufficient suite | Oldest boundary — catch compatibility regressions; auth + core flows |
| **3.11** | Pairwise A | Middle version — guards + auth; complements 3.12 |
| **3.12** | Pairwise B | Middle version — channels + regression + auth; complements 3.11 |

Together, 3.11 + 3.12 cover every test in the suite. AUTH-002 runs on all four configs given expected auth improvements.

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
| [QUICK_START.md](../tests/e2e/setup/QUICK_START.md) | Installation and setup for RC2 |

---

## E2E Test Matrix

### Configurations (4 total)

| # | OS | Client | Python | Transport | Auth state | Strategy | QA |
|---|-----|--------|--------|-----------|------------|----------|----|
| 1 | macOS | Claude Desktop | 3.13 | STDIO | Both | Full suite | QA 2 |
| 2 | macOS | Claude Desktop | 3.10 | STDIO | Both | Sufficient | QA 1 |
| 3 | macOS | Claude Desktop | 3.11 | STDIO | Both | Pairwise A | QA 1 |
| 4 | macOS | Claude Desktop | 3.12 | STDIO | Both | Pairwise B | QA 2 |

### Tests Per Configuration

| QA | Config | SETUP-001 | CORE-001a | CORE-001 | CORE-001b | AUTH-001a | AUTH-002 | GUARD-001 | CHAN-001 | REGRESS-002 | Total |
|----|--------|:---------:|:---------:|:--------:|:---------:|:---------:|:--------:|:---------:|:--------:|:-----------:|:-----:|
| QA 2 | macOS, 3.13 | + | + | + | blocked | + | + | + | + | + | **8** |
| QA 1 | macOS, 3.10 | + | + | + | — | + | + | — | — | — | **5** |
| QA 1 | macOS, 3.11 | — | + | + | — | — | + | + | — | — | **4** |
| QA 2 | macOS, 3.12 | — | + | + | — | + | + | — | + | + | **6** |

> **Note**: CORE-001b is blocked by [KI-027](../bug_details/api_key_auth/KI-027-api-key-auth-not-working-mcp.md) — API key auth does not work for MCP channel access.

**Pairwise coverage check** — 3.11 + 3.12 together:

| Test | 3.11 | 3.12 | Combined |
|------|:----:|:----:|:--------:|
| SETUP-001 | — | — | covered by 3.13 + 3.10 |
| CORE-001a | + | + | ✓ |
| CORE-001 | + | + | ✓ |
| CORE-001b | — | — | **blocked by KI-027** (API key auth doesn't work) |
| AUTH-001a | — | + | ✓ |
| AUTH-002 | + | + | ✓ |
| GUARD-001 | + | — | ✓ |
| CHAN-001 | — | + | ✓ |
| REGRESS-002 | — | + | ✓ |

**Rationale per test**:
- **SETUP-001**: 3.13 (full) + 3.10 (sufficient) — installation disclaimer is version-independent; two configs sufficient
- **CORE-001a / CORE-001**: all 4 configs — core flow is the baseline for every config
- **CORE-001b**: 3.13 only — **BLOCKED by KI-027**; API key authentication does not work for MCP channel access; test cannot be executed until bug is fixed
- **AUTH-001a**: 3.13, 3.10, 3.12 — anonymous private channel 403 behavior; confirmed working in Iteration 1, spot-check on 3 configs
- **AUTH-002**: all 4 configs — connector 0.1.11 includes auth improvements; DESK-1401 may be resolved; must validate across all Python versions
- **GUARD-001**: 3.13, 3.11 — guardrails are config-independent; two configs sufficient
- **CHAN-001**: 3.13, 3.12 — `override_channels` behavior is config-independent; two configs sufficient
- **REGRESS-002**: 3.13, 3.12 — KI-003 fix confirmed in Iteration 1; spot-check on two configs

---

## Risk Acceptance

| Eliminated Coverage | Risk | Mitigation |
|---------------------|------|------------|
| Windows | Medium | Deferred due to DESK-1405; re-evaluate for RC3 or GA |
| HTTP transport | Low | No transport-specific bugs; STDIO is target |
| SETUP-001 on 3.11, 3.12 | Low | Installation behavior is version-independent |
| CORE-001b | N/A | **Blocked by KI-027** — API key auth doesn't work; cannot validate KI-026 workaround until fixed |
| GUARD-001 on 3.10, 3.12 | Low | Guardrails are config-independent; covered on 3.13 + 3.11 |
| CHAN-001 on 3.10, 3.11 | Low | `override_channels` is config-independent; covered on 3.13 + 3.12 |
| REGRESS-002 on 3.10, 3.11 | Low | Fix already confirmed in Iteration 1; covered on 3.13 + 3.12 |

---

## Execution

See [Tests Per Configuration](#tests-per-configuration) table for assignments. Track progress in [TEST_PROGRESS.md](../_tracking/TEST_PROGRESS.md).

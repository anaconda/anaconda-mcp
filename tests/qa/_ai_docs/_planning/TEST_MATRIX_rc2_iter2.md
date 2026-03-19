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

## Goals

1. **Core flow validation** across all 4 Python versions (CORE-001, CORE-001a)
2. **Bug retesting**: each QA retests their own opened bugs
   - QA 1: retest bugs filed by QA 1
   - QA 2: retest bugs filed by QA 2

## Rationale for Matrix Changes

| Decision | Reason |
|----------|--------|
| **Simplified scope** | Version about to publish — focus on core flows; further testing deferred to subsequent versions |
| **CORE-001 + CORE-001a only** | Core CRUD operations are the essential baseline; other tests already passed on 3.13 |
| **Bug retesting by author** | Each QA familiar with their bugs; efficient verification |

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
| 2 | macOS | Claude Desktop | 3.10 | STDIO | Both | Core only | QA 1 |
| 3 | macOS | Claude Desktop | 3.11 | STDIO | Both | Core only | QA 1 |
| 4 | macOS | Claude Desktop | 3.12 | STDIO | Both | Core only | QA 2 |

### Tests Per Configuration

| QA | Config | SETUP-001 | CORE-001a | CORE-001 | AUTH-001a | AUTH-002 | GUARD-001 | CHAN-001 | REGRESS-002 | Total |
|----|--------|:---------:|:---------:|:--------:|:---------:|:--------:|:---------:|:--------:|:-----------:|:-----:|
| QA 2 | macOS, 3.13 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **8** |
| QA 1 | macOS, 3.10 | — | ✅ | ✅ | — | — | — | — | — | **2** |
| QA 1 | macOS, 3.11 | — | + | + | — | — | — | — | — | **2** |
| QA 2 | macOS, 3.12 | — | ✅ | ✅ | — | — | — | — | — | **2** |

**Rationale**: Python 3.13 full suite completed. Remaining configs validate core CRUD flows only — version is about to publish, extended testing deferred to subsequent versions.

---

## Risk Acceptance

| Eliminated Coverage | Risk | Mitigation |
|---------------------|------|------------|
| Windows | Medium | Deferred due to DESK-1405; re-evaluate for subsequent versions |
| Extended test suite on 3.10/3.11/3.12 | Low | Full suite passed on 3.13; core flows validate Python compatibility |
| HTTP transport | Low | No transport-specific bugs; STDIO is target |

---

## Execution

See [Tests Per Configuration](#tests-per-configuration) table for assignments. Track progress in [TEST_PROGRESS.md](../_tracking/TEST_PROGRESS.md).

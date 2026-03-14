# QA Documentation Index

## Quick Links

| Priority | Document | Purpose |
|----------|----------|---------|
| 1 | [QA_WALKTHROUGH.md](./QA_WALKTHROUGH.md) | Step-by-step guide for running E2E tests |
| 2 | [TEST_PROGRESS.md](./_tracking/TEST_PROGRESS.md) | Current testing status and bug tracking |
| 3 | [TEST_MATRIX_rc2.md](./_planning/TEST_MATRIX_rc2.md) | RC2 test assignments and configurations |

---

## Structure Overview

```
_ai_docs/
├── INDEX.md                    ← You are here
├── QA_WALKTHROUGH.md           ← Start here for testing
│
├── _product/                   # What we're testing
│   ├── PRODUCT_OVERVIEW.md     # Architecture, features, constraints
│   ├── FEATURE_TREE.md         # Feature catalog with release scope
│   └── COVERAGE_MAP.md         # Feature → test mapping
│
├── _planning/                  # How we planned testing
│   ├── TEST_MATRIX_rc2.md      # Current release assignments
│   ├── TEST_MATRIX.md          # RC1 assignments (historical)
│   ├── TEST_DESIGN.md          # Test strategy rationale
│   ├── TEST_COVERAGE_ANALYSIS.md
│   └── TESTING_WORKFLOW.md
│
├── _tracking/                  # Progress and issues
│   ├── TEST_PROGRESS.md        # Results and bug summary
│   ├── KNOWN_ISSUES.md         # Bugs, workarounds, investigations
│   └── OPEN_QUESTIONS.md       # Decisions log
│
├── tech_details/               # Technical references
│   ├── CONFIGURATION.md        # Config options
│   ├── INSTALL_OPTIONS.md      # Installation methods
│   ├── LOCAL-DEV-SETUP.md      # Dev environment setup
│   └── CONDA_SETUP.md          # Miniconda vs Anaconda
│
├── tests/
│   ├── e2e/                    # E2E test definitions
│   │   ├── setup/              # Prerequisites (auth, Windows, etc.)
│   │   └── *.md                # Individual test flows
│   └── automation/             # Automatable tests (CLI, Config, API)
│
└── bug_details/                # Investigation artifacts
```

---

## By Role

**QA Tester**: Start with [QA_WALKTHROUGH.md](./QA_WALKTHROUGH.md)

**New to project**: Read [PRODUCT_OVERVIEW.md](./_product/PRODUCT_OVERVIEW.md) then [TEST_MATRIX_rc2.md](./_planning/TEST_MATRIX_rc2.md)

**Checking status**: See [TEST_PROGRESS.md](./_tracking/TEST_PROGRESS.md)

**Hit a bug**: Check [KNOWN_ISSUES.md](./_tracking/KNOWN_ISSUES.md)

# Anaconda MCP - QA Documentation Index

## Purpose
This documentation serves as the central knowledge base for QA testing of the Anaconda MCP server. Documents are structured for both manual QA testing and AI-assisted testing workflows.

## Document Structure

### Product Documentation
| Document | Description | Audience |
|----------|-------------|----------|
| [PRODUCT_OVERVIEW.md](./PRODUCT_OVERVIEW.md) | Product features, architecture, constraints | All QA |
| [FEATURE_TREE.md](./FEATURE_TREE.md) | 3-level feature tree with diagrams | All QA |
| [CONFIGURATION.md](./CONFIGURATION.md) | Configuration options reference | All QA |

### Test Flows (TESTS_* prefix)
| Document | Description | Platform |
|----------|-------------|----------|
| [TESTS_E2E_CLAUDE.md](./TESTS_E2E_CLAUDE.md) | E2E flows requiring Claude Desktop | macOS only |
| [TESTS_CLI.md](./TESTS_CLI.md) | CLI-only flows (automatable) | All platforms |
| [TESTS_CONFIG.md](./TESTS_CONFIG.md) | Configuration tests (automatable) | All platforms |
| [TESTS_API_TOOLS.md](./TESTS_API_TOOLS.md) | Direct API tool tests (automatable) | All platforms |

### Test Planning
| Document | Description | Audience |
|----------|-------------|----------|
| [E2E_COVERAGE_MAP.md](./E2E_COVERAGE_MAP.md) | Feature to test mapping | QA leads |
| [TEST_MATRIX.md](./TEST_MATRIX.md) | OS/Python/Transport matrix | QA leads |
| [TEST_COVERAGE_ANALYSIS.md](./TEST_COVERAGE_ANALYSIS.md) | Existing pytest coverage analysis | QA leads |
| [OPEN_QUESTIONS.md](./OPEN_QUESTIONS.md) | Questions for product owner | QA leads, PO |

### Reference
| Document | Description | Audience |
|----------|-------------|----------|
| [QUICK_START.md](./QUICK_START.md) | Minimal install steps | All QA |
| [LOCAL_DEV_SETUP.md](./LOCAL_DEV_SETUP.md) | Full setup guide with troubleshooting | All QA |
| [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) | Known bugs and regression tests | All QA |

### Scripts
| Script | Description |
|--------|-------------|
| [scripts/start-http-server.sh](./scripts/start-http-server.sh) | Start HTTP server (keeps running) |

## Source Documents

Original requirements in `initial_docs/`:
- `epic_information.md` - Epic requirements
- `conversation.md` - Internal testing feedback
- `Anaconda MCP-User Stories.pdf` - User stories

## Quick Links

| Task | Document |
|------|----------|
| **Quick Start** | [QUICK_START.md](./QUICK_START.md) |
| **Full Setup Guide** | [LOCAL_DEV_SETUP.md](./LOCAL_DEV_SETUP.md) |
| **E2E Tests (macOS)** | [TESTS_E2E_CLAUDE.md](./TESTS_E2E_CLAUDE.md) |
| **CLI Tests (All Platforms)** | [TESTS_CLI.md](./TESTS_CLI.md) |
| **Config Tests (All Platforms)** | [TESTS_CONFIG.md](./TESTS_CONFIG.md) |
| **Known Issues** | [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) |

## Test Flow Organization

```
TESTS_E2E_CLAUDE.md   → macOS only (requires Claude Desktop)
  ├── CORE-001: Full Tools Flow (run with STDIO and HTTP)
  ├── GUARD-001: Guardrails
  ├── AUTH-001: Anonymous Mode
  ├── AUTH-002: Authenticated Mode
  └── REGRESS-001: Known Issues

TESTS_CLI.md          → All platforms (manual first, then CI)
  ├── CLI-001: Server Discovery
  ├── CLI-002: Advanced Options
  ├── CLI-003: Config Management
  └── CLI-004: Regression CLI

TESTS_CONFIG.md       → All platforms (manual first, then CI)
  ├── ENV-001 to ENV-004: Environment variables
  ├── CFG-001 to CFG-003: Config file tests
  └── PATH-001 to PATH-002: OS path tests

TESTS_API_TOOLS.md    → Win365 manual first, then CI
  ├── TOOL-001 to TOOL-006: Each MCP tool
  └── ERR-001 to ERR-005: Error scenarios (tool + protocol)
```

## Conventions

- Test IDs: `{AREA}-{NUMBER}` (e.g., `CLI-001`, `ENV-002`)
- Preconditions: `[PRE]`
- Expected results: `[EXPECTED]`

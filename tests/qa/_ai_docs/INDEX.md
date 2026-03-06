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
| [TESTS_E2E.md](./TESTS_E2E.md) | E2E flows (Claude Desktop, Cursor, or Claude Code) | macOS, Windows |
| [TESTS_CLI.md](./TESTS_CLI.md) | CLI-only flows (automatable) | All platforms |
| [TESTS_CONFIG.md](./TESTS_CONFIG.md) | Configuration tests (automatable) | All platforms |
| [TESTS_API_TOOLS.md](./TESTS_API_TOOLS.md) | Direct API tool tests (automatable) | All platforms |

### Test Planning
| Document | Description | Audience |
|----------|-------------|----------|
| [COVERAGE_MAP.md](./COVERAGE_MAP.md) | Feature to test case mapping (all test files) | QA leads |
| [TEST_MATRIX.md](./TEST_MATRIX.md) | OS/Python/Transport matrix | QA leads |
| [TEST_PROGRESS.md](./TEST_PROGRESS.md) | Live run status, results, bugs and observations | All QA |
| [TEST_COVERAGE_ANALYSIS.md](./TEST_COVERAGE_ANALYSIS.md) | Existing pytest coverage analysis | QA leads |
| [OPEN_QUESTIONS.md](./OPEN_QUESTIONS.md) | Questions for product owner | QA leads, PO |

### Reference
| Document | Description | Audience |
|----------|-------------|----------|
| [TESTING_WORKFLOW.md](./TESTING_WORKFLOW.md) | Step-by-step workflow for QA participants | All QA |
| [QUICK_START.md](./QUICK_START.md) | Install, configure and verify setup | All QA |
| [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) | Known bugs and workarounds | All QA |
| [KI-011-HTTP-PROXY-HANG.md](./KI-011-HTTP-PROXY-HANG.md) | Root cause analysis and fix plan for the mcp-compose proxy hang on error responses (HTTP transport) | Developers, QA leads |
| [BUG-REPORT-KI011-MCP-COMPOSE-PROXY-HANG.md](./BUG-REPORT-KI011-MCP-COMPOSE-PROXY-HANG.md) | Concise bug report for filing against mcp-compose — steps to reproduce, observed behaviour, server logs, suggested fix | Developers |

### Scripts
| Script | Description |
|--------|-------------|
| [scripts/start-http-server.sh](./scripts/start-http-server.sh) | Start HTTP server (keeps running) |

## Test Projects

| Folder | Transport | Purpose | Needs pre-started server? |
|--------|-----------|---------|--------------------------|
| [`tests/qa/api_tools/`](../api_tools/README.md) | Streamable HTTP | Primary API regression suite; catches KI-011 hang | Yes (port 8888) |
| [`tests/qa/stdio_tools/`](../stdio_tools/README.md) | STDIO | Negative-control for KI-011; confirms hang is HTTP-specific | No — fixture self-manages |

## Source Documents

Original requirements in `initial_docs/`:
- `epic_information.md` - Epic requirements
- `conversation.md` - Internal testing feedback
- `Anaconda MCP-User Stories.pdf` - User stories

## Quick Links

| Task | Document |
|------|----------|
| **Quick Start** | [QUICK_START.md](./QUICK_START.md) |
| **Setup & Install** | [QUICK_START.md](./QUICK_START.md) |
| **Test Matrix** | [TEST_MATRIX.md](./TEST_MATRIX.md) |
| **Test Progress** | [TEST_PROGRESS.md](./TEST_PROGRESS.md) |
| **E2E Tests** | [TESTS_E2E.md](./TESTS_E2E.md) |
| **CLI Tests (All Platforms)** | [TESTS_CLI.md](./TESTS_CLI.md) |
| **Config Tests (All Platforms)** | [TESTS_CONFIG.md](./TESTS_CONFIG.md) |
| **API Tool Tests (All Platforms)** | [TESTS_API_TOOLS.md](./TESTS_API_TOOLS.md) |
| **Feature → Test Mapping** | [COVERAGE_MAP.md](./COVERAGE_MAP.md) |
| **Known Issues** | [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) |

## Conventions

- Test IDs: `{AREA}-{NUMBER}` (e.g., `CLI-001`, `ENV-002`)
- Preconditions: `[PRE]`
- Expected results: `[EXPECTED]`

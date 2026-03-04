# Anaconda MCP - QA Documentation Index

## Purpose
This documentation serves as the central knowledge base for QA testing of the Anaconda MCP server. Documents are structured for both manual QA testing and AI-assisted testing workflows.

## Document Structure

| Document | Description | Audience |
|----------|-------------|----------|
| [PRODUCT_OVERVIEW.md](./PRODUCT_OVERVIEW.md) | Product features, architecture, constraints | All QA |
| [FEATURE_TREE.md](./FEATURE_TREE.md) | 3-level feature tree with mermaid diagrams | All QA |
| [CONFIGURATION.md](./CONFIGURATION.md) | Configuration options, environment variables | All QA |
| [E2E_USER_FLOWS.md](./E2E_USER_FLOWS.md) | Real-world user scenarios and test flows | Manual/AI QA |
| [E2E_COVERAGE_MAP.md](./E2E_COVERAGE_MAP.md) | E2E to feature mapping, gaps, optimized flows | QA leads |
| [TEST_MATRIX.md](./TEST_MATRIX.md) | OS/Python/Transport pairwise test matrix | QA leads |
| [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) | Known bugs, quirks, and regression tests | All QA |
| [TEST_COVERAGE_ANALYSIS.md](./TEST_COVERAGE_ANALYSIS.md) | Current test coverage, gaps, priorities | QA leads |
| [LOCAL_DEV_SETUP.md](./LOCAL_DEV_SETUP.md) | Setting up local dev environment for testing | All QA |

## Source Documents

Original requirements and context in `initial_docs/`:
- `epic_information.md` - Epic requirements (reference only)
- `conversation.md` - Internal testing feedback and known issues
- `Anaconda MCP-User Stories.pdf` - User stories document

## Quick Links

- **Start Testing**: [LOCAL_DEV_SETUP.md](./LOCAL_DEV_SETUP.md)
- **Test Scenarios**: [E2E_USER_FLOWS.md](./E2E_USER_FLOWS.md)
- **Known Issues**: [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)
- **Test Matrix**: [TEST_MATRIX.md](./TEST_MATRIX.md)

## Conventions

- All test IDs follow format: `{AREA}-{TYPE}-{NUMBER}` (e.g., `AUTH-E2E-001`)
- Preconditions marked with `[PRE]`
- Expected results marked with `[EXPECTED]`
- AI-executable steps marked with `[AI]`

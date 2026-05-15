# Implementation Plan: Extend QA Tool Test Coverage

**Branch**: `001-extend-qa-tool-coverage` | **Date**: 2026-05-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-extend-qa-tool-coverage/spec.md`

## Summary

Extend QA-owned MCP tool tests to achieve 100% happy-path coverage across all 20 tools (environments-mcp: 6, conda-meta-mcp: 9, search-mcp: 5), implement programmatic OAuth authentication for CI workflows, and add authentication-state-aware test behavior that adapts based on logged-in vs logged-out state.

## Technical Context

**Language/Version**: Python 3.10+ (pyproject.toml: `requires-python = ">=3.10,<3.14"`)

**Primary Dependencies**: pytest, httpx, mcp-compose, anaconda-auth (for OAuth flow)

**Storage**: N/A (test infrastructure, no persistence)

**Testing**: pytest with pytest-asyncio, pytest-html for reports

**Target Platform**: Linux/macOS for CI (GitHub Actions), local development on macOS/Linux

**Project Type**: Test infrastructure extension (QA test suite)

**Performance Goals**: Test suite completes within CI job time limits; individual tool calls timeout at 60s (`TOOL_TIMEOUT`)

**Constraints**:
- Tests must be transport-agnostic (work across `http-http`, `stdio-http`, `stdio-stdio` profiles)
- Auth-required tests must skip gracefully when credentials unavailable
- No mocks: all tests use real integrations (local conda, public channels, anaconda.com API)

**Scale/Scope**: 20 tools across 3 MCP servers; ~35-40 new test methods

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. MCP Server Composition** | ✅ Pass | Tests verify tool contracts over defined interfaces; transport-agnostic design maintained |
| **II. Type Safety & Code Quality** | ✅ Pass | All test code will have type annotations; pre-commit hooks enforced |
| **III. QA-Owned Test Standards** | ✅ Pass | Tests follow existing patterns in `tests/qa/mcp_tools/`; documented in `_docs/test_design.md` |
| **IV. Observability & Error Handling** | ✅ Pass | Tests validate well-formed MCP responses; error scenarios verify `is_error=True` with meaningful messages |
| **PR Separation** | ✅ Pass | This is a QA-focused PR; no codebase changes |

**Gate Result**: PASS — No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-extend-qa-tool-coverage/
├── plan.md              # This file
├── research.md          # Phase 0: Auth service design, test patterns
├── data-model.md        # Phase 1: Test entity model, auth categories
├── quickstart.md        # Phase 1: Quick setup guide for running new tests
├── contracts/           # Phase 1: Auth service interface, test markers
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
tests/qa/mcp_tools/
├── conftest.py                          # Extended: auth fixtures, skip markers
├── common/
│   ├── constants/
│   │   └── mcp_tools.py                # Already complete: all 20 tools defined
│   └── utils/
│       ├── auth_service.py             # NEW: OAuth programmatic auth
│       └── response_validators.py      # Existing: may add auth validators
├── _docs/
│   └── test_design.md                  # Updated: coverage tables, auth section
│
# Existing test files (environments-mcp) - may need gap fixes:
├── test_create_environment_*.py
├── test_list_environment_packages.py
├── test_remove_*.py
│
# Existing test files (conda-meta-mcp) - already have coverage:
├── test_conda_meta_*.py                # 9 files, happy + some error paths
│
# Existing test files (search-mcp) - need auth-state handling:
├── test_search_*.py                    # 5 files, need auth-aware logic
```

**Structure Decision**: Extend existing `tests/qa/mcp_tools/` structure. No new directories needed except `contracts/` in the spec folder for design artifacts.

## Complexity Tracking

> No violations requiring justification. Structure follows established patterns.

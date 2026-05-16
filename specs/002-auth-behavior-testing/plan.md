# Implementation Plan: Auth Behavior Testing

**Branch**: `002-auth-behavior-testing` | **Date**: 2026-05-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-auth-behavior-testing/spec.md`

## Summary

Refactor QA test infrastructure to eliminate manual auth checks in test bodies (DRY principle) by introducing:
1. A `require_auth` fixture that auto-skips auth-required tests
2. Conditional assertion helpers for auth-enhanced tests
3. Clear auth state reporting in test output

This is a test infrastructure enhancement affecting `tests/qa/mcp_tools/` only.

## Technical Context

**Language/Version**: Python 3.13 (per workflow default, conda-meta-mcp requirement)

**Primary Dependencies**: pytest, httpx, mcp-compose (test infrastructure)

**Storage**: N/A (test suite, no data persistence)

**Testing**: pytest with custom fixtures and markers

**Target Platform**: macOS, Linux, Windows (CI runners)

**Project Type**: Test infrastructure enhancement (QA suite)

**Performance Goals**: Test suite completes within CI timeout limits (no change from current)

**Constraints**: Must not break existing tests, must maintain transport-agnostic design

**Scale/Scope**: ~25 test files, 3 MCP servers (environments-mcp, conda-meta-mcp, search-mcp)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Evidence |
|------|--------|----------|
| III. QA-Owned Test Standards | ✅ PASS | Follows established patterns in `tests/qa/mcp_tools/` |
| III. Transport Matrix Testing | ✅ PASS | Same assertions run for every profile |
| III. Test Infrastructure | ✅ PASS | Uses existing fixture scopes and marks |
| II. Type Safety | ✅ PASS | All new code will have type annotations |
| Git & PR Workflow - QA PRs focused | ✅ PASS | Targeted, single-purpose (auth behavior only) |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```text
specs/002-auth-behavior-testing/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (auth state model)
├── quickstart.md        # Phase 1 output
├── contracts/           # N/A (internal test infrastructure)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
tests/qa/mcp_tools/
├── conftest.py                    # Auth fixtures (require_auth, conditional assertions)
├── common/
│   ├── utils/
│   │   ├── auth_service.py        # Auth state detection (existing)
│   │   └── assertions.py          # NEW: Conditional assertion helpers
│   └── constants/
│       └── mcp_tools.py           # Tool auth categories
├── test_search_*.py               # Update to use require_auth fixture
└── _docs/
    └── auth_testing.md            # NEW: Auth behavior documentation
```

**Structure Decision**: Minimal changes to existing structure. New helpers in `common/utils/assertions.py`, fixture updates in `conftest.py`.

## Complexity Tracking

No violations requiring justification.

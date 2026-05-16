# Tasks: Auth Behavior Testing

**Input**: Design documents from `/specs/002-auth-behavior-testing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested - focusing on infrastructure changes only.

**Organization**: Tasks organized by user story to enable independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Test infrastructure**: `tests/qa/mcp_tools/`
- **Fixtures**: `tests/qa/mcp_tools/conftest.py`
- **Utils**: `tests/qa/mcp_tools/common/utils/`
- **Docs**: `tests/qa/mcp_tools/_docs/`

---

## Phase 1: Setup

**Purpose**: No setup needed - modifying existing infrastructure

*No tasks - existing project structure is sufficient*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add validator for auth error responses

**⚠️ CRITICAL**: User Story 1 tasks cannot begin until this validator exists

- [x] T001 Add `validate_auth_error_response` validator to tests/qa/mcp_tools/common/utils/response_validators.py

**Implementation details for T001**:
```python
def validate_auth_error_response(response: dict, context: str = "") -> None:
    """
    Assert that a tool returned a graceful authentication error.
    Checks isError=true and content contains auth-related message.
    """
```

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Dual-Mode Auth Test Execution (Priority: P1) 🎯 MVP

**Goal**: Tests validate BOTH auth states with conditional assertions (no skipping)

**Independent Test**: Run `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http -k search_environments` with and without `ANACONDA_AUTH_API_KEY`. Verify tests pass in both modes with appropriate assertions.

### Implementation for User Story 1

- [x] T002 [P] [US1] Update test_search_environments.py to use conditional assertions based on auth_state
- [x] T003 [P] [US1] Update test_search_collections_files.py to use conditional assertions based on auth_state

**Migration pattern for T002 and T003**:

Before (old skip approach - DO NOT USE):
```python
def test_search_environments_basic(self, call_tool, require_auth):
    # fixture skips if not authenticated
    # ... test code expecting success only
```

After (conditional assertions - IMPLEMENTED):
```python
def test_search_environments_basic(self, call_tool, auth_state: AuthState):
    response = call_tool(SearchTools.SEARCH_ENVIRONMENTS, {...})
    mcp_result = _extract_mcp_response(response)

    if auth_state.logged_in:
        # Authenticated: expect success with results
        validate_search_success(mcp_result, context="...")
        validate_search_has_content(mcp_result, context="...")
    else:
        # Unauthenticated: expect graceful auth error
        validate_auth_error_response(mcp_result, context="...")
```

**Checkpoint**: User Story 1 complete - auth-required tests validate both modes

---

## Phase 4: User Story 2 - Dual-Mode Test Suite Execution (Priority: P2)

**Goal**: Verify test suite works correctly in both authenticated and unauthenticated modes

**Independent Test**: Run full test suite twice (with/without API key) and verify all tests pass

### Implementation for User Story 2

- [x] T004 [US2] Verify test suite passes with ANACONDA_AUTH_API_KEY set (all tests pass)
- [x] T005 [US2] Verify test suite passes without ANACONDA_AUTH_API_KEY (all tests pass with different assertions)

**Verification commands**:
```bash
# Authenticated mode - all tests pass with success assertions
ANACONDA_AUTH_API_KEY=<key> pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http -v

# Unauthenticated mode - all tests pass (auth-required tests validate auth errors)
pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http -v
```

**Checkpoint**: User Story 2 complete - dual-mode execution verified

---

## Phase 5: User Story 3 - Clear Auth State Reporting (Priority: P2)

**Goal**: Ensure auth state is clearly visible in test output

**Independent Test**: Run tests and verify pytest header shows auth state

### Implementation for User Story 3

- [x] T006 [US3] Verify pytest header displays auth state on every run
- [x] T007 [US3] Verify HTML report metadata includes auth state

**Verification**: Already implemented in conftest.py via `pytest_report_header` and `pytest_sessionstart`

**Checkpoint**: User Story 3 complete - reporting verified

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and cleanup

- [x] T008 [P] Update auth testing documentation in tests/qa/mcp_tools/_docs/auth_testing.md
- [x] T009 Remove deprecated require_auth fixture from conftest.py

**Documentation content for T008**:
- Auth categories explanation (auth_independent, auth_required, auth_enhanced)
- How to use conditional assertions with auth_state fixture
- How to run tests in authenticated vs unauthenticated mode
- Troubleshooting common auth issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A - no setup needed
- **Foundational (Phase 2)**: T001 MUST complete before US1 tasks
- **User Story 1 (Phase 3)**: Depends on T001
- **User Story 2 (Phase 4)**: Depends on US1 completion (T002, T003)
- **User Story 3 (Phase 5)**: No dependencies (verification only)
- **Polish (Phase 6)**: Depends on all user stories

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (T001)
- **User Story 2 (P2)**: Depends on US1 (needs conditional assertion changes applied)
- **User Story 3 (P2)**: Independent (verification only)

### Within User Story 1

- T002 and T003 can run in parallel (different files)

### Parallel Opportunities

- T002 [P] and T003 [P] can run in parallel
- T006 and T007 can run in parallel (independent verification)
- T008 [P] can run in parallel with verification tasks

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001 (Foundational validator)
2. Complete T002, T003 (Update test files with conditional assertions)
3. **STOP and VALIDATE**: Run auth-required tests with/without API key
4. Merge if passing

### Incremental Delivery

1. T001 → Validator ready
2. T002, T003 → MVP complete (US1)
3. T004, T005 → Dual-mode verified (US2)
4. T006, T007 → Reporting verified (US3)
5. T008, T009 → Documentation and cleanup complete

---

## Notes

- Total tasks: 9
- Tasks per user story: US1=2, US2=2, US3=2, Foundational=1, Polish=2
- Migration scope: 3 tests in 2 files updated to conditional assertions
- No new test files needed - infrastructure enhancement only
- **Key change**: Tests do NOT skip when unauthenticated - they validate graceful auth error responses
- Success criteria from spec.md: FR-005 (tests validate auth error response, not skip)

# Research: Auth Behavior Testing

**Feature**: Auth Behavior Testing for MCP Tools
**Phase**: 0 - Research
**Date**: 2026-05-15

## Research Questions

### RQ-1: How to implement auto-skip fixture for auth-required tests?

**Decision**: Use `pytest.fixture` with `autouse=False` that calls `pytest.skip()` when not authenticated.

**Rationale**:
- pytest's fixture system allows injecting behavior before test execution
- Tests that need auth simply add `require_auth` to their fixture list
- Skip message is centralized, not duplicated in each test

**Implementation Pattern**:
```python
@pytest.fixture
def require_auth(auth_state: AuthState) -> None:
    """Skip test if not authenticated. Use as fixture dependency."""
    if not auth_state.logged_in:
        pytest.skip("Requires authentication - set ANACONDA_AUTH_API_KEY env var")
```

**Alternatives Considered**:
- Custom marker with hook: More complex, requires hook implementation
- Class-level skip decorator: Less granular, can't mix auth-required and auth-independent tests in same class

---

### RQ-2: How to implement conditional assertions for auth-enhanced tests?

**Decision**: Create assertion helper functions that accept `auth_state` and adjust behavior accordingly.

**Rationale**:
- Keeps test code clean and readable
- Single point of change for assertion logic
- Can evolve to check for private content when logged in

**Implementation Pattern**:
```python
def assert_search_results(
    response: dict,
    *,
    auth_state: AuthState,
    context: str,
    min_results: int = 1,
) -> None:
    """Assert search response is valid. Adjusts expectations based on auth state."""
    validate_search_success(response, context=context)
    validate_search_has_content(response, context=context)
    # Future: when logged in, could assert private results are present
```

**Alternatives Considered**:
- Separate test methods for each auth state: Violates DRY, doubles test count
- Parametrized tests with auth fixtures: Complex fixture dependencies

---

### RQ-3: Should auth-required tests validate error response or just skip?

**Decision**: Skip for now, with option to add error validation tests later.

**Rationale**:
- Primary goal is DRY test code, not adding new test scenarios
- Error validation is a separate test concern (testing the API, not the tool behavior)
- Skip provides clear signal that test requires auth without false failures

**Alternatives Considered**:
- Always validate auth error: Adds complexity, mixes concerns (tool behavior vs API error handling)
- Both skip and validate in same test: Confusing test intent

---

### RQ-4: Current manual skip pattern inventory

**Analysis of existing code**:

Files with manual `if not auth_state.logged_in: pytest.skip()`:
- `test_search_environments.py`: 2 occurrences (both test methods)
- `test_search_collections_files.py`: 2 occurrences (both test methods)

Files with no auth checks (auth-enhanced, run regardless):
- `test_search_packages.py`: Uses `@pytest.mark.auth_enhanced` but no skip logic
- `test_search_documentation.py`: Uses `@pytest.mark.auth_enhanced` but no skip logic
- `test_search_forum.py`: Uses `@pytest.mark.auth_enhanced` but no skip logic

Files with `@pytest.mark.auth_independent` (15+ files):
- All environments-mcp tests
- All conda-meta-mcp tests
- No auth checks needed or present

**Decision**: Migrate the 4 manual skip occurrences to use `require_auth` fixture.

---

### RQ-5: How to report auth state clearly?

**Decision**: Keep existing implementation (pytest header + HTML metadata), add skip reason standardization.

**Current implementation already provides**:
- `pytest_report_header`: Shows auth state at session start
- `pytest_sessionstart`: Adds auth state to HTML report metadata
- `detect_auth_state()`: Returns structured `AuthState` with `source` field

**Enhancement**: Standardize skip reason text to include actionable guidance.

---

## Summary of Decisions

| Question | Decision |
|----------|----------|
| Auto-skip fixture | `require_auth` fixture that calls `pytest.skip()` |
| Conditional assertions | Helper functions in `common/utils/assertions.py` |
| Auth error validation | Skip only (error validation is separate concern) |
| Migration scope | 4 manual skips in 2 files |
| Reporting | Keep existing, standardize skip message |

## Dependencies Identified

- None: All required infrastructure already exists in `conftest.py`

## Next Phase

Phase 1 will produce:
- `data-model.md`: AuthState model documentation
- `common/utils/assertions.py`: Conditional assertion helpers
- Updated `conftest.py`: `require_auth` fixture
- Updated test files: Use new fixtures

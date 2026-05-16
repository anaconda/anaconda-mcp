# Quickstart: Auth Behavior Testing

**Feature**: Auth Behavior Testing for MCP Tools
**Date**: 2026-05-15

## Overview

This feature refactors QA tests to handle authentication states in a DRY manner:
- Auth-required tests auto-skip via `require_auth` fixture
- Auth-enhanced tests use conditional assertions
- No manual `if not auth_state.logged_in: pytest.skip()` in test bodies

## Quick Implementation Guide

### 1. Add `require_auth` fixture to conftest.py

```python
@pytest.fixture
def require_auth(auth_state: AuthState) -> None:
    """Auto-skip test if not authenticated."""
    if not auth_state.logged_in:
        pytest.skip("Requires authentication - set ANACONDA_AUTH_API_KEY env var")
```

### 2. Update auth-required tests

Before:
```python
def test_search_environments_basic(self, call_tool, auth_state):
    if not auth_state.logged_in:
        pytest.skip("Requires authentication - set ANACONDA_USER_EMAIL/PASSWORD")
    # ... test code
```

After:
```python
def test_search_environments_basic(self, call_tool, require_auth):
    # No skip check needed - fixture handles it
    # ... test code
```

### 3. Files to modify

| File | Change |
|------|--------|
| `conftest.py` | Add `require_auth` fixture |
| `test_search_environments.py` | Replace manual skip with fixture |
| `test_search_collections_files.py` | Replace manual skip with fixture |

## Running Tests

### Authenticated mode (full coverage)
```bash
ANACONDA_AUTH_API_KEY=<your-key> pytest tests/qa/mcp_tools -o addopts=
```

### Unauthenticated mode (auth-required tests skipped)
```bash
pytest tests/qa/mcp_tools -o addopts=
```

## Verification

Check pytest output header shows auth state:
```
auth state: logged_in=True, source=env_credentials
```
or
```
auth state: logged_in=False, source=no_auth
```

## Success Criteria

- [ ] No `if not auth_state.logged_in: pytest.skip()` in test bodies
- [ ] `test_search_environments.py` uses `require_auth` fixture
- [ ] `test_search_collections_files.py` uses `require_auth` fixture
- [ ] Tests pass with and without `ANACONDA_AUTH_API_KEY`

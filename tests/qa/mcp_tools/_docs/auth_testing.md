# Authentication Testing Guide

This document describes how authentication is handled in MCP tool tests.

## Auth Categories

Tools are classified into three categories based on their authentication requirements:

| Category | Marker | Behavior |
|----------|--------|----------|
| **auth_independent** | `@pytest.mark.auth_independent` | Works identically with/without auth |
| **auth_required** | `@pytest.mark.auth_required` | Requires auth to return results |
| **auth_enhanced** | `@pytest.mark.auth_enhanced` | Works both ways, may return different results |

### Tool Classification

| Server | Tools | Category |
|--------|-------|----------|
| environments-mcp | All 6 tools | auth_independent |
| conda-meta-mcp | All 9 tools | auth_independent |
| search-mcp | `search_packages`, `search_documentation`, `search_forum` | auth_enhanced |
| search-mcp | `search_collections_and_files`, `search_environments` | auth_required |

## Using the `require_auth` Fixture

For auth-required tests, use the `require_auth` fixture instead of manual auth checks:

```python
# Before (manual check - DO NOT USE)
def test_feature(self, call_tool, auth_state):
    if not auth_state.logged_in:
        pytest.skip("Requires authentication")
    # ... test code

# After (use fixture - PREFERRED)
def test_feature(self, call_tool, require_auth):
    # No manual skip needed - fixture handles it
    # ... test code
```

The fixture automatically skips the test with a clear message when not authenticated.

## Running Tests

### Authenticated Mode (full coverage)

```bash
ANACONDA_AUTH_API_KEY=<your-key> pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http
```

### Unauthenticated Mode (auth-required tests skipped)

```bash
pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http
```

## Auth State Detection

Auth state is detected once at session start via `detect_auth_state()`:

1. Check `ANACONDA_AUTH_API_KEY` environment variable
2. If not found, run in unauthenticated mode

The auth state is displayed in:
- Pytest session header: `auth state: logged_in=True, source=env_credentials`
- HTML report metadata

## Troubleshooting

### Tests skipping unexpectedly

Check pytest output header for auth state:
```
auth state: logged_in=False, source=no_auth
```

If not authenticated when expected:
- Verify `ANACONDA_AUTH_API_KEY` is set: `echo $ANACONDA_AUTH_API_KEY`
- Check `.env` file exists at repo root with `ANACONDA_AUTH_API_KEY=<token>`

### Token errors

If you see "Token is invalid or expired":
- Generate a new API key from anaconda.com
- Update `ANACONDA_AUTH_API_KEY` in your environment or `.env`

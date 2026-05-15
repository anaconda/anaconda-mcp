# Contract: Authentication Service

**Date**: 2026-05-15

## Purpose

Define the interface for programmatic OAuth authentication used by search-mcp tests to obtain session tokens in CI environments.

## Interface

### AuthService Class

```python
class AuthService:
    """Programmatic OAuth authentication for Anaconda API."""

    def __init__(self, base_url: str = "https://api.anaconda.com") -> None:
        """Initialize auth service with API base URL."""

    def login(self, email: str, password: str) -> str:
        """
        Complete OAuth 2-step flow and return session token.

        Args:
            email: Anaconda account email
            password: Anaconda account password

        Returns:
            Session token string

        Raises:
            AuthError: If authentication fails
            httpx.HTTPStatusError: If API request fails
        """
```

### AuthState Dataclass

```python
@dataclass
class AuthState:
    """Test session authentication state."""

    logged_in: bool
    """True if authentication succeeded."""

    token: str | None = None
    """Session token if logged_in is True."""

    source: Literal["env_credentials", "keyring", "no_auth", "env_credentials_failed"] = "no_auth"
    """How the auth state was determined."""
```

### AuthError Exception

```python
class AuthError(Exception):
    """Authentication failed."""
    pass
```

## Pytest Fixtures

### `auth_state` (session-scoped)

```python
@pytest.fixture(scope="session")
def auth_state() -> AuthState:
    """
    Detect and return authentication state for the test session.

    Detection priority:
    1. Environment credentials (ANACONDA_USER_EMAIL + ANACONDA_USER_PASSWORD)
    2. Keyring token (from `anaconda login`)
    3. No authentication available

    Returns:
        AuthState with logged_in status and source information
    """
```

## Pytest Markers

### `@pytest.mark.auth_independent`

Tool works identically with or without authentication.

**Behavior**: Test runs normally in all auth states.

**Applied to**: All environments-mcp tests, all conda-meta-mcp tests.

### `@pytest.mark.auth_required`

Tool requires authentication to return meaningful results.

**Behavior**: Test skips with message when `auth_state.logged_in == False`.

**Applied to**: `search_collections_and_files`, `search_environments` tests.

### `@pytest.mark.auth_enhanced`

Tool works in both states but may return different results.

**Behavior**: Test runs in all auth states, asserts only on public data when logged out.

**Applied to**: `search_packages`, `search_documentation`, `search_forum` tests.

## Credential Sources

**Priority order**: `.env` file → GitHub secrets → keyring fallback

| Source | Location | Usage |
|--------|----------|-------|
| `.env` file | Repo root (in `.gitignore`) | Local development |
| GitHub secrets | Repository secrets | CI workflow |
| Keyring | System keychain via `anaconda login` | Fallback |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANACONDA_USER_EMAIL` | Test account email |
| `ANACONDA_USER_PASSWORD` | Test account password |

## Test Skip Pattern

```python
@pytest.mark.auth_required
class TestSearchEnvironments:
    def test_happy_path(self, call_tool, auth_state):
        if not auth_state.logged_in:
            pytest.skip(
                f"Requires authentication (source: {auth_state.source}). "
                "Set ANACONDA_USER_EMAIL and ANACONDA_USER_PASSWORD, "
                "or run `anaconda login`."
            )
        # ... test code
```

## CI Workflow Configuration

```yaml
# .github/workflows/qa-mcp-tools.yml
env:
  ANACONDA_USER_EMAIL: ${{ secrets.ANACONDA_USER_EMAIL }}
  ANACONDA_USER_PASSWORD: ${{ secrets.ANACONDA_USER_PASSWORD }}
```

## Test Output

When tests skip due to auth state:

```
SKIPPED [1] test_search_environments.py:15: Requires authentication (source: no_auth). Set ANACONDA_USER_EMAIL and ANACONDA_USER_PASSWORD, or run `anaconda login`.
```

Session summary includes auth state:

```
======= test session starts =======
Auth state: logged_in=True, source=env_credentials
...
```

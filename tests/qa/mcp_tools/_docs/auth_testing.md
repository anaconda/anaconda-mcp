# Authentication Testing Guide

This document describes how authentication is handled in MCP tool tests.

## Authentication Requirement

**anaconda-mcp requires authentication to function.** The server will not start without valid credentials. Users attempting to run without auth get a clear error:

```
RuntimeError: Not authenticated with Anaconda. Run 'anaconda-auth login' or sign in when prompted.
```

## Auth Categories

Tools are classified into categories based on their authentication behavior:

| Category | Marker | Behavior |
|----------|--------|----------|
| **auth_independent** | `@pytest.mark.auth_independent` | Works identically regardless of token scope |
| **auth_required** | `@pytest.mark.auth_required` | Requires specific token permissions |
| **auth_enhanced** | `@pytest.mark.auth_enhanced` | May return different results based on permissions |

### Tool Classification

| Server | Tools | Category |
|--------|-------|----------|
| environments-mcp | All 6 tools | auth_independent |
| conda-meta-mcp | All 9 tools | auth_independent |
| search-mcp | `search_packages`, `search_documentation`, `search_forum` | auth_enhanced |
| search-mcp | `search_collections_and_files`, `search_environments` | auth_required |

## Running Tests

Tests require `ANACONDA_AUTH_API_KEY` to be set:

```bash
ANACONDA_AUTH_API_KEY=<your-key> pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http
```

Or set it in `.env` file at repo root:
```
ANACONDA_AUTH_API_KEY=<your-key>
```

## Auth State Detection

Auth state is detected once at session start via `detect_auth_state()`:

1. Check `ANACONDA_AUTH_API_KEY` environment variable
2. If not found, tests report `logged_in=False`

For mcp-compose config generation, `_get_auth_token_for_tests()` also checks:
1. `ANACONDA_AUTH_API_KEY` environment variable
2. Keyring token from `anaconda login` (via `anaconda_auth`)

**Note:** The server itself (anaconda-mcp) has its own auth detection that includes
keyring fallback. If `ANACONDA_AUTH_API_KEY` is not set but you've run `anaconda login`,
the server may still start successfully.

The auth state is displayed in:
- Pytest session header: `auth state: logged_in=True, source=env_credentials`
- HTML report metadata

## Troubleshooting

### Server won't start

If you see:
```
RuntimeError: Not authenticated with Anaconda. Run 'anaconda-auth login' or sign in when prompted.
```

Solutions:
- Set `ANACONDA_AUTH_API_KEY` environment variable
- Run `anaconda login` to store token in keyring
- Add token to `.env` file at repo root

### Token errors

If you see "Token is invalid or expired":
- Generate a new API key from anaconda.com
- Update `ANACONDA_AUTH_API_KEY` in your environment or `.env`

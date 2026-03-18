# KI-027: API Key Authentication Does Not Work for MCP Channel Access

**Jira**: TBD (to be filed)

## Summary

API key authentication via `ANACONDA_AUTH_API_KEY` environment variable or `~/.anaconda/config.toml` does not grant access to private conda channels when using anaconda-mcp. The `anaconda-auth` plugin requires a repo token installed via `anaconda token install`, which in turn requires interactive login first.

**User scenario**: User sets API key in Claude Desktop config or `~/.anaconda/config.toml`, configures `.condarc` with private channels, but `conda_create_environment` fails with "Token not found for defaults".

## Status

| Field | Value |
|-------|-------|
| Severity | Medium |
| Component | anaconda-auth / anaconda-mcp |
| Type | Bug / Feature Gap |
| Affects | Users trying to use API key auth as alternative to interactive login |

## User-Visible Symptoms

1. User configures API key (env var or config file)
2. User configures `.condarc` with `default_channels` pointing to `repo.anaconda.cloud` and `channel_settings` with `anaconda-auth`
3. User asks Claude to create an environment
4. Error returned:
   ```
   Token not found for defaults. Please install token with `anaconda token install`.
   ```

## Root Cause

The `anaconda-auth` conda plugin distinguishes between two types of credentials:

| Credential | Purpose | How obtained |
|------------|---------|--------------|
| API key | Authenticates identity to Anaconda services | Generated at anaconda.cloud |
| Repo token | Grants access to private conda channels | `anaconda token install` (requires prior auth) |

When conda accesses `repo.anaconda.cloud`, the `anaconda-auth` plugin looks for a **repo token** (installed via `anaconda token install`), not the API key. The API key alone is insufficient for channel access.

### Why API Key Auth Was Expected to Work

The `anaconda-auth` documentation suggests that setting `ANACONDA_AUTH_API_KEY` should provide authentication. However:
1. `anaconda whoami` works with API key alone (shows username)
2. Conda channel access does NOT work with API key alone (requires repo token)

This creates a confusing UX where `anaconda whoami` succeeds but conda operations fail.

## Additional Issue: Environment Variable Not Passed to Subprocess

Even if API key auth were to work, there's a secondary issue:

1. `ANACONDA_AUTH_API_KEY` set in Claude Desktop config is available to `anaconda-mcp`
2. `anaconda-mcp` spawns `environments-mcp-server` as a subprocess via `mcp-compose`
3. The environment variable is NOT passed to the subprocess
4. `environments-mcp-server` calls conda, which calls `anaconda-auth`, which can't find the API key

## Error Details

```
Request:
{
  "environment_name": "core-001b-2",
  "packages": []
}

Response:
{
  "is_error": true,
  "error_description": "There was an error while creating the environment. Details: ('conda', 'Token not found for defaults. Please install token with `anaconda token install`.')",
  "tool_result": {}
}
```

## Workaround

**Currently, API key authentication is NOT a viable alternative to interactive login for MCP channel access.**

Use interactive login instead:

```bash
# Quit Claude Desktop (to free port 8000)
# Then:
anaconda login
anaconda token install
anaconda token config
# Restart Claude Desktop
```

## Proposed Resolution

### Option A: anaconda-auth should use API key for channel access
The `anaconda-auth` conda plugin should be able to use the API key (from env var or config file) to authenticate channel requests, not just identity requests.

### Option B: `anaconda token install` should work with API key auth
If the API key is set, `anaconda token install` should be able to fetch the repo token without requiring interactive login first.

### Option C: mcp-compose should pass environment variables to subprocesses
At minimum, `ANACONDA_AUTH_API_KEY` (and other auth-related env vars) should be passed from the parent process to spawned downstream MCP servers.

## Environment

- anaconda-mcp: 1.0.0.rc.2
- environments-mcp-server: 1.0.0.rc.2
- anaconda-auth: 0.13.1
- mcp-compose: 0.1.11
- OS: macOS (likely affects all platforms)

## Test Configuration

```yaml
# ~/.condarc
default_channels:
  - https://repo.anaconda.cloud/repo/main
  - https://repo.anaconda.cloud/repo/r
  - https://repo.anaconda.cloud/repo/msys2

channel_settings:
  - channel: https://repo.anaconda.cloud/*
    auth: anaconda-auth
```

```toml
# ~/.anaconda/config.toml
[plugin.auth]
api_key = "valid-api-key-from-anaconda-cloud"
```

## Related

- [KI-026/DESK-1411](../port_conflict/KI-026-port-8000-conflict-anaconda-login.md) — Port 8000 conflict that motivated API key auth workaround
- [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) — MCP subprocess doesn't pass credentials

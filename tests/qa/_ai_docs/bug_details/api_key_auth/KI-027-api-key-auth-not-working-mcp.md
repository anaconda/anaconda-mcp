# KI-027: `conda_create_environment` fails with "Token not found" when using API key authentication instead of interactive login

**Jira**: [DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413)

## Summary

User generates API key at anaconda.cloud, configures it in `~/.anaconda/config.toml`, sets up `.condarc` with private channels (`repo.anaconda.cloud`), and asks Claude Desktop to create an environment. Operation fails with "Token not found for defaults. Please install token with `anaconda token install`."

API key authentication is not a viable alternative to interactive login for MCP channel access.

## Status

| Field | Value |
|-------|-------|
| Severity | Medium |
| Component | anaconda-auth / anaconda-mcp |
| Type | Bug / Feature Gap |
| Affects | Users trying to use API key auth as alternative to interactive login |
| Discovered | 2026-03-17, during CORE-001b testing |
| Client | Claude Desktop |
| Transport | STDIO |

---

## User Flow (What Was Tested)

### Context

User cannot run `anaconda login` due to port 8000 conflict with running Claude Desktop ([KI-026/DESK-1411](../port_conflict/KI-026-port-8000-conflict-anaconda-login.md)). API key authentication was attempted as a workaround.

### Steps Performed

1. Generated API key at https://anaconda.cloud → Account Settings → API Keys

2. Configured API key in `~/.anaconda/config.toml`:
   ```toml
   [plugin.auth]
   api_key = "actual-api-key-value"
   ```

3. Configured `.condarc` with private channels:
   ```yaml
   channels:
     - defaults
   default_channels:
     - https://repo.anaconda.cloud/repo/main
     - https://repo.anaconda.cloud/repo/r
     - https://repo.anaconda.cloud/repo/msys2
   channel_settings:
     - channel: https://repo.anaconda.cloud/*
       auth: anaconda-auth
   ```

4. Verified `anaconda whoami` shows username (works)

5. Opened Claude Desktop and asked: "Create environment core-001b-2"

### Expected Result

Environment created successfully using private channels (`repo.anaconda.cloud`).

### Actual Result

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

---

## MCP Server Log

```
🚀 MCP Compose: anaconda-mcp
Conflict Resolution: ConflictResolutionStrategy.PREFIX
Log Level: INFO

ℹ️  No proxied servers configured. Running with built-in tools only.

Connecting to 1 Streamable HTTP server(s)...

  • conda
    URL: http://localhost:4041/mcp
    Auto-starting: /opt/miniconda3/envs/anaconda-mcp-rc2-c111-py313/bin/python -m environments_mcp_server start --transport streamable-http --port 4041
    Process started (PID: 16076)

...

✓ Unified MCP server is ready!
  Total tools: 6

Running in STDIO mode - awaiting JSON-RPC messages on stdin...

2026-03-18T02:01:17.179Z [anaconda-mcp] [info] Message from server:
{"jsonrpc":"2.0","id":5,"result":{"content":[{"type":"text","text":
"{\"is_error\":true,\"error_description\":\"There was an error while creating the environment.
Details: ('conda', 'Token not found for defaults. Please install token with `anaconda token install`.')\",\"tool_result\":{}}"}],"isError":false}}
```

---

## Root Cause Analysis

### Issue 1: API Key vs Repo Token

The `anaconda-auth` plugin distinguishes between two types of credentials:

| Credential | Purpose | How obtained |
|------------|---------|--------------|
| API key | Authenticates identity | Generated at anaconda.cloud |
| Repo token | Grants channel access | `anaconda token install` |

When conda accesses `repo.anaconda.cloud`, the `anaconda-auth` plugin looks for a **repo token**, not the API key. The API key alone is insufficient for channel access.

### Issue 2: Environment Variable Not Passed to Subprocess

Even if API key auth were to work via env var, there's a secondary issue:

```
Claude Desktop
    └── anaconda-mcp (has ANACONDA_AUTH_API_KEY)
            └── spawns → environments-mcp-server (does NOT inherit env var)
                              └── calls → conda → anaconda-auth (can't find API key)
```

The `mcp-compose` framework does not pass environment variables from the parent process to spawned downstream MCP servers.

---

## Workaround

**API key authentication is NOT a viable alternative to interactive login for MCP channel access.**

Use interactive login instead:

```bash
# Quit Claude Desktop (to free port 8000 — see KI-026)
# Then:
anaconda login
anaconda token install
anaconda token config
# Restart Claude Desktop
```

---

## Proposed Resolution

### Option A: anaconda-auth should use API key for channel access
The `anaconda-auth` conda plugin should be able to use the API key (from env var or config file) to authenticate channel requests, not just identity requests.

### Option B: `anaconda token install` should work with API key auth
If the API key is set, `anaconda token install` should be able to fetch the repo token without requiring interactive login first.

### Option C: mcp-compose should pass environment variables to subprocesses
At minimum, `ANACONDA_AUTH_API_KEY` (and other auth-related env vars) should be passed from the parent process to spawned downstream MCP servers.

---

## Environment

| Component | Version |
|-----------|---------|
| anaconda-mcp | 1.0.0.rc.2 |
| environments-mcp-server | 1.0.0.rc.2 |
| anaconda-auth | 0.13.1 |
| mcp-compose | 0.1.11 |
| Python | 3.13 |
| OS | macOS |

---

## Related

- [KI-026/DESK-1411](../port_conflict/KI-026-port-8000-conflict-anaconda-login.md) — Port 8000 conflict that motivated API key auth workaround
- [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) — MCP subprocess doesn't pass credentials
- [CORE-001b](../../tests/e2e/CORE-001b.md) — Test case blocked by this issue

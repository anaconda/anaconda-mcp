# KI-027: `conda_create_environment` fails with "Token not found" when using API key authentication instead of interactive login

**Jira**: [DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413)

## Summary

User generates API key at anaconda.cloud, configures it in `~/.anaconda/config.toml`, sets up `.condarc` with private channels (`repo.anaconda.cloud`), and asks Claude Desktop to create an environment. Operation fails with "Token not found for defaults. Please install token with `anaconda token install`."

**Resolution**: This is **by design**, not a bug. API key authentication is architecturally incapable of replacing the interactive login flow for conda channel access.

## Status

| Field | Value |
|-------|-------|
| Status | **Closed: No Action / By Design** |
| Severity | Lowest (not a bug) |
| Component | anaconda-auth / anaconda-mcp |
| Type | By Design |
| Affects | Users trying to use API key auth as alternative to interactive login |
| Discovered | 2026-03-17, during CORE-001b testing |
| Resolved | 2026-03-18 |
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

## Why API Key Authentication Cannot Work — By Design

There are **three independent failure points**, any one of which alone would block the API key path from working.

### Failure 1: `anaconda token install` requires OAuth browser session

This is the earliest and most fundamental break in the chain. The user flow assumes:
- Set API key in `~/.anaconda/config.toml` or via `ANACONDA_AUTH_API_KEY`
- `anaconda whoami` reports a valid user ✅
- Therefore "I am logged in" and can run `anaconda token install`

But `anaconda whoami` and `anaconda token install` have **different authentication requirements**. The API key satisfies identity verification (`whoami`), but `anaconda token install` requires an active **OAuth browser session** to fetch a repo token from the server. The API key alone cannot initiate or complete that OAuth exchange.

### Failure 2: API key ≠ repo token

The `anaconda-auth` plugin maintains a hard distinction between two credential types:

| Credential | Purpose | How obtained | Works for |
|------------|---------|--------------|-----------|
| **API key** | Authenticates identity | Generated at anaconda.cloud UI | `anaconda whoami`, API calls |
| **Repo token** | Grants conda channel access | `anaconda token install` (OAuth required) | conda operations against `repo.anaconda.cloud` |

When conda accesses `repo.anaconda.cloud`, the `anaconda-auth` plugin specifically looks for a **repo token**. The API key is not checked and cannot substitute.

### Failure 3: Environment variable not forwarded (MCP-specific)

Even setting aside failures 1 and 2, `mcp-compose` does not pass environment variables from the parent `anaconda-mcp` process to the spawned `environments-mcp-server` subprocess:

```
Claude Desktop
    └── anaconda-mcp (has ANACONDA_AUTH_API_KEY)
            └── spawns → environments-mcp-server (does NOT inherit env var)
                              └── calls → conda → anaconda-auth (can't find API key)
```

---

## Documentation Reference

The Anaconda docs recommend interactive login as the user-facing flow:

1. **[Tokens — primary user onboarding page](https://docs.anaconda.com/psm-cloud/tokens/)**: Explicitly states "If you are issuing a token for the first time or need to issue a new token, use the anaconda-auth CLI method" — the interactive browser flow.

2. **[anaconda-auth command reference](https://www.anaconda.com/docs/anaconda-platform/cloud/admin/anaconda-auth-reference)**: The only page where `ANACONDA_AUTH_API_KEY` appears. It is filed under **Admin guides**, and scoped to "automated workflow environments" (CI/CD, Docker) — with the prerequisite that `anaconda token install` was already run interactively first.

---

## The Only Supported Flow

```bash
# 1. Quit Claude Desktop (frees port 8000 — see KI-026)
# 2. Interactive login
anaconda login
anaconda token install
anaconda token config
# 3. Restart Claude Desktop
```

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
- [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) — MCP subprocess doesn't pass credentials (separate issue, now fixed)

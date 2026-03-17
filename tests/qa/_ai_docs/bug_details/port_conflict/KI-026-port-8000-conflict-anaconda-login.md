# KI-026: Cannot run `anaconda login` while Claude Desktop with anaconda-mcp is running (port 8000 conflict)

## Summary

User cannot login to Anaconda from command line while Claude Desktop with anaconda-mcp is running. Both anaconda-mcp (via mcp-compose) and `anaconda login` OAuth flow require port 8000, causing "Address already in use" error.

**User scenario**: User has Claude Desktop running with anaconda-mcp. User opens terminal and runs `anaconda login` to authenticate. Login fails with `OSError: [Errno 48] Address already in use`.

## Status

| Field | Value |
|-------|-------|
| Severity | Medium |
| Component | anaconda-mcp / mcp-compose |
| Type | Bug (with feature request for resolution) |
| Affects | All users running Claude Desktop with anaconda-mcp |

## User-Visible Symptoms

1. User has Claude Desktop running with anaconda-mcp configured
2. User opens terminal
3. User runs `anaconda login`
4. Error appears:
   ```
   OSError: [Errno 48] Address already in use
   ```
5. User cannot authenticate to Anaconda without closing Claude Desktop

## Root Cause

**Port 8000 conflict:**

| Component | Uses Port 8000 For |
|-----------|-------------------|
| mcp-compose (anaconda-mcp) | Upstream HTTP server for MCP protocol |
| anaconda-auth (`anaconda login`) | OAuth redirect callback (`http://127.0.0.1:8000/auth/oidc`) |

Both components hardcode port 8000, making them mutually exclusive.

## Error Details

```
anaconda login
OSError: [Errno 48] Address already in use

Traceback shows:
- anaconda_auth/handlers.py:147 in capture_auth_code
- AuthCodeRedirectServer tries to bind to ('127.0.0.1', 8000)
- Port already in use by mcp-compose
```

## Workarounds

### Option 1: Quit Claude Desktop temporarily
```bash
# Quit Claude Desktop
# Then login
anaconda login
# Restart Claude Desktop after login completes
```

### Option 2: Login before starting Claude Desktop
Authenticate first, then start Claude Desktop.

### Option 3: Use API key instead of interactive login
```bash
# Set in environment
export ANACONDA_AUTH_API_KEY="your-api-key"

# Or in config file ~/.anaconda/config.toml
[plugin.auth]
api_key = "your-api-key"
```

## Proposed Resolution (Feature Request)

**Option A: Make mcp-compose port configurable**
- Allow users to configure upstream HTTP port in mcp-compose settings
- Default could remain 8000, but allow override (e.g., 8001)

**Option B: Make anaconda-auth redirect port configurable**
- Allow `anaconda login --port 8001` or similar
- Or use dynamic port allocation

**Option C: Change mcp-compose default port**
- Use a different default port (e.g., 8080, 9000) to avoid common conflicts

**Recommended**: Option A or C - change mcp-compose since it's the newer component and anaconda-auth port 8000 is established in OAuth configurations.

## Environment

- anaconda-mcp: 1.26.0
- mcp-compose: 0.1.11
- anaconda-auth: 0.13.1
- OS: macOS (likely affects all platforms)

## Related

- Port 8000 is also used by many development servers (Django, FastAPI default, etc.)
- This conflict may affect other tools that use port 8000

## Evidence

```
(anaconda-mcp-rc2-c111-py313) $ anaconda login
OSError: [Errno 48] Address already in use

$ lsof -i :8000
COMMAND   PID       USER   FD   TYPE  NODE NAME
python3.1 1352 iiliukhina  8u  IPv4  TCP localhost:8000 (LISTEN)
```

The python process is mcp-compose spawned by Claude Desktop.

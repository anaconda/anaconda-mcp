# Documentation Feedback for PR #898

**PR**: [anaconda/documentation#898](https://github.com/anaconda/documentation/pull/898)
**Title**: DRAFT: Adds Anaconda MCP Server CLI reference and Claude integration docs
**Source**: QA Testing Findings
**Date**: 2026-03-18

---

## Summary

QA testing identified four items not covered in the current documentation that may cause user confusion.

| # | Item | Severity | Related JIRA |
|---|------|----------|--------------|
| 1 | Boolean env var parsing behavior | Medium | [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) |
| 2 | ~~Claude Desktop startup timing issue~~ | ~~High~~ | [DESK-1408](https://anaconda.atlassian.net/browse/DESK-1408) — **Closed** (Claude Desktop update fixed it) |
| 3 | Port default inconsistency (CLI 8000 vs config 2391) | Medium | — |
| 4 | Port 8000 conflict with `anaconda login` (due to #3) | Medium | [DESK-1411](https://anaconda.atlassian.net/browse/DESK-1411) |
| 5 | Private/internal channel access setup not documented | High | [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) |

---

## 1. Boolean Environment Variable Parsing Behavior

**Env var**: `ENVIRONMENTS_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS`

### What We Know

Setting this environment variable to `"false"` does **not** disable the feature. The string `"false"` is evaluated as truthy in Python (`bool("false") → True`).

Standard Python string-to-boolean behavior:
```python
bool("false") # → True  (non-empty string)
bool("0")     # → True  (non-empty string)
bool("")      # → False (empty string)
```

**Note**: If Pydantic Settings is properly configured with `bool` type, `"0"` and `"false"` *should* be recognized as falsy. The observed behavior suggests either the field isn't typed as `bool` or custom parsing bypasses Pydantic's smart boolean handling. Needs verification whether `"0"` works.

### User Impact

Users who set `ENVIRONMENTS_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS=false` expecting to explicitly disable channel override will find the feature remains enabled.

### How to Avoid

Omit the environment variable entirely to keep the feature disabled (default behavior).

---

## ~~2. Claude Desktop Startup Timing Issue~~ — RESOLVED

> **Status**: Closed (2026-03-19) — Claude Desktop was updated and the bug is no longer reproducible. No `--delay 15` workaround is needed.

~~**Affects**: Claude Desktop v1.1.6679+ on macOS~~

<details>
<summary>Historical details (no longer applicable)</summary>

After Claude Desktop updated to v1.1.6679, a timing/race condition caused the MCP server to enter a launch/kill loop. The server completed handshake and registered all 6 tools, but Claude Desktop killed and restarted it before the internal HTTP server (port 4041) stabilized.

This matched known Anthropic issues:
- [#22299](https://github.com/anthropics/claude-code/issues/22299)
- [#31864](https://github.com/anthropics/claude-code/issues/31864)

**Former workaround** (no longer needed): Add `--delay 15` to the server startup args.

</details>

---

## 3. Port Default Inconsistency

### What We Know

The default port differs depending on where you look:

| Source | Default Port |
|--------|--------------|
| CLI (`anaconda-mcp serve`) | 8000 |
| Config file (`mcp_compose.toml.template`) | 2391 |
| Docs example ([`getting-started.mdx`](https://github.com/anaconda/documentation/blob/DESK-1175/cli-reference/anaconda-mcp/1.0.0/getting-started.mdx)) | 8000 |

CLI default (8000) takes precedence over config file (2391).

### User Impact

Port 8000 conflicts with `anaconda login` (which also uses port 8000 for OAuth). Users running `anaconda-mcp serve` cannot login to Anaconda without stopping the server first.

### Recommendation

Align all defaults to the same port (suggest 2391 to avoid conflict with `anaconda login`).

---

## 4. Port 8000 Conflict with `anaconda login`

### What We Know

**Root cause identified**: CLI default `--port 8000` overrides config file default `port = 2391` (see Item #3).

**Conflict components**:
| Component | Port 8000 Usage |
|-----------|-----------------|
| `anaconda-mcp serve` (CLI default) | MCP composer endpoint |
| `anaconda login` (anaconda-auth) | OAuth redirect callback (`http://127.0.0.1:8000/auth/oidc`) |

When user runs `anaconda-mcp serve` without explicit `--port`, CLI default **8000** is used (not config's 2391), causing conflict with `anaconda login`.

**Error observed**:
```
$ anaconda login
OSError: [Errno 48] Address already in use
```

**Port verification**:
```
$ lsof -i :8000
COMMAND   PID  USER   FD   TYPE  NODE NAME
python3.1 1352 user   8u  IPv4  TCP localhost:8000 (LISTEN)
```

### User Impact

Users running `anaconda-mcp serve` (default invocation) cannot run `anaconda login` while Claude Desktop is running. This blocks:
- Initial login for new users
- Token refresh when session expires
- Switching between Anaconda accounts

### How to Avoid

**Option 1**: Explicitly set port to avoid 8000
```bash
anaconda-mcp serve --port 2391
```

**Option 2**: Quit Claude Desktop temporarily
1. Quit Claude Desktop completely (not just close window)
2. Run `anaconda login`
3. Restart Claude Desktop after authentication completes

**Option 3**: Login before starting Claude Desktop
Authenticate first, then launch Claude Desktop.

### Recommendation

Change CLI default from 8000 to 2391 to match config file default and avoid conflict with `anaconda login`.

---

## 5. Private/Internal Channel Access Setup Not Documented

### What We Know

PR #898 mentions "channel configurations" and `ENVIRONMENTS_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS` env var, but does **not** document how to access private/internal channels on `repo.anaconda.cloud`.

**What users expect**: "I ran `anaconda login`, now I can use MCP to create environments from private channels."

**Reality**: Login alone is insufficient. Full setup requires:

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `anaconda login` | Authenticates user identity |
| 2 | `anaconda token install` | Installs repo token for channel access |
| 3 | `anaconda token config` | Sets `default_channels` → `repo.anaconda.cloud` |
| 4 | Manual `.condarc` edit | Bug: step 3 often doesn't set `channel_settings` |
| 5 | Restart Claude Desktop | MCP server reads `.condarc` at startup only |

**Required `.condarc` configuration** (after steps 1-3):
```yaml
default_channels:
  - https://repo.anaconda.cloud/repo/main
  - https://repo.anaconda.cloud/repo/r
  - https://repo.anaconda.cloud/repo/msys2

channel_settings:
  - channel: https://repo.anaconda.cloud/*
    auth: anaconda-auth
```

**Note**: PR mentions "When Anaconda MCP Server starts, it will open a browser window to Anaconda's login page. However, authentication is not required to use Anaconda MCP Server." — this is misleading because:
1. Login IS required for private channels
2. Login alone is not enough (token install/config also needed)

### User Impact

Users attempting to create environments or install packages from private/internal channels will get:
- HTTP 403 Forbidden errors
- "Authentication required" errors
- Confusion because they already ran `anaconda login`

### Recommendation

Add a section documenting private channel access setup, including:
1. When it's needed (accessing `repo.anaconda.cloud` instead of public `repo.anaconda.com`)
2. Full setup steps (`login` + `token install` + `token config` + manual `channel_settings`)
3. Known bug: `anaconda token config` may not set `channel_settings` automatically
4. Requirement to restart Claude Desktop after config changes

---

## References

| Issue ID | JIRA | Description |
|----------|------|-------------|
| KI-022 | [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) | Boolean env var parsing |
| ~~KI-023~~ | [DESK-1408](https://anaconda.atlassian.net/browse/DESK-1408) | ~~Claude Desktop launch/kill loop~~ — **Closed** |
| KI-026 | [DESK-1411](https://anaconda.atlassian.net/browse/DESK-1411) | Port 8000 conflict with `anaconda login` |
| — | — | CLI vs config port default inconsistency (root cause of KI-026) |
| KI-020 | [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401) | MCP returns 403 despite valid auth (credentials not passed to subprocess) |

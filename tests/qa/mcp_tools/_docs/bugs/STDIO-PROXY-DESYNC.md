# mcp-compose STDIO Proxy Response Desync Bug

**Status**: Open (workaround available)
**Severity**: High
**Component**: mcp-compose
**Related**: DESK-1409

## Summary

mcp-compose STDIO proxy has a response desync bug when multiple STDIO servers are configured or under concurrent requests. Responses from downstream servers get mismatched to requests.

## Observed Errors

Primary error pattern observed in CI (GitHub Actions run 25952789005):

### "No response from tool execution"

Tool is recognized but response never arrives:

```
{'content': [{'text': 'Error executing tool conda-meta_cli_help: No response from tool execution', 'type': 'text'}], 'isError': True}
```

This error affects all servers when using multi-server STDIO config:
- `conda-meta_*` tools (all 9 tools fail)
- `conda_*` tools (environments-mcp - fails when other STDIO servers are configured)
- `search_*` tools (when configured)

All errors occur for tools that work correctly via `stdio-http` profile.

## Root Cause

The original STDIO proxy in `mcp_compose/tool_proxy.py`:

1. **Hardcoded request IDs** (1, 2, "tool-call") instead of unique IDs per request
2. **No response ID matching** - just reads "next line" from stdout
3. **No locking** for concurrent access
4. **Low timeout** (5s default)

If the downstream server outputs anything unexpected (logs, notifications, delayed responses), responses get mismatched to requests.

## Affected Configurations

| Profile | Status |
|---------|--------|
| `stdio-http` | Works (HTTP upstream avoids the bug) |
| `http-http` | Works |
| `stdio-stdio` | **Affected** - STDIO upstream triggers desync |

## Proposed Fix

PR: https://github.com/j-iliukhina-anaconda/mcp-compose/pull/1

Changes to `mcp_compose/tool_proxy.py`:

1. **Unique request IDs**: Incrementing counter per process instead of hardcoded IDs
2. **Request serialization**: Lock per process to prevent concurrent request/response interleaving
3. **Response ID matching**: Loop and read responses until finding one with matching ID, skipping non-JSON output and notifications
4. **Increased timeout**: 30s default instead of 5s

## Workaround

Use `stdio-http` profile instead of `stdio-stdio`:

```bash
pytest tests/qa/mcp_tools -o addopts= \
  --mcp-profile=stdio-http \
  --server-conda-env anaconda-mcp-server
```

The `stdio-http` profile uses HTTP for the upstream connection (mcp-compose → downstream servers), avoiding the STDIO desync bug while still using STDIO for the client edge (test → mcp-compose).

## Test Impact

Until the fix is merged upstream:

- `stdio-stdio` profile produces consistent failures for conda-meta-mcp tools (14 of 14 tests fail)
- environments-mcp tools work (single server, simpler traffic pattern)
- search-mcp may also fail (shares the STDIO proxy issue)
- CI should use `stdio-http` as the default profile

### Observed Failure Rate (stdio-stdio with multi-server config)

| Server | Tests | Passed | Failed | Notes |
|--------|-------|--------|--------|-------|
| environments-mcp | 6 | 6 | 0 | Works (original single-server config) |
| conda-meta-mcp | 9 | 0 | 9 | All fail with "No response from tool execution" |
| search-mcp | 5 | 0 | 5 | All fail with same error |

### Config Status

The multi-server config for `stdio-stdio` is implemented in `mcp_compose_profiles.py` for debugging purposes but should not be used in CI until the upstream bug is fixed. The config adds conda-meta-mcp (STDIO) and search-mcp (streamable-http, remote) to the existing environments-mcp (STDIO) server.

## References

- DESK-1409: Original hang investigation that led to STDIO proxy adoption
- https://github.com/j-iliukhina-anaconda/mcp-compose/pull/1: Proposed fix
- https://github.com/anaconda/anaconda-mcp/pull/23: Config change to use STDIO transport

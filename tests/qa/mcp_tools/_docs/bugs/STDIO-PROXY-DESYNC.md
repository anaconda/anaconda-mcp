# mcp-compose STDIO Proxy Response Desync Bug

**Status**: Open (workaround available)
**Severity**: High
**Component**: mcp-compose
**Related**: DESK-1409

## Summary

mcp-compose STDIO proxy has a response desync bug when multiple STDIO servers are configured or under concurrent requests. Responses from downstream servers get mismatched to requests, causing "Unknown tool" errors or incorrect responses.

## Symptoms

```
{'content': [{'text': 'Unknown tool: conda-meta_cache_maintenance', 'type': 'text'}], 'isError': True}
```

The tool exists and works fine via `stdio-http` profile, but fails via `stdio-stdio`.

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

- `stdio-stdio` profile may produce intermittent failures for conda-meta-mcp and search-mcp tools
- environments-mcp tools may work (single server, simpler traffic pattern)
- CI should use `stdio-http` as the default profile

## References

- DESK-1409: Original hang investigation that led to STDIO proxy adoption
- https://github.com/j-iliukhina-anaconda/mcp-compose/pull/1: Proposed fix
- https://github.com/anaconda/anaconda-mcp/pull/23: Config change to use STDIO transport

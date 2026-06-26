# Code Organization for Native FastMCP Composition

This document maps the runtime path for `anaconda mcp serve`. The server is composed in Python code and run over stdio; there is no generated runtime config file in the serve path.

## Module Structure

```text
src/anaconda_mcp/
├── app.py                         # Typer integration for `anaconda mcp`
├── cli.py                         # Click commands and serve startup
│   └── serve()                    # Validates auth/TOS, emits telemetry, runs stdio
│
├── composition.py                 # Native FastMCP composition
│   ├── PlatformMiddleware         # Auth, Terms, and telemetry enforcement
│   ├── _DynamicBearerAuth         # Supplies bearer auth for proxied search
│   └── build_composed_server()    # Mounts conda and registers search proxy
│
├── conda_mcp_lite/
│   ├── __init__.py
│   └── server.py                  # Vendored conda FastMCP server/tools
│
├── auth.py                        # Token retrieval and validation
├── terms.py                       # Terms acceptance checks and persistence
├── telemetry.py                   # Event names and telemetry helpers
├── client_config.py               # General stdio client config generation
└── claude_desktop.py              # Claude Desktop stdio config helpers
```

## Serve Data Flow

```text
1. User or MCP client launches `anaconda mcp serve`
   ↓
2. cli.serve() validates authentication and Terms acceptance
   ↓
3. cli.serve() emits startup/login telemetry and installs shutdown handlers
   ↓
4. cli.serve() calls composition.build_composed_server()
   ↓
5. build_composed_server():
   - creates the top-level FastMCP server
   - installs PlatformMiddleware
   - mounts the vendored conda FastMCP server in-process
   - creates an authenticated proxy for the remote search MCP
   ↓
6. cli.serve() runs the composed server with stdio transport
   ↓
7. The MCP client calls conda_* and search_* tools in one stdio session
```

## Native Composition Responsibilities

### `composition.py`

- Owns the runtime server graph for `serve`.
- Mounts `anaconda_mcp.conda_mcp_lite.server` directly into the top-level FastMCP app.
- Creates the remote search proxy with bearer auth.
- Installs `PlatformMiddleware` so all tool calls share auth, Terms, and telemetry behavior.

### `cli.py`

- Owns command-line startup and user-facing errors.
- Treats deprecated config/host/port inputs as ignored for `serve`.
- Validates login and Terms before starting the stdio server.
- Calls `build_composed_server().run(transport="stdio")`.

### `client_config.py` and `claude_desktop.py`

- Generate stdio client config entries.
- Point clients at the Python executable or CLI command that can run Anaconda MCP.
- Do not configure a host, port, or separate server transport for `serve`.

## Environment Variables

Runtime configuration is handled through environment variables and persisted Anaconda auth state:

| Variable | Purpose |
|----------|---------|
| `CONDA_EXE` | Explicit conda executable path for GUI clients |
| `ANACONDA_AUTH_API_KEY` | API-key authentication when keyring login is unavailable |
| `ANACONDA_MCP_ACCEPTED_TERMS` | Headless Terms acceptance flag |
| `ANACONDA_MCP_ACCEPTED_TERMS_VERSION` | Accepted Terms version |

## Related Documentation

- [Architecture](./ARCHITECTURE.md)
- [Configuration Guide](./CONFIGURATION_GUIDE.md)
- [CLI User Guide](./CLI_USER_GUIDE.md)

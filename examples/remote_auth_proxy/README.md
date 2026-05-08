# Remote Auth Proxy Proof-of-Concept

Demonstrates that `anaconda-mcp` can forward the user's Anaconda authentication
token to a remote proxied MCP server via the `Authorization: Bearer` header —
with zero manual configuration from the user.

## How It Works

1. `anaconda-mcp serve` retrieves the token from keyring (via `anaconda-auth`)
2. Sets `ANACONDA_API_KEY` in the process environment automatically
3. mcp-compose resolves `${ANACONDA_API_KEY}` in the TOML config
4. Every request to the proxied server includes `Authorization: Bearer <token>`
5. The echo server reads that header and returns it as the tool response

This proves the pattern works for remote MCP servers deployed to anaconda.com
that need to authenticate the calling user.

## Architecture

```
┌──────────────┐      stdio       ┌─────────────────────────┐
│  MCP Client  │ ◄──────────────► │     anaconda-mcp        │
│  (Inspector) │                  │                         │
└──────────────┘                  │  1. Reads token from    │
                                  │     keyring             │
                                  │  2. Sets ANACONDA_API_KEY│
                                  │  3. mcp-compose resolves │
                                  │     ${ANACONDA_API_KEY}  │
                                  └────────────┬────────────┘
                                               │
                                               │ HTTP + Authorization: Bearer <token>
                                               ▼
                                  ┌─────────────────────────┐
                                  │   Echo Auth Server      │
                                  │   (localhost:9999)       │
                                  │                         │
                                  │   Reads Authorization   │
                                  │   header and returns it │
                                  └─────────────────────────┘
```

## Quick Start

### Prerequisites

- Logged in via `anaconda login` (token stored in keyring)
- `anaconda-mcp` installed in the current environment

### Option A: MCP Inspector (recommended)

```bash
npx @modelcontextprotocol/inspector -- anaconda-mcp serve \
  --config examples/remote_auth_proxy/mcp_compose.toml
```

In the Inspector UI:
1. Connect to the server
2. Call the tool `auth_echo_echo_auth_token`
3. You should see your Anaconda API key echoed back as `Bearer ana-...`

### Option B: Manual (two terminals)

```bash
# Terminal 1: Start the echo server directly
python examples/remote_auth_proxy/echo_auth_server.py

# Terminal 2: Start anaconda-mcp in stdio mode
anaconda-mcp serve --config examples/remote_auth_proxy/mcp_compose.toml
```

### Option C: Auto-start (single terminal)

The `mcp_compose.toml` has `auto_start = true`, so the echo server will be
started automatically by mcp-compose. Just run:

```bash
anaconda-mcp serve --config examples/remote_auth_proxy/mcp_compose.toml
```

## What Success Looks Like

When you call `auth_echo_echo_auth_token`, the response should be:

```
Bearer ana-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

This proves the Anaconda token from your local keyring was forwarded through
mcp-compose to the downstream server as an HTTP Authorization header.

## Applying to Real Remote Servers

To connect to an actual remote MCP server deployed on anaconda.com, add an
entry like this to your `mcp_compose.toml`:

```toml
[[servers.proxied.streamable-http]]
name = "my_remote_server"
url = "https://my-server.anaconda.com/mcp"
auth_token = "${ANACONDA_API_KEY}"
auth_type = "bearer"
```

No `auto_start` needed since the server is already running remotely. The token
forwarding works identically.

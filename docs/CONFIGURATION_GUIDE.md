# Anaconda MCP Configuration Guide

`anaconda mcp serve` uses native FastMCP composition and stdio transport. There is no runtime server-composition file to edit for the default server. The `serve` command builds the Anaconda MCP server in code by mounting the vendored conda tools, proxying the remote package-search server with bearer authentication, and installing `PlatformMiddleware` for authentication, Terms of Service, and telemetry.

This guide covers the configuration that still applies to the native stdio runtime: authentication, Terms acceptance, conda executable discovery, and client environment variables.

## Table of Contents

- [Runtime Model](#runtime-model)
- [Authentication](#authentication)
- [Terms of Service](#terms-of-service)
- [Conda Executable Discovery](#conda-executable-discovery)
- [Client Environment Variables](#client-environment-variables)
- [Manual Client Configuration](#manual-client-configuration)
- [Compose and Discover](#compose-and-discover)
- [Troubleshooting](#troubleshooting)

---

## Runtime Model

The default server is fixed by code, not by a user-edited composition file:

1. `anaconda mcp serve` validates Anaconda authentication and Terms acceptance.
2. `build_composed_server()` creates a FastMCP server.
3. The vendored `anaconda_mcp.conda_mcp_lite` FastMCP server is mounted in-process.
4. The remote Anaconda search MCP is registered as an authenticated proxy.
5. `PlatformMiddleware` enforces auth, Terms, and telemetry.
6. The server runs over stdio for the launching MCP client.

Deprecated config, host, and port inputs are ignored by `serve`; they are not needed for stdio client setup.

---

## Authentication

Authentication is required before `serve` can run successfully.

Interactive login:

```bash
anaconda login
```

This stores credentials in the user's system keyring. Anaconda MCP retrieves and validates those credentials at startup and uses them for proxied Anaconda search requests.

Headless or CI-style client configuration can pass an API key through the client's environment:

```json
"env": {
  "ANACONDA_AUTH_API_KEY": "<your-api-key>"
}
```

API keys can be obtained from your Anaconda account settings.

---

## Terms of Service

Anaconda MCP requires acceptance of the current MCP Terms of Service.

Interactive acceptance:

```bash
anaconda mcp terms accept
```

Check status:

```bash
anaconda mcp terms status
```

Non-interactive acceptance:

```json
"env": {
  "ANACONDA_MCP_ACCEPTED_TERMS": "true",
  "ANACONDA_MCP_ACCEPTED_TERMS_VERSION": "2026-05-27"
}
```

Both variables are required for headless clients.

---

## Conda Executable Discovery

The vendored conda tools need a user-facing conda executable. Discovery tries, in order:

1. `CONDA_EXE` from the client environment.
2. `_CONDA_ROOT/bin/conda` from conda shell-hook state.
3. `conda` on `PATH`.
4. Platform-specific fallbacks for shell or registry discovery.

GUI applications often launch without shell initialization, so setting `CONDA_EXE` explicitly is the most reliable configuration:

```json
"env": {
  "CONDA_EXE": "/path/to/conda"
}
```

On Windows, point to `conda.exe` in the `Scripts` directory:

```json
"env": {
  "CONDA_EXE": "C:\\Users\\me\\miniconda3\\Scripts\\conda.exe"
}
```

---

## Client Environment Variables

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `CONDA_EXE` | Optional, recommended for GUI clients | Explicit conda executable path |
| `ANACONDA_AUTH_API_KEY` | Optional | API-key authentication when keyring login is unavailable |
| `ANACONDA_MCP_ACCEPTED_TERMS` | Required for headless Terms acceptance | Must be `true` |
| `ANACONDA_MCP_ACCEPTED_TERMS_VERSION` | Required for headless Terms acceptance | Current accepted Terms version |

Use the smallest env block possible. For a typical desktop setup, running `anaconda login` and `anaconda mcp terms accept` is enough; add `CONDA_EXE` only if the client cannot find conda.

---

## Manual Client Configuration

Most users should run:

```bash
anaconda mcp setup
```

If configuring manually, use a stdio MCP entry that launches the Python environment containing Anaconda MCP:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "type": "stdio",
      "command": "/path/to/anaconda-mcp/env/bin/python",
      "args": ["-m", "anaconda_mcp", "serve"],
      "env": {
        "CONDA_EXE": "/path/to/conda"
      }
    }
  }
}
```

Client JSON schemas vary. Some clients omit the `type` field or use a different top-level key, but the command, args, and env values remain the same.

---

## Compose and Discover

The `compose` and `discover` subcommands still exist:

```bash
anaconda mcp discover
anaconda mcp compose --output-format json
```

They are dependency-inspection helpers and are separate from `serve`. Running `serve` does not consume output from these commands.

---

## Troubleshooting

### Authentication errors

Run:

```bash
anaconda login
anaconda auth whoami
```

For headless clients, set `ANACONDA_AUTH_API_KEY` in the client env block.

### Terms errors

Run:

```bash
anaconda mcp terms accept
anaconda mcp terms status
```

For headless clients, set both Terms environment variables.

### Conda executable not found

Set `CONDA_EXE` in the client config. This is especially common for GUI-launched clients that do not inherit shell startup files.

### Config, host, or port changes have no effect

This is expected for the native stdio server. `serve` ignores deprecated config, host, and port inputs because it builds the FastMCP composition in code and communicates over stdin/stdout.

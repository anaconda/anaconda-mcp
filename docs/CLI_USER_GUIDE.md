# Anaconda MCP CLI User Guide

The Anaconda MCP CLI configures and runs Anaconda's MCP server. The primary runtime command, `anaconda mcp serve`, runs a native FastMCP server over stdio: conda tools are mounted in-process from the vendored `anaconda_mcp.conda_mcp_lite` package, package search is proxied remotely with bearer auth, and `PlatformMiddleware` enforces authentication, Terms of Service, and telemetry.

The `compose` and `discover` commands still exist for dependency discovery and composition workflows. They are not the startup path for `serve`.

## Table of Contents

- [Quick Start](#quick-start)
- [Commands Overview](#commands-overview)
- [Command Reference](#command-reference)
  - [serve](#serve-command)
  - [setup](#setup-command)
  - [compose](#compose-command)
  - [discover](#discover-command)
- [Configuration](#configuration)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Authenticate and accept Terms

```bash
anaconda login
anaconda mcp terms accept
```

### 2. Configure a client

```bash
anaconda mcp setup
```

The setup wizard writes a stdio MCP configuration for supported clients.

### 3. Start the MCP server manually, if needed

```bash
anaconda mcp serve
```

This will:

- Validate Anaconda authentication and Terms acceptance
- Build the native FastMCP composition in-process
- Mount vendored conda tools
- Proxy remote package-search tools with bearer auth
- Serve the MCP session over stdio

No host, port, or external runtime config is required for `serve`.

---

## Commands Overview

| Command | Description |
|---------|-------------|
| `serve` | Run the native Anaconda MCP FastMCP server over stdio |
| `setup` | Configure supported MCP clients with stdio transport |
| `compose` | Compose MCP servers from project dependencies |
| `discover` | Discover MCP servers available in project dependencies |
| `terms` | Show or accept Anaconda MCP Terms of Service |

### Global Options

```bash
-h, --help          Show help message
-v, --verbose       Enable verbose logging where supported
```

---

## Command Reference

### `serve` Command

Run the Anaconda MCP server over stdio.

#### Syntax

```bash
anaconda mcp serve [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-c, --config PATH` | Deprecated and ignored; native composition is built in code | None |
| `--delay SECONDS` | Delay in seconds before serving | `0` |
| `-v, --verbose` | Enable verbose logging | `false` |

`serve` is stdio-only. Deprecated host, port, and config inputs are not part of client setup and should not be used for normal operation.

#### Examples

**Start the stdio server:**

```bash
anaconda mcp serve
```

**Start with verbose logging:**

```bash
anaconda mcp -v serve
```

#### What It Does

1. **Validates platform requirements**: checks authentication and Terms acceptance.
2. **Builds native composition**: calls `build_composed_server()` instead of loading an external runtime config.
3. **Mounts conda tools**: mounts the vendored conda FastMCP server in-process.
4. **Proxies search**: registers the remote Anaconda search proxy with bearer auth.
5. **Applies middleware**: enforces auth, Terms, and telemetry with `PlatformMiddleware`.
6. **Runs stdio**: serves MCP requests through stdin/stdout for the launching client.

---

### `setup` Command

Configure supported MCP clients to launch Anaconda MCP over stdio.

#### Syntax

```bash
anaconda mcp setup [OPTIONS]
```

#### Common Options

| Option | Description |
|--------|-------------|
| `--client CLIENT` | Configure one supported client instead of using the wizard |
| `--scope SCOPE` | Choose a client-specific config scope, such as `global` or `project` |
| `--name NAME` | Server entry name in the client config |
| `--force` | Replace an existing entry |

#### Examples

```bash
anaconda mcp setup
anaconda mcp setup --client claude-code
anaconda mcp setup --client cursor --scope project
```

Generated client entries use stdio and launch `anaconda mcp serve` or `python -m anaconda_mcp serve` directly.

---

### `compose` Command

Compose multiple MCP servers from your project dependencies into a unified server description.

#### Syntax

```bash
anaconda mcp compose [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --pyproject PATH` | Path to `pyproject.toml` file | `./pyproject.toml` |
| `-n, --name NAME` | Name for the composed server | `composed-mcp-server` |
| `-c, --conflict-resolution STRATEGY` | Naming conflict strategy | `prefix` |
| `--include SERVER` | Include only specified servers, repeatable | None (all) |
| `--exclude SERVER` | Exclude specified servers, repeatable | None |
| `-o, --output PATH` | Write composed metadata to file | stdout |
| `--output-format FORMAT` | Output format: `text` or `json` | `text` |
| `-v, --verbose` | Enable verbose logging | `false` |

#### Conflict Resolution Strategies

| Strategy | Description |
|----------|-------------|
| `prefix` | Add server name as prefix: `server_toolname` |
| `suffix` | Add server name as suffix: `toolname_server` |
| `ignore` | Use first occurrence, ignore conflicts |
| `error` | Raise error on conflicts |
| `override` | Later servers override earlier ones |

#### Examples

```bash
anaconda mcp compose
anaconda mcp compose --name my-unified-server
anaconda mcp compose --include conda --include search
anaconda mcp compose --conflict-resolution suffix
anaconda mcp compose --output composed.json --output-format json
anaconda mcp compose -p /path/to/pyproject.toml
```

#### What It Does

1. **Scans dependencies**: reads your `pyproject.toml` to find MCP server packages.
2. **Discovers tools**: identifies tools and resources from each server.
3. **Resolves conflicts**: applies the requested naming strategy.
4. **Outputs metadata**: displays or saves the composed server description.

---

### `discover` Command

Discover MCP servers available in your project's dependencies.

#### Syntax

```bash
anaconda mcp discover [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --pyproject PATH` | Path to `pyproject.toml` file | `./pyproject.toml` |
| `--output-format FORMAT` | Output format: `text` or `json` | `text` |
| `-v, --verbose` | Enable verbose logging | `false` |

#### Examples

```bash
anaconda mcp discover
anaconda mcp discover --output-format json
anaconda mcp discover -p /workspace/myproject/pyproject.toml
anaconda mcp discover --output-format json > servers.json
```

#### What It Does

1. **Scans dependencies**: reads the specified `pyproject.toml` file.
2. **Identifies MCP servers**: finds installed packages that expose MCP servers.
3. **Extracts metadata**: gathers server names, versions, and capabilities.
4. **Outputs results**: displays the discovered servers in the requested format.

---

## Configuration

The `serve` command is configured through code and environment, not a runtime server file. It always builds the same Anaconda MCP stdio composition:

- Vendored conda tools mounted in-process
- Remote Anaconda search proxy with bearer auth
- Shared `PlatformMiddleware` for auth, Terms, and telemetry

Runtime environment variables that users may need:

| Variable | Purpose |
|----------|---------|
| `CONDA_EXE` | Explicit path to conda for GUI-launched clients |
| `ANACONDA_AUTH_API_KEY` | API key alternative to stored login credentials |
| `ANACONDA_MCP_ACCEPTED_TERMS` | Non-interactive Terms acceptance flag |
| `ANACONDA_MCP_ACCEPTED_TERMS_VERSION` | Accepted Terms version |

See [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) for details.

---

## Common Use Cases

### Local Development

Run the server in a terminal to see logs and startup errors:

```bash
anaconda mcp -v serve
```

### Client Setup

Configure a project-scoped client entry when supported:

```bash
anaconda mcp setup --client cursor --scope project
```

### Dependency Discovery

Inspect MCP servers in the current project:

```bash
anaconda mcp discover
anaconda mcp compose --output-format json
```

---

## Troubleshooting

### Server Won't Start

**Problem**: The `serve` command exits immediately.

**Solutions**:

1. Check authentication:
   ```bash
   anaconda auth whoami
   ```

2. Check Terms acceptance:
   ```bash
   anaconda mcp terms status
   ```

3. Use verbose logging:
   ```bash
   anaconda mcp -v serve
   ```

### Authentication Fails

Run:

```bash
anaconda login
```

If the client runs headlessly, provide `ANACONDA_AUTH_API_KEY` in the client's environment.

### Conda Is Not Found

GUI clients may not inherit shell initialization. Set `CONDA_EXE` explicitly in the client config:

```json
"env": {
  "CONDA_EXE": "/path/to/conda"
}
```

### No Servers Discovered

`discover` scans project dependencies, so it may return no results even when `serve` works. Verify your project dependencies and run:

```bash
anaconda mcp -v discover
```

### Tool Name Conflicts

For dependency-based composition, choose a different conflict strategy:

```bash
anaconda mcp compose --conflict-resolution prefix
```

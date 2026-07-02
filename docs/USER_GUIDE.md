# Anaconda MCP User Guide

Anaconda MCP exposes Anaconda tools to MCP-enabled AI assistants. The default runtime is `anaconda mcp serve`, a stdio-only FastMCP server that mounts vendored conda tools in-process, proxies Anaconda package search with bearer authentication, and enforces authentication, Terms of Service, and telemetry through one platform middleware layer.

The legacy `anaconda-mcp` executable may still work as a compatibility alias, but new examples use `anaconda mcp`.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Authentication and Terms](#authentication-and-terms)
- [Quick Start](#quick-start)
- [Commands Overview](#commands-overview)
- [Command Reference](#command-reference)
  - [serve](#serve)
  - [setup](#setup)
  - [compose](#compose)
  - [discover](#discover)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Configuration](#configuration)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- [Conda](https://docs.conda.io/en/latest/) (Miniconda or Anaconda Distribution)
- An Anaconda account or API key for authentication
- Acceptance of the current Anaconda MCP Terms of Service

---

## Installation

### Creating a new environment

```bash
conda create -n anaconda-mcp anaconda-mcp
conda activate anaconda-mcp
```

### Adding to an existing environment

```bash
conda activate <environment_name>
conda install anaconda-mcp
```

---

## Authentication and Terms

Authentication is required. Sign in before starting the server:

```bash
anaconda login
```

Then accept the MCP Terms of Service:

```bash
anaconda mcp terms accept
```

For non-interactive environments, set both Terms variables in the client environment:

```bash
export ANACONDA_MCP_ACCEPTED_TERMS=true
export ANACONDA_MCP_ACCEPTED_TERMS_VERSION=2026-05-27
```

Tool calls fail until authentication and Terms acceptance are both valid.

---

## Quick Start

### 1. Configure your MCP client

```bash
anaconda mcp setup
```

The setup wizard writes a stdio MCP configuration for supported clients. Supported clients include Claude Desktop, Claude Code, Cursor, Windsurf, VS Code, and OpenCode.

To configure one client non-interactively:

```bash
anaconda mcp setup --client claude-desktop
anaconda mcp setup --client cursor --scope project
```

### 2. Start the MCP server manually, if needed

Most clients launch the server automatically from their MCP config. For manual testing:

```bash
anaconda mcp serve
```

This starts the native FastMCP server over stdio. It does not open a port and does not require a separate server process.

### 3. Optional: inspect composition helpers

The `compose` and `discover` subcommands still exist for dependency discovery and composition workflows:

```bash
anaconda mcp discover
anaconda mcp compose --output-format json
```

These commands are separate from the stdio runtime used by `serve`.

---

## Commands Overview

| Command | Description |
|---------|-------------|
| `serve` | Run the native Anaconda MCP FastMCP server over stdio |
| `setup` | Configure a supported MCP client with stdio transport |
| `compose` | Compose MCP servers from project dependencies |
| `discover` | Discover MCP servers available in project dependencies |
| `terms` | View or accept the Anaconda MCP Terms of Service |

All commands support these global options:

```bash
-h, --help      Show help message
-v, --verbose   Enable verbose logging where supported
```

---

## Command Reference

### `serve`

Run the Anaconda MCP server over stdio.

```bash
anaconda mcp serve [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `-c, --config PATH` | Deprecated and ignored; `serve` uses native composition | None |
| `--delay SECONDS` | Delay before serving, useful for client startup races | `0` |
| `-v, --verbose` | Enable verbose logging | `false` |

**Examples:**

```bash
# Start over stdio
anaconda mcp serve

# Start with verbose logging
anaconda mcp -v serve
```

`serve` always uses stdio. It mounts `anaconda_mcp.conda_mcp_lite` in-process, proxies the remote search server with bearer auth, and applies `PlatformMiddleware` for authentication, Terms of Service, and telemetry.

---

### `setup`

Configure a supported MCP client to launch Anaconda MCP over stdio.

```bash
anaconda mcp setup [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--client CLIENT` | Configure one supported client | Interactive selection |
| `--scope SCOPE` | Client-specific config scope, such as `global` or `project` | Client default |
| `--name NAME` | Server entry name in the client config | `anaconda-mcp` |
| `--force` | Overwrite an existing entry | `false` |

The generated config is stdio-only and launches `anaconda mcp serve` or `python -m anaconda_mcp serve`, depending on the client and installation path.

---

### `compose`

Compose multiple MCP servers from your environment into a unified server description.

```bash
anaconda mcp compose [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --pyproject PATH` | Path to `pyproject.toml` | `./pyproject.toml` |
| `-n, --name NAME` | Name for the composed server | `composed-mcp-server` |
| `-c, --conflict-resolution STRATEGY` | Conflict strategy: `prefix`, `suffix`, `ignore`, `error`, `override` | `prefix` |
| `--include SERVER` | Include only specified servers, repeatable | All |
| `--exclude SERVER` | Exclude specified servers, repeatable | None |
| `-o, --output PATH` | Write output to file | stdout |
| `--output-format FORMAT` | Output format: `text` or `json` | `text` |

**Examples:**

```bash
anaconda mcp compose
anaconda mcp compose --name my-mcp-server
anaconda mcp compose --include conda_environments --include jupyter_server
anaconda mcp compose --output composed.json --output-format json
```

---

### `discover`

Discover MCP servers available in your current environment.

```bash
anaconda mcp discover [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --pyproject PATH` | Path to `pyproject.toml` | `./pyproject.toml` |
| `--output-format FORMAT` | Output format: `text` or `json` | `text` |

**Examples:**

```bash
anaconda mcp discover
anaconda mcp discover --output-format json
anaconda mcp discover -p /path/to/pyproject.toml
```

---

## Claude Desktop Integration

Anaconda MCP includes a built-in command to configure [Claude Desktop](https://claude.ai/download).

### Automatic setup

Make sure the environment containing Anaconda MCP is active, then run:

```bash
anaconda mcp claude-desktop setup-config
```

Restart Claude Desktop after running this command. Anaconda MCP tools will appear in Claude's tools list.

### Custom config location

```bash
anaconda mcp claude-desktop setup-config -c <PATH_TO_CLAUDE_DESKTOP_CONFIG>
```

### Manual setup

If you prefer to edit the Claude Desktop config file manually, add a stdio entry under `mcpServers`:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/path/to/python",
      "args": ["-m", "anaconda_mcp", "serve"],
      "env": {}
    }
  }
}
```

To find the correct Python path for your environment:

```bash
conda activate <environment_name>
which python
```

For full details on Claude Desktop integration, including how to remove the configuration or verify setup, see [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md).

---

## Configuration

`anaconda mcp serve` uses native FastMCP composition. There is no runtime composition file to edit for the default server, and client setup is stdio-only.

Configuration that still matters at runtime is supplied through Anaconda authentication, Terms acceptance, and environment variables:

| Setting | Purpose |
|---------|---------|
| `CONDA_EXE` | Explicit path to the user's conda executable, useful for GUI clients |
| `ANACONDA_AUTH_API_KEY` | API key alternative to keyring login |
| `ANACONDA_MCP_ACCEPTED_TERMS` | Non-interactive Terms acceptance flag |
| `ANACONDA_MCP_ACCEPTED_TERMS_VERSION` | Accepted Terms version |

For details, see [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md).

---

## Common Use Cases

### Local development with Claude Desktop

```bash
# 1. Install and activate
conda activate anaconda-mcp

# 2. Authenticate and accept Terms
anaconda login
anaconda mcp terms accept

# 3. Configure Claude Desktop
anaconda mcp claude-desktop setup-config

# 4. Restart Claude Desktop — tools are now available
```

### Manual client configuration

Add a stdio MCP server entry to your client config:

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

### Inspecting available dependency-based servers

```bash
anaconda mcp discover
anaconda mcp compose --output-format json
```

---

## Troubleshooting

### Server won't start

1. Confirm you are logged in:
   ```bash
   anaconda auth whoami
   ```

2. Confirm Terms acceptance:
   ```bash
   anaconda mcp terms status
   ```

3. Run manually with verbose logging:
   ```bash
   anaconda mcp -v serve
   ```

### Claude Desktop doesn't show Anaconda MCP tools

1. Verify the configuration was written correctly:
   ```bash
   anaconda mcp claude-desktop show
   ```

2. Fully restart Claude Desktop; closing the window is not enough.

3. Check that the Python path in the config points to the environment where Anaconda MCP is installed.

4. For GUI clients that cannot find conda, set `CONDA_EXE` in the config `env` block.

### Authentication errors

Run:

```bash
anaconda login
```

If using an API key in a client config, set `ANACONDA_AUTH_API_KEY` in that client's environment.

### Terms errors

Run:

```bash
anaconda mcp terms accept
```

For headless clients, set both `ANACONDA_MCP_ACCEPTED_TERMS=true` and `ANACONDA_MCP_ACCEPTED_TERMS_VERSION=2026-05-27`.

For additional troubleshooting details, see [CLI_USER_GUIDE.md](CLI_USER_GUIDE.md) and [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md).

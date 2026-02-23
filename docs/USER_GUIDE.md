# Anaconda MCP User Guide

Anaconda MCP is a unified gateway that composes multiple [Model Context Protocol (MCP)](https://modelcontextprotocol.io) servers into a single endpoint. It lets AI assistants like Claude interact with your Anaconda environments, Jupyter notebooks, and other tools through a consistent interface — without requiring you to configure each server individually.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Anaconda Authentication](#anaconda-authentication)
- [Quick Start](#quick-start)
- [Commands Overview](#commands-overview)
- [Command Reference](#command-reference)
  - [serve](#serve)
  - [compose](#compose)
  - [discover](#discover)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Configuration](#configuration)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- [Conda](https://docs.conda.io/en/latest/) (Miniconda or Anaconda Distribution)

---

## Installation

### Creating a new environment

```bash
conda create -n <environment_name> anaconda-mcp
conda activate <environment_name>
```

### Adding to an existing environment

```bash
conda activate <environment_name>
conda install anaconda-mcp
```

---

## Anaconda Authentication

When Anaconda MCP starts, it may automatically open a browser window pointing to Anaconda's login page. This happens if you are not currently logged in or do not have an Anaconda account.

**Authentication is not required.** You can safely ignore the browser window, leave it open, or close it entirely — Anaconda MCP will continue running normally either way. Core functionality is available without an Anaconda account.

---

## Quick Start

### 1. Start the MCP server

```bash
anaconda-mcp serve
```

This loads the default configuration, starts all configured MCP servers, and exposes them through a unified endpoint.

### 2. Discover available servers

```bash
anaconda-mcp discover
```

Lists all MCP servers available in your current environment.

### 3. Compose multiple servers

```bash
anaconda-mcp compose
```

Combines multiple MCP servers into a single unified interface.

---

## Commands Overview

| Command | Description |
|---------|-------------|
| `serve` | Start MCP servers from a configuration file |
| `compose` | Compose multiple MCP servers into one unified server |
| `discover` | Discover MCP servers available in the current environment |

All commands support these global options:

```bash
-h, --help      Show help message
-v, --verbose   Enable verbose logging
```

---

## Command Reference

### `serve`

Start and manage MCP servers based on a configuration file.

```bash
anaconda-mcp serve [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `-c, --config PATH` | Path to `mcp_compose.toml` | `src/anaconda_mcp/mcp_compose.toml` |
| `--host HOST` | Host address to bind to | `0.0.0.0` |
| `--port PORT` | Port to bind to | `8000` |

**Examples:**

```bash
# Start with default configuration
anaconda-mcp serve

# Start on a custom port
anaconda-mcp serve --port 8888

# Start with a custom configuration file
anaconda-mcp serve --config /path/to/my_config.toml

# Start with verbose logging
anaconda-mcp -v serve
```

---

### `compose`

Compose multiple MCP servers from your environment into a unified server.

```bash
anaconda-mcp compose [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --pyproject PATH` | Path to `pyproject.toml` | `./pyproject.toml` |
| `-n, --name NAME` | Name for the composed server | `composed-mcp-server` |
| `-c, --conflict-resolution STRATEGY` | Conflict strategy: `prefix`, `suffix`, `ignore`, `error`, `override` | `prefix` |
| `--include SERVER` | Include only specified servers (repeatable) | All |
| `--exclude SERVER` | Exclude specified servers (repeatable) | None |
| `-o, --output PATH` | Write output to file | stdout |
| `--output-format FORMAT` | Output format: `text` or `json` | `text` |

**Examples:**

```bash
# Compose all servers
anaconda-mcp compose

# Compose with a custom name
anaconda-mcp compose --name my-mcp-server

# Include only specific servers
anaconda-mcp compose --include conda_environments --include jupyter_server

# Save composed configuration as JSON
anaconda-mcp compose --output composed.json --output-format json
```

---

### `discover`

Discover MCP servers available in your current environment.

```bash
anaconda-mcp discover [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --pyproject PATH` | Path to `pyproject.toml` | `./pyproject.toml` |
| `--output-format FORMAT` | Output format: `text` or `json` | `text` |

**Examples:**

```bash
# Discover servers in the current environment
anaconda-mcp discover

# Output as JSON
anaconda-mcp discover --output-format json

# Discover from a specific pyproject.toml
anaconda-mcp discover -p /path/to/pyproject.toml
```

---

## Claude Desktop Integration

Anaconda MCP includes a built-in command to configure [Claude Desktop](https://claude.ai/download) automatically.

### Automatic setup

Make sure the environment containing Anaconda MCP is active, then run:

```bash
anaconda-mcp claude-desktop setup-config
```

Restart Claude Desktop after running this command. Anaconda MCP tools will appear in Claude's tools list.

### Custom config location

If your Claude Desktop configuration file is in a non-standard location:

```bash
anaconda-mcp claude-desktop setup-config -c <PATH_TO_CLAUDE_DESKTOP_CONFIG>
```

### Transport types

By default, the setup uses STDIO transport (recommended for most users). To use Streamable HTTP instead:

```bash
# Configure with HTTP transport
anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888

# Then start the server separately
anaconda-mcp serve --port 8888
```

### Default config file paths by OS

| Operating System | Path |
|------------------|------|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |

To print the path for your current OS:

```bash
anaconda-mcp claude-desktop path
```

### Manual setup

If you prefer to edit the Claude Desktop config file manually, add an entry under `mcpServers`:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/path/to/python",
      "args": ["-m", "anaconda_mcp", "serve", "--config", "/path/to/mcp_compose.toml"],
      "env": {
        "MCP_COMPOSE_CONFIG_DIR": "/path/to/anaconda_mcp"
      }
    }
  }
}
```

To find the correct Python path for your environment:

```bash
conda activate <environment_name>
which python
```

For full details on Claude Desktop integration, including how to remove the configuration or verify the setup, see [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md).

---

## Configuration

Anaconda MCP uses a `mcp_compose.toml` file to define server composition, transport settings, authentication, and tool management.

### Which file should I edit?

There are two related files shipped with the package:

| File | Purpose | Should I edit it? |
|------|---------|-------------------|
| `mcp_compose.toml.template` | Primary config with dynamic placeholders | ✅ Yes |
| `mcp_compose.toml` | Fallback used only if the template is absent | ❌ No |

When Anaconda MCP starts, it detects whether `mcp_compose.toml.template` exists. If it does, the template is rendered at runtime (resolving placeholders like `{{PYTHON_EXECUTABLE}}`) and the resulting config is used. If the template is absent, `mcp_compose.toml` is used as-is.

**Edit `mcp_compose.toml.template`** for any customizations — your changes take effect on the next run without restarting.

### Example: changing the port

```toml
# mcp_compose.toml.template
[composer]
port = 9000
```

Then restart the server:

```bash
anaconda-mcp serve
```

### Using a fully custom config file

You can bypass the template system entirely by pointing the CLI to your own config file:

```bash
anaconda-mcp serve --config /path/to/my_custom.toml
```

For the full configuration reference, including transport, authentication, and tool aliases, see [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) and [SERVER_CONFIGURATION.md](SERVER_CONFIGURATION.md).

---

## Common Use Cases

### Local development with Claude Desktop

```bash
# 1. Install and activate
conda activate anaconda-mcp-env

# 2. Configure Claude Desktop
anaconda-mcp claude-desktop setup-config

# 3. Restart Claude Desktop — tools are now available
```

### Running as a shared HTTP server

```bash
# Start the server on a specific host and port
anaconda-mcp serve --host 0.0.0.0 --port 8888
```

Other clients can then connect to `http://<your-host>:8888/mcp`.

### Inspecting what's available before serving

```bash
# See all available servers
anaconda-mcp discover

# Preview the composed server configuration
anaconda-mcp compose --output-format json
```

---

## Troubleshooting

### Server won't start

1. Check that the configuration file exists and is valid TOML:
   ```bash
   ls src/anaconda_mcp/mcp_compose.toml
   ```

2. Run with verbose logging to see detailed errors:
   ```bash
   anaconda-mcp -v serve
   ```

3. Check whether the port is already in use:
   ```bash
   lsof -i :8000
   ```

### Port already in use (port collision)

This is one of the most common issues. It happens when another process is already listening on the port Anaconda MCP is trying to bind to (default: `2391`).

**Symptoms:** The server fails to start with an error like `Address already in use` or `OSError: [Errno 48]`.

1. Find out what is using the port:
   ```bash
   # macOS / Linux
   lsof -i :2391

   # Windows
   netstat -ano | findstr :2391
   ```

2. You can either stop the conflicting process or start Anaconda MCP on a different port:
   ```bash
   anaconda-mcp serve --port 8888
   ```

3. If you are using Claude Desktop and changed the port, update the config to match:
   ```bash
   anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888 --force
   ```

4. To avoid repeated collisions, set a custom default port in `mcp_compose.toml.template`:
   ```toml
   [composer]
   port = 8888
   ```

### Downstream port collision (Environments MCP)

Anaconda MCP acts as a gateway to downstream MCP servers. Even if Anaconda MCP itself starts successfully and your MCP client connects without issue, tool calls can still fail silently if a downstream server can't bind to its own port.

The **Environments MCP** server, when configured to use Streamable HTTP transport, defaults to port `4041`. If something else is already using that port, Anaconda MCP will start normally and the client will connect — but any call routed to the Environments MCP will fail.

1. Check whether port `4041` is in use:
   ```bash
   # macOS / Linux
   lsof -i :4041

   # Windows
   netstat -ano | findstr :4041
   ```

2. If there is a conflict, update the Environments MCP port in `mcp_compose.toml.template`:
   ```toml
   [[servers.proxied.streamable-http]]
   name = "environments"
   url = "http://localhost:4042/mcp"  # changed from 4041
   ```

### Diagnosing failures with logs

When tool calls fail and the cause isn't obvious, there are two good ways to get more detail:

**Claude Desktop MCP logs** — Claude Desktop writes MCP-level logs that can surface connection and tool errors. Open them from the Claude Desktop menu under **Help → Open MCP Log File** (or equivalent for your OS).

**Run the server manually in a terminal** — This gives you the most complete output and is often the fastest way to understand what's going wrong:
```bash
anaconda-mcp -v serve
```
With verbose logging enabled you'll see each downstream server starting up, the ports they bind to, and any errors as they happen in real time.

---

### No servers discovered

1. Confirm MCP server packages are installed in the active environment:
   ```bash
   conda list | grep mcp
   ```

2. Run with verbose logging:
   ```bash
   anaconda-mcp -v discover
   ```

### My configuration changes aren't taking effect

You likely edited `mcp_compose.toml` while `mcp_compose.toml.template` exists. The template takes precedence — edit the template file instead.

### Claude Desktop doesn't show Anaconda MCP tools

1. Verify the configuration was written correctly:
   ```bash
   anaconda-mcp claude-desktop show
   ```

2. Make sure you fully restarted Claude Desktop (quit and reopen, not just close the window).

3. Check that the Python path in the config points to the correct conda environment.

### Authentication errors

Anaconda MCP authentication is disabled by default. If you have enabled it in your config, ensure you are logged in:

```bash
anaconda login
```

For additional troubleshooting details, see [CLI_USER_GUIDE.md](CLI_USER_GUIDE.md) and [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md).

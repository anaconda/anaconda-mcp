# Anaconda MCP CLI User Guide

The Anaconda MCP CLI is a command-line interface for managing and composing Model Context Protocol (MCP) servers. It provides a unified way to discover, compose, and serve multiple MCP servers through a single endpoint.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands Overview](#commands-overview)
- [Command Reference](#command-reference)
  - [serve](#serve-command)
  - [compose](#compose-command)
  - [discover](#discover-command)
- [Configuration](#configuration)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Using pip

```bash
# Install the package
pip install anaconda-mcp

# Or install in development mode
pip install -e ".[dev]"
```

### Using conda

```bash
# Create environment from file
conda env create -f environment.yml

# Activate the environment
conda activate anaconda-mcp

# Or use the development environment
conda env create -f environment-dev.yml
conda activate anaconda-mcp-dev
```

### Using Make (for developers)

```bash
# Setup development environment
make setup

# Install in development mode
make install-dev
```

### Verify Installation

```bash
# Check that the CLI is installed
anaconda-mcp --help
```

---

## Quick Start

### 1. Start the MCP Server

The simplest way to get started is to run the serve command:

```bash
# Start with default configuration
anaconda-mcp serve

# Start with custom host and port
anaconda-mcp serve --host 0.0.0.0 --port 8888
```

This will:
- Load the default configuration from `mcp_compose.toml`
- Start any configured MCP servers
- Expose them through a unified API endpoint
- Handle authentication if configured

### 2. Discover Available MCP Servers

To see what MCP servers are available in your project dependencies:

```bash
# Discover servers in current project
anaconda-mcp discover

# Discover servers from specific pyproject.toml
anaconda-mcp discover -p /path/to/pyproject.toml

# Output as JSON
anaconda-mcp discover --output-format json
```

### 3. Compose Multiple Servers

Combine multiple MCP servers into a single unified interface:

```bash
# Compose servers from dependencies
anaconda-mcp compose

# Compose with custom name
anaconda-mcp compose --name my-mcp-server

# Include specific servers only
anaconda-mcp compose --include server1 --include server2

# Exclude specific servers
anaconda-mcp compose --exclude server3
```

---

## Commands Overview

| Command | Description |
|---------|-------------|
| `serve` | Start MCP servers from a configuration file |
| `compose` | Compose multiple MCP servers into one unified server |
| `discover` | Discover MCP servers available in project dependencies |

### Global Options

All commands support these global options:

```bash
-h, --help          Show help message
-v, --verbose       Enable verbose logging
```

---

## Command Reference

### `serve` Command

Start and manage MCP servers based on a configuration file.

#### Syntax

```bash
anaconda-mcp serve [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-c, --config PATH` | Path to mcp_compose.toml configuration file | `src/anaconda_mcp/mcp_compose.toml` |
| `--host HOST` | Host address to bind the server to | `0.0.0.0` |
| `--port PORT` | Port number to bind the server to | `8000` |
| `-v, --verbose` | Enable verbose logging | `false` |

#### Examples

**Start with default configuration:**
```bash
anaconda-mcp serve
```

**Start with custom configuration file:**
```bash
anaconda-mcp serve --config /path/to/my_config.toml
```

**Start on specific host and port:**
```bash
anaconda-mcp serve --host 127.0.0.1 --port 8888
```

**Start with verbose logging:**
```bash
anaconda-mcp -v serve --port 9000
```

#### What It Does

1. **Loads Configuration**: Reads the specified `mcp_compose.toml` file
2. **Authenticates**: Initiates the Anaconda authentication flow (if enabled)
3. **Starts Servers**: Launches all configured MCP servers
4. **Exposes API**: Makes tools and resources available through HTTP/SSE endpoints
5. **Health Monitoring**: Monitors server health and handles reconnections

#### Configuration File

The `serve` command requires a `mcp_compose.toml` configuration file. See [Configuration](#configuration) section for details.

---

### `compose` Command

Compose multiple MCP servers from your project dependencies into a unified server.

#### Syntax

```bash
anaconda-mcp compose [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --pyproject PATH` | Path to pyproject.toml file | `./pyproject.toml` |
| `-n, --name NAME` | Name for the composed server | `composed-mcp-server` |
| `-c, --conflict-resolution STRATEGY` | How to handle naming conflicts | `prefix` |
| `--include SERVER` | Include only specified servers (repeatable) | None (all) |
| `--exclude SERVER` | Exclude specified servers (repeatable) | None |
| `-o, --output PATH` | Write composed server metadata to file | stdout |
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

**Basic composition:**
```bash
anaconda-mcp compose
```

**Compose with custom name:**
```bash
anaconda-mcp compose --name my-unified-server
```

**Include only specific servers:**
```bash
anaconda-mcp compose --include conda_environments --include jupyter_server
```

**Exclude certain servers:**
```bash
anaconda-mcp compose --exclude legacy_server --exclude deprecated_tools
```

**Use suffix for conflict resolution:**
```bash
anaconda-mcp compose --conflict-resolution suffix
```

**Save composition to JSON file:**
```bash
anaconda-mcp compose --output composed.json --output-format json
```

**Compose from specific pyproject.toml:**
```bash
anaconda-mcp compose -p /path/to/pyproject.toml
```

**Combine multiple options:**
```bash
anaconda-mcp -v compose \
  --name production-mcp \
  --include conda_environments \
  --include jupyter_server \
  --conflict-resolution prefix \
  --output metadata.json \
  --output-format json
```

#### What It Does

1. **Scans Dependencies**: Reads your `pyproject.toml` to find MCP server packages
2. **Discovers Tools**: Identifies all tools and resources from each server
3. **Resolves Conflicts**: Applies naming strategy to handle duplicate tool names
4. **Generates Metadata**: Creates a unified interface combining all servers
5. **Outputs Result**: Displays or saves the composed server configuration

---

### `discover` Command

Discover MCP servers available in your project's dependencies.

#### Syntax

```bash
anaconda-mcp discover [OPTIONS]
```

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --pyproject PATH` | Path to pyproject.toml file | `./pyproject.toml` |
| `--output-format FORMAT` | Output format: `text` or `json` | `text` |
| `-v, --verbose` | Enable verbose logging | `false` |

#### Examples

**Discover servers in current project:**
```bash
anaconda-mcp discover
```

**Discover with JSON output:**
```bash
anaconda-mcp discover --output-format json
```

**Discover from specific pyproject.toml:**
```bash
anaconda-mcp discover -p /workspace/myproject/pyproject.toml
```

**Pipe JSON output to file:**
```bash
anaconda-mcp discover --output-format json > servers.json
```

**Pretty-print JSON with jq:**
```bash
anaconda-mcp discover --output-format json | jq .
```

#### What It Does

1. **Scans Dependencies**: Reads the specified `pyproject.toml` file
2. **Identifies MCP Servers**: Finds all installed packages that expose MCP servers
3. **Extracts Metadata**: Gathers information about each server (name, version, capabilities)
4. **Outputs Results**: Displays the discovered servers in the requested format

#### Sample Output

**Text format:**
```
Discovered MCP Servers:
  ✓ conda_environments (v1.0.0)
    - Tools: list_environments, create_environment, delete_environment
    - Resources: environment_info
  ✓ jupyter_server (v2.1.0)
    - Tools: create_notebook, run_cell, list_notebooks
```

**JSON format:**
```json
{
  "servers": [
    {
      "name": "conda_environments",
      "version": "1.0.0",
      "tools": [
        "list_environments",
        "create_environment",
        "delete_environment"
      ],
      "resources": ["environment_info"]
    }
  ]
}
```

---

## Configuration

The Anaconda MCP uses a `mcp_compose.toml` file for configuration. This file defines how servers are composed, connected, and exposed.

### Configuration File Location

By default, the CLI looks for the configuration file at:
```
src/anaconda_mcp/mcp_compose.toml
```

You can specify a custom location with the `--config` flag:
```bash
anaconda-mcp serve --config /path/to/custom_config.toml
```

### Configuration Structure

#### Basic Configuration

```toml
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"
port = 8888
```

#### Transport Configuration

```toml
[transport]
stdio_enabled = true
sse_enabled = true
sse_path = "/sse"
sse_cors_enabled = true
```

#### Authentication (Optional)

```toml
[authentication]
enabled = true
providers = ["anaconda"]
default_provider = "anaconda"

[authentication.anaconda]
domain = "anaconda.com"
```

#### Server Configuration

**Streamable HTTP Server:**
```toml
[[servers.proxied.streamable-http]]
name = "conda_environments"
url = "http://localhost:4041/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
auto_start = true
command = ["environments-mcp-server", "start", "--transport", "streamable-http"]
startup_delay = 3
```

**STDIO Server:**
```toml
[[servers.proxied.stdio]]
name = "local_tools"
command = ["my-mcp-server", "start"]
restart_policy = "never"
```

**SSE Server:**
```toml
[[servers.proxied.sse]]
name = "remote_server"
url = "https://remote.example.com/mcp/sse"
auth_token = "${REMOTE_SERVER_TOKEN}"
timeout = 30
reconnect_on_failure = true
```

#### Tool Manager Configuration

```toml
[tool_manager]
conflict_resolution = "prefix"

[tool_manager.custom_template]
template = "{server_name}_{tool_name}"

[tool_manager.aliases]
create_env = "conda_create_environment"
list_envs = "conda_list_environments"
```

#### REST API Configuration

```toml
[api]
enabled = true
path_prefix = "/api/v1"
host = "0.0.0.0"
port = 8888
cors_enabled = true
cors_origins = ["http://localhost:3000"]
docs_enabled = true
docs_path = "/docs"
```

### Configuration Options Reference

| Section | Option | Description | Default |
|---------|--------|-------------|---------|
| `[composer]` | `name` | Name of the composed server | `anaconda-mcp` |
| | `conflict_resolution` | Naming conflict strategy | `prefix` |
| | `log_level` | Logging level | `INFO` |
| | `port` | Server port | `8888` |
| `[transport]` | `stdio_enabled` | Enable STDIO transport | `true` |
| | `sse_enabled` | Enable SSE transport | `true` |
| | `sse_cors_enabled` | Enable CORS for SSE | `true` |
| `[authentication]` | `enabled` | Enable authentication | `false` |
| | `providers` | Authentication providers | `["anaconda"]` |
| `[api]` | `enabled` | Enable REST API | `true` |
| | `cors_enabled` | Enable CORS | `true` |
| | `docs_enabled` | Enable API documentation | `true` |

---

## Common Use Cases

### Use Case 1: Local Development

Start a local MCP server for development:

```bash
# Start with default config and verbose logging
anaconda-mcp -v serve --host 127.0.0.1 --port 8000
```

### Use Case 2: Production Deployment

Deploy MCP servers in production:

```bash
# Use production config with proper host binding
anaconda-mcp serve \
  --config /etc/anaconda-mcp/production.toml \
  --host 0.0.0.0 \
  --port 8888
```

### Use Case 3: Discover Available Tools

Find out what MCP servers are available:

```bash
# List all available servers
anaconda-mcp discover

# Export to JSON for processing
anaconda-mcp discover --output-format json > available_servers.json
```

### Use Case 4: Selective Server Composition

Compose only specific servers:

```bash
# Only include conda and jupyter servers
anaconda-mcp compose \
  --include conda_environments \
  --include jupyter_server \
  --name data-science-mcp
```

### Use Case 5: Exclude Problematic Servers

Exclude servers that are causing issues:

```bash
# Exclude legacy or broken servers
anaconda-mcp compose \
  --exclude old_server \
  --exclude deprecated_tools \
  --conflict-resolution prefix
```

### Use Case 6: Testing New Configuration

Test a new configuration before deploying:

```bash
# Use a test configuration file
anaconda-mcp -v serve \
  --config ./test_config.toml \
  --port 9999
```

### Use Case 7: Multi-Environment Setup

Run different configurations for different environments:

```bash
# Development
anaconda-mcp serve --config dev_config.toml --port 8000

# Staging
anaconda-mcp serve --config staging_config.toml --port 8001

# Production
anaconda-mcp serve --config prod_config.toml --port 8888
```

### Use Case 8: CI/CD Pipeline Integration

Use in automated pipelines:

```bash
#!/bin/bash
# Discover and validate servers
if anaconda-mcp discover --output-format json | jq -e '.servers | length > 0'; then
  echo "MCP servers found"
  anaconda-mcp compose --output composition.json --output-format json
else
  echo "No MCP servers found"
  exit 1
fi
```

---

## Troubleshooting

### Server Won't Start

**Problem**: The serve command fails immediately.

**Solutions**:
1. Check if the configuration file exists:
   ```bash
   ls -la src/anaconda_mcp/mcp_compose.toml
   ```

2. Verify the configuration is valid TOML syntax

3. Use verbose logging to see detailed errors:
   ```bash
   anaconda-mcp -v serve
   ```

4. Check if the port is already in use:
   ```bash
   lsof -i :8888  # or your configured port
   ```

### Authentication Fails

**Problem**: Authentication with Anaconda fails.

**Solutions**:
1. Ensure you're logged into Anaconda:
   ```bash
   anaconda login
   ```

2. Check your authentication configuration in `mcp_compose.toml`

3. Verify your network connection and firewall settings

### No Servers Discovered

**Problem**: `discover` command returns no servers.

**Solutions**:
1. Verify MCP server packages are installed:
   ```bash
   pip list | grep mcp
   ```

2. Check your `pyproject.toml` has the dependencies listed:
   ```bash
   cat pyproject.toml
   ```

3. Try with verbose logging:
   ```bash
   anaconda-mcp -v discover
   ```

### Tool Name Conflicts

**Problem**: Tool names conflict between servers.

**Solutions**:
1. Use a different conflict resolution strategy:
   ```bash
   anaconda-mcp compose --conflict-resolution prefix
   ```

2. Use tool aliases in `mcp_compose.toml`:
   ```toml
   [tool_manager.aliases]
   env_create = "conda_create_environment"
   ```

3. Exclude conflicting servers:
   ```bash
   anaconda-mcp compose --exclude conflicting_server
   ```

### Connection Issues

**Problem**: Cannot connect to remote MCP servers.

**Solutions**:
1. Verify the server URL is correct and accessible:
   ```bash
   curl http://localhost:4041/mcp
   ```

2. Check timeout settings in configuration

3. Ensure authentication tokens are set correctly

4. Review health check settings:
   ```toml
   [[servers.proxied.streamable-http]]
   health_check_enabled = true
   health_check_interval = 30
   ```

### High Memory Usage

**Problem**: Server consumes too much memory.

**Solutions**:
1. Reduce the number of proxied servers

2. Adjust reconnection attempts:
   ```toml
   max_reconnect_attempts = 3  # Instead of 10
   ```

3. Disable keep-alive for inactive connections:
   ```toml
   keep_alive = false
   ```

### Logs Not Appearing

**Problem**: Cannot see log output.

**Solutions**:
1. Enable verbose logging:
   ```bash
   anaconda-mcp -v serve
   ```

2. Check log level in configuration:
   ```toml
   [composer]
   log_level = "DEBUG"  # Instead of INFO
   ```

3. Ensure logs aren't being redirected:
   ```bash
   anaconda-mcp serve 2>&1 | tee server.log
   ```

---

## Additional Resources

- **Project Repository**: [https://github.com/anaconda/anaconda-mcp](https://github.com/anaconda/anaconda-mcp)
- **Issue Tracker**: [https://github.com/anaconda/anaconda-mcp/issues](https://github.com/anaconda/anaconda-mcp/issues)
- **MCP Specification**: [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- **Anaconda Documentation**: [https://docs.anaconda.com](https://docs.anaconda.com)

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check verbose output**: Run commands with `-v` flag for detailed logs
2. **Search existing issues**: Check the GitHub issue tracker
3. **Ask the community**: Join the Anaconda community forums
4. **Report bugs**: Create a detailed issue report with:
   - Command you ran
   - Expected behavior
   - Actual behavior
   - Configuration file (sanitized)
   - Log output with `-v` flag

---

## Version Information

To check your installed version:

```bash
pip show anaconda-mcp
```

Or:

```bash
conda list anaconda-mcp
```

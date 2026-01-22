# Anaconda MCP Configuration Guide

This guide provides detailed information about configuring the Anaconda MCP using the `mcp_compose.toml` file.

## Table of Contents

- [Configuration File Overview](#configuration-file-overview)
- [Composer Settings](#composer-settings)
- [Transport Configuration](#transport-configuration)
- [Authentication](#authentication)
- [Server Configuration](#server-configuration)
- [Tool Manager](#tool-manager)
- [Complete Examples](#complete-examples)

---

## Configuration File Overview

The Anaconda MCP uses a TOML configuration file (`mcp_compose.toml`) to define:
- Server composition settings
- Transport protocols
- Authentication providers
- Individual MCP server configurations
- Tool naming and conflict resolution

### File Location

**Default location:**
```
src/anaconda_mcp/mcp_compose.toml
```

**Custom location:**
```bash
anaconda-mcp serve --config /path/to/custom_config.toml
```

---

## Composer Settings

The `[composer]` section defines global settings for the composed MCP server.

### Configuration



### Options

### Conflict Resolution Strategies


### Example

```toml
[composer]
name = "production-mcp-server"
conflict_resolution = "prefix"
log_level = "WARNING"
port = 8080
```

---

## Transport Configuration

The `[transport]` section configures communication protocols.

### Configuration

```toml
[transport]
stdio_enabled = true
sse_enabled = true
sse_path = "/sse"
sse_cors_enabled = true
```

### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `stdio_enabled` | boolean | Enable standard input/output transport | `true` |
| `sse_enabled` | boolean | Enable Server-Sent Events transport | `true` |
| `sse_path` | string | URL path for SSE endpoint | `"/sse"` |
| `sse_cors_enabled` | boolean | Enable CORS for SSE | `true` |

### Transport Types

**STDIO** - Standard input/output

**SSE** - Server-Sent Events

**HTTP Streamable **

### Example

```toml
[transport]
stdio_enabled = false
sse_enabled = true
sse_path = "/api/events"
sse_cors_enabled = true
```

---

## Authentication



### Anaconda Provider


### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `enabled` | boolean | Enable authentication | `false` |
| `providers` | array | List of authentication providers | `["anaconda"]` |
| `default_provider` | string | Default provider to use | `"anaconda"` |


### Environment Variables


---

## Server Configuration


### Streamable HTTP Servers


#### Options


### STDIO Servers


#### Restart Policies

- `never` - Never restart
- `on-failure` - Restart only on failure
- `always` - Always restart

### SSE Servers

---

## Tool Manager

The `[tool_manager]` section configures how tools from different servers are named and managed.

### Configuration

```toml
[tool_manager]
conflict_resolution = "prefix"

[tool_manager.custom_template]
template = "{server_name}_{tool_name}"

[tool_manager.aliases]
create_env = "conda_create_environment"
list_envs = "conda_list_environments"
delete_env = "conda_delete_environment"

[tool_manager.versioning]
enabled = false
allow_multiple_versions = false
version_suffix_format = "_v{version}"
```

### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `conflict_resolution` | string | Naming strategy | `"prefix"` |
| `custom_template.template` | string | Custom naming template | `null` |
| `aliases` | table | Tool name aliases | `{}` |
| `versioning.enabled` | boolean | Enable tool versioning | `false` |
| `versioning.allow_multiple_versions` | boolean | Allow multiple versions | `false` |
| `versioning.version_suffix_format` | string | Version suffix format | `"_v{version}"` |

### Custom Templates

Available variables:
- `{server_name}` - Name of the server
- `{tool_name}` - Original tool name
- `{version}` - Tool version (if available)

**Examples:**


### Aliases

Create friendly names for tools:

```toml
[tool_manager.aliases]
# alias = "actual_tool_name"
create_env = "conda_environments_create_environment"
list_envs = "conda_environments_list_environments"
notebook = "jupyter_server_create_notebook"
```

Usage:
```bash
# Instead of: conda_environments_create_environment
# Use: create_env
```

---

## Complete Examples

### Development Configuration

```toml
[composer]
name = "dev-mcp"
conflict_resolution = "prefix"
log_level = "DEBUG"
port = 8000

[transport]
stdio_enabled = true
sse_enabled = true
sse_cors_enabled = true

[authentication]
enabled = false

[[servers.proxied.streamable-http]]
name = "conda_environments"
url = "http://localhost:4041/mcp"
auto_start = true
command = ["environments-mcp-server", "start", "--transport", "streamable-http"]
startup_delay = 2

[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = true
host = "127.0.0.1"
port = 8000
cors_enabled = true
cors_origins = ["http://localhost:3000"]
docs_enabled = true
```
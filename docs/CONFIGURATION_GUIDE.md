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

```toml
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"
port = 8888
```

### Options

| Option | Type | Description | Default | Valid Values |
|--------|------|-------------|---------|--------------|
| `name` | string | Name of the composed server | `"anaconda-mcp"` | Any string |
| `conflict_resolution` | string | Strategy for handling tool name conflicts | `"prefix"` | `prefix`, `suffix`, `ignore`, `error`, `override` |
| `log_level` | string | Logging verbosity | `"INFO"` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `port` | integer | Default port for the server | `8888` | 1024-65535 |

### Conflict Resolution Strategies

**prefix** - Add server name before tool name:
```
server_name_tool_name
```

**suffix** - Add server name after tool name:
```
tool_name_server_name
```

**ignore** - Keep first occurrence, ignore duplicates:
```
tool_name  # from first server only
```

**error** - Raise an error when conflicts occur:
```
ConfigurationError: Duplicate tool name 'tool_name'
```

**override** - Later servers override earlier ones:
```
tool_name  # from last server
```

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
- Best for: CLI tools, local processes
- Pros: Simple, fast, no network overhead
- Cons: Local only

**SSE** - Server-Sent Events
- Best for: Web applications, real-time updates
- Pros: Browser-compatible, real-time streaming
- Cons: One-way communication (server to client)

**HTTP Streamable - TBD**

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

The `[authentication]` section configures authentication providers.

### Basic Configuration

```toml
[authentication]
enabled = true
providers = ["anaconda"]
default_provider = "anaconda"
```

### Anaconda Provider

```toml
[authentication.anaconda]
domain = "anaconda.com"
```

### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `enabled` | boolean | Enable authentication | `false` |
| `providers` | array | List of authentication providers | `["anaconda"]` |
| `default_provider` | string | Default provider to use | `"anaconda"` |

### Custom Provider Example

```toml
[authentication]
enabled = true
providers = ["anaconda", "custom"]
default_provider = "custom"

[authentication.custom]
domain = "auth.example.com"
client_id = "${AUTH_CLIENT_ID}"
client_secret = "${AUTH_CLIENT_SECRET}"
```

### Environment Variables

Use environment variables for sensitive data:

```toml
[authentication.anaconda]
api_key = "${ANACONDA_API_KEY}"
```

Then set the environment variable:
```bash
export ANACONDA_API_KEY="your-key-here"
```

---

## Server Configuration

The `[[servers]]` sections define individual MCP servers to proxy or embed.

### Streamable HTTP Servers

Best for: Remote HTTP-based MCP servers

```toml
[[servers.proxied.streamable-http]]
name = "conda_environments"
url = "http://localhost:4041/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"

# Auto-start configuration
auto_start = true
command = ["environments-mcp-server", "start", "--transport", "streamable-http"]
startup_delay = 3
```

#### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `name` | string | Unique server identifier | **required** |
| `url` | string | Server URL | **required** |
| `timeout` | integer | Connection timeout in seconds | `30` |
| `keep_alive` | boolean | Keep connection alive | `true` |
| `reconnect_on_failure` | boolean | Auto-reconnect on failure | `true` |
| `max_reconnect_attempts` | integer | Maximum reconnection attempts | `10` |
| `health_check_enabled` | boolean | Enable health checks | `false` |
| `mode` | string | Proxy mode | `"proxy"` |
| `auto_start` | boolean | Auto-start server if not running | `false` |
| `command` | array | Command to start server | `null` |
| `startup_delay` | integer | Delay after starting (seconds) | `3` |

### STDIO Servers

Best for: Local command-line tools

```toml
[[servers.proxied.stdio]]
name = "local_tools"
command = ["my-mcp-server", "start", "--verbose"]
restart_policy = "never"
working_directory = "/path/to/workdir"
environment = { PATH = "/usr/local/bin:$PATH" }
```

#### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `name` | string | Unique server identifier | **required** |
| `command` | array | Command and arguments | **required** |
| `restart_policy` | string | When to restart | `"never"` |
| `working_directory` | string | Working directory | Current dir |
| `environment` | table | Environment variables | `{}` |

#### Restart Policies

- `never` - Never restart
- `on-failure` - Restart only on failure
- `always` - Always restart

### SSE Servers

Best for: Remote SSE-based MCP servers

```toml
[[servers.proxied.sse]]
name = "remote_analytics"
url = "https://analytics.example.com/mcp/sse"
auth_token = "${REMOTE_SERVER_TOKEN}"
timeout = 30
retry_interval = 5
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = true
health_check_interval = 60
health_check_endpoint = "/health"
mode = "proxy"
```

#### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `name` | string | Unique server identifier | **required** |
| `url` | string | SSE endpoint URL | **required** |
| `auth_token` | string | Authentication token | `null` |
| `timeout` | integer | Connection timeout | `30` |
| `retry_interval` | integer | Retry delay in seconds | `5` |
| `health_check_interval` | integer | Health check interval | `60` |
| `health_check_endpoint` | string | Health check path | `"/health"` |

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

```toml
# Prefix with server name
template = "{server_name}_{tool_name}"
# Result: conda_create_environment

# Suffix with server name
template = "{tool_name}_{server_name}"
# Result: create_environment_conda

# Include version
template = "{server_name}_{tool_name}_v{version}"
# Result: conda_create_environment_v1
```

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

### Production Configuration

```toml
[composer]
name = "production-mcp"
conflict_resolution = "prefix"
log_level = "WARNING"
port = 8888

[transport]
stdio_enabled = false
sse_enabled = true
sse_path = "/events"
sse_cors_enabled = true

[authentication]
enabled = true
providers = ["anaconda"]
default_provider = "anaconda"

[authentication.anaconda]
domain = "anaconda.com"
api_key = "${ANACONDA_API_KEY}"

[[servers.proxied.streamable-http]]
name = "conda_environments"
url = "http://environments-server:4041/mcp"
timeout = 60
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 5
health_check_enabled = true

[[servers.proxied.sse]]
name = "analytics_server"
url = "https://analytics.prod.example.com/mcp/sse"
auth_token = "${ANALYTICS_TOKEN}"
timeout = 120
health_check_enabled = true
health_check_interval = 300

[tool_manager]
conflict_resolution = "prefix"

[tool_manager.aliases]
create_env = "conda_environments_create_environment"
list_envs = "conda_environments_list_environments"

[api]
enabled = true
path_prefix = "/api/v1"
host = "0.0.0.0"
port = 8888
cors_enabled = true
cors_origins = [
    "https://app.example.com",
    "https://dashboard.example.com"
]
docs_enabled = false
rate_limiting_enabled = true
rate_limit_per_minute = 100
```

### Multi-Server Configuration

```toml
[composer]
name = "multi-server-mcp"
conflict_resolution = "prefix"
log_level = "INFO"
port = 8888

# Local STDIO server
[[servers.proxied.stdio]]
name = "local_tools"
command = ["local-mcp-server", "start"]
restart_policy = "on-failure"

# Remote HTTP server 1
[[servers.proxied.streamable-http]]
name = "conda_environments"
url = "http://localhost:4041/mcp"
auto_start = true
command = ["environments-mcp-server", "start", "--transport", "streamable-http"]

# Remote HTTP server 2
[[servers.proxied.streamable-http]]
name = "jupyter_server"
url = "http://localhost:5041/mcp"
auto_start = true
command = ["jupyter-mcp-server", "start", "--port", "5041"]

# Remote SSE server
[[servers.proxied.sse]]
name = "cloud_resources"
url = "https://cloud.example.com/mcp/sse"
auth_token = "${CLOUD_TOKEN}"

[tool_manager]
conflict_resolution = "prefix"

[tool_manager.aliases]
# Conda shortcuts
create_env = "conda_environments_create_environment"
delete_env = "conda_environments_delete_environment"
# Jupyter shortcuts
new_notebook = "jupyter_server_create_notebook"
run_cell = "jupyter_server_run_cell"

[api]
enabled = true
cors_enabled = true
docs_enabled = true
```
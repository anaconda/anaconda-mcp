# Anaconda MCP Configuration Guide

Anaconda MCP is built on [MCP Compose](https://mcp-compose.datalayer.tech), a unified control plane for composing multiple MCP servers. This guide provides an overview of the configuration options. For the complete reference, see the [MCP Compose Configuration Documentation](https://mcp-compose.datalayer.tech/configuration/).

## Table of Contents

- [Configuration File Overview](#configuration-file-overview)
- [Composer Settings](#composer-settings)
- [Transport Configuration](#transport-configuration)
- [Authentication](#authentication)
- [Server Configuration](#server-configuration)
- [Tool Manager](#tool-manager)
- [Example Configuration](#example-configuration)

---

## Configuration File Overview

Anaconda MCP uses a TOML configuration file (`mcp_compose.toml`) to define server composition, transport protocols, authentication, and tool management.

**Default location:** `src/anaconda_mcp/mcp_compose.toml`

**Custom location:**
```bash
anaconda-mcp serve --config /path/to/custom_config.toml
```

📖 **Reference:** [Configuration File Location](https://mcp-compose.datalayer.tech/configuration/#configuration-file-location)

---

## Composer Settings

The `[composer]` section defines the identity and behavior of your unified MCP server. Set the server name, choose how to handle tool name conflicts when multiple servers expose tools with the same name, and configure logging verbosity.

```toml
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"
port = 8080
```

The `prefix` conflict resolution strategy is recommended—it prefixes tool names with the server name (e.g., `conda_create_environment`) to avoid collisions.

📖 **Reference:** [Composer Section](https://mcp-compose.datalayer.tech/configuration/#composer-section)

---

## Transport Configuration

The `[transport]` section configures how MCP clients connect to your server. Choose between STDIO (subprocess communication) and Streamable HTTP (network-based). SSE is deprecated.

```toml
[transport]
stdio_enabled = true
streamable_http_enabled = true
streamable_http_path = "/mcp"
```

Use STDIO for local development with Claude Desktop or VS Code. Use Streamable HTTP when running as a shared network service.

📖 **Reference:** [Transport Section](https://mcp-compose.datalayer.tech/configuration/#transport-section)

---

## Authentication

The `[authentication]` section protects your MCP endpoint. Anaconda MCP supports Anaconda token authentication out of the box, validating bearer tokens against the Anaconda API.

```toml
[authentication]
enabled = true
providers = ["anaconda"]
default_provider = "anaconda"

[authentication.anaconda]
domain = "anaconda.com"
```

When the authentication is turned ON (`enabled = true), the tool calls will fail unless the two points are satisfied:

- User is authenticated
- MCP_COMPOSE_ANACONDA_TOKEN env var is set to "fallback"

Clients authenticate by including their Anaconda token in the Authorization header:
```
Authorization: Bearer <your_anaconda_token>
```

> Implementation Notes: At the moment, we are not passing the token in the header but instead relying on the keyring to fetch the token. For now, we turn off the authentication by default so users are not forced to log in to use the Anaconda MCP Server.

For local development, set `MCP_COMPOSE_ANACONDA_TOKEN="fallback"` to use your locally stored Anaconda credentials from `anaconda login`.

📖 **Reference:** [Authentication Section](https://mcp-compose.datalayer.tech/configuration/#authentication-section) and [Anaconda Authentication](https://mcp-compose.datalayer.tech/configuration/#anaconda-authentication)

---

## Server Configuration

The `[servers]` section defines the downstream MCP servers that Anaconda MCP composes. Each server's tools become available through the single unified endpoint.

### STDIO Servers

STDIO servers run as subprocesses, providing process isolation. This is the most common pattern.

```toml
[[servers.proxied.stdio]]
name = "environments"
command = ["environments-mcp-server", "start", "--transport", "stdio"]
restart_policy = "on-failure"
```

### Streamable HTTP Servers

Connect to MCP servers running as standalone HTTP services.

```toml
[[servers.proxied.http]]
name = "jupyter"
url = "http://localhost:8888/mcp"
protocol = "streamable-http"
timeout = 30
reconnect_on_failure = true
```

📖 **Reference:** [Servers Section](https://mcp-compose.datalayer.tech/configuration/#servers-section)

---

## Tool Manager

The `[tool_manager]` section fine-tunes how tools are named and organized. Create aliases for friendlier tool names or customize the naming template.

```toml
[tool_manager]
conflict_resolution = "prefix"

[tool_manager.aliases]
create_env = "conda_environments_create_environment"
list_envs = "conda_environments_list_environments"
```

Aliases let you expose tools under shorter, more intuitive names without modifying the underlying servers.

📖 **Reference:** [Tool Manager Section](https://mcp-compose.datalayer.tech/configuration/#tool-manager-section)

---

## Example Configuration

A typical Anaconda MCP development configuration:

```toml
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "DEBUG"
port = 8000

[transport]
stdio_enabled = true
streamable_http_enabled = true
streamable_http_path = "/mcp"

[authentication]
enabled = false

[[servers.proxied.stdio]]
name = "environments"
command = ["environments-mcp-server", "start", "--transport", "stdio"]
restart_policy = "on-failure"

[[servers.proxied.http]]
name = "jupyter"
url = "http://localhost:8888/mcp"
protocol = "streamable-http"
timeout = 30

[tool_manager]
conflict_resolution = "prefix"

[tool_manager.aliases]
create_env = "conda_environments_create_environment"
list_envs = "conda_environments_list_environments"
```

---

## Further Reading

For complete configuration options including authorization, monitoring, REST API, and Web UI settings, see the [MCP Compose Configuration Documentation](https://mcp-compose.datalayer.tech/configuration/).
docs_enabled = true
```
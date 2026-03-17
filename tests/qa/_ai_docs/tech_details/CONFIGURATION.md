# Anaconda MCP - Configuration Guide

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANACONDA_AUTH_API_KEY` | (none) | API key for authentication (alternative to `anaconda login`) |
| `ANACONDA_MCP_ANACONDA_DOMAIN` | (auto) | Anaconda API domain |
| `ANACONDA_MCP_ENVIRONMENT` | production | Environment mode: production/staging |
| `ANACONDA_MCP_LOG_LEVEL` | INFO | Logging level: DEBUG/INFO/WARNING/ERROR |
| `ANACONDA_MCP_SERVICE_NAME` | anaconda-mcp | Service identifier for telemetry |
| `ANACONDA_MCP_SEND_METRICS` | True | Enable/disable telemetry |
| `ANACONDA_MCP_PYTHON_EXECUTABLE` | sys.executable | Python interpreter path |
| `MCP_COMPOSE_CONFIG_DIR` | (package dir) | Config directory for Claude Desktop |

## Configuration Files

### Primary: `mcp_compose.toml.template`
Location: `src/anaconda_mcp/mcp_compose.toml.template`

Contains dynamic placeholders like `{{PYTHON_EXECUTABLE}}` that are rendered at runtime.

### Fallback: `mcp_compose.toml`
Location: `src/anaconda_mcp/mcp_compose.toml`

Static configuration used only if template doesn't exist.

## Configuration Sections

### [composer]
```toml
[composer]
name = "anaconda-mcp"           # Server name
conflict_resolution = "prefix"   # How to handle tool name conflicts
log_level = "INFO"              # Logging verbosity
port = 2391                     # HTTP server port
```

**Conflict Resolution Options:**
- `prefix` - Prepend server name (e.g., `conda_list_environments`)
- `suffix` - Append server name
- `ignore` - Keep original names (may conflict)
- `error` - Fail on conflicts
- `override` - Last wins
- `custom` - Custom mapping

### [transport]
```toml
[transport]
stdio_enabled = true             # Enable STDIO transport
streamable_http_enabled = false  # Enable HTTP transport
sse_enabled = false              # SSE transport (mcp-compose only, not used by anaconda-mcp)
```

### [authentication]
```toml
[authentication]
enabled = false                  # Enable authentication
providers = ["anaconda"]         # Available auth providers
default_provider = "anaconda"    # Default provider

[authentication.anaconda]
domain = "anaconda.com"          # Anaconda domain
```

### [servers.proxied.streamable-http]
```toml
[servers.proxied.streamable-http.conda]
name = "conda"
url = "http://localhost:4041/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
auto_start = true
command = ["{{PYTHON_EXECUTABLE}}", "-m", "environments_mcp_server", "--port", "4041"]
startup_delay = 3
```

**Key Parameters:**
- `url` - Downstream server MCP endpoint
- `auto_start` - Start server automatically if not running
- `command` - Command to start downstream server
- `startup_delay` - Seconds to wait after starting

## CLI Options

### Global Options
```bash
anaconda-mcp -v          # Verbose logging (DEBUG)
anaconda-mcp --help      # Show help
```

### serve Command
```bash
anaconda-mcp serve [OPTIONS]

Options:
  --config PATH    Configuration file path (default: built-in template)
  --host TEXT      Host to bind (default: 127.0.0.1)
  --port INTEGER   Port to bind (default: from config)
  --delay INTEGER  Startup delay in seconds (default: 0)
```

### claude-desktop Commands
```bash
# Setup with STDIO transport (default)
anaconda-mcp claude-desktop setup-config

# Setup with HTTP transport
anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888

# Force overwrite existing
anaconda-mcp claude-desktop setup-config --force

# Remove configuration
anaconda-mcp claude-desktop remove-config

# Show current config
anaconda-mcp claude-desktop show
anaconda-mcp claude-desktop show --name anaconda-mcp

# Show config file path
anaconda-mcp claude-desktop path
```

## Claude Desktop Config Paths

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

## Config File Format (Claude Desktop)

### STDIO Transport
```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/path/to/python",
      "args": ["-m", "anaconda_mcp", "serve"],
      "env": {
        "MCP_COMPOSE_CONFIG_DIR": "/path/to/config/dir"
      }
    }
  }
}
```

### Streamable HTTP Transport
```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "url": "http://localhost:8888/mcp",
      "transport": "streamable-http"
    }
  }
}
```

### STDIO with API Key Authentication

Use this to authenticate without running `anaconda login` (avoids port 8000 conflict — see [KI-026](../_tracking/KNOWN_ISSUES.md#ki-026)):

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/path/to/python",
      "args": ["-m", "anaconda_mcp", "serve", "--delay", "15"],
      "env": {
        "ANACONDA_AUTH_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Alternative**: Add API key to `~/.anaconda/config.toml`:
```toml
[plugin.auth]
api_key = "your-api-key-here"
```

## Claude Desktop Setup Quirks

From internal testing (see [KNOWN_ISSUES.md](../_tracking/KNOWN_ISSUES.md)):

### Required Setting
Users MUST enable in Claude Desktop:
**Settings > Capabilities > Code execution and file creation > Cloud code execution**

Without this, MCP tools won't appear in Claude Desktop.

### Permission Prompts
- First-time use of each conda operation requires granting permission
- This is standard Claude Desktop behavior for MCP tools
- Users should expect multiple permission prompts on first use

### Tool Selection
- When multiple MCP tools are installed, Claude may pick wrong tool
- Recommend users specify "using anaconda-mcp" or "using conda" in requests
- Example: "List my conda environments using anaconda-mcp"

## Configuration Validation Checklist

- [ ] Python executable exists and is correct version (3.10-3.13)
- [ ] Ports not in use by other processes (2391, 4041)
- [ ] Environment variables properly set
- [ ] Claude Desktop config file is valid JSON
- [ ] Downstream servers accessible (if manually started)
- [ ] Anaconda auth token available (if auth enabled)
- [ ] "Code execution and file creation" enabled in Claude Desktop
- [ ] No conflicting MCP tools with similar names

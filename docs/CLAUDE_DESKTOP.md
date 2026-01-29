# Claude Desktop Integration

Anaconda MCP provides built-in CLI commands to configure [Claude Desktop](https://claude.ai/download) for seamless integration. This guide covers installation, configuration, and usage.

## Quick Start

```bash
# Add Anaconda MCP to Claude Desktop
anaconda-mcp claude configure

# Restart Claude Desktop to apply changes
```

That's it! Claude Desktop will now have access to Anaconda MCP tools.

---

## CLI Commands

### `anaconda-mcp claude configure`

Add Anaconda MCP server configuration to Claude Desktop.

```bash
anaconda-mcp claude configure [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config PATH` | Auto-detected | Path to Claude Desktop config file |
| `-n, --name NAME` | `anaconda-mcp` | Name for the MCP server entry |
| `-t, --transport` | `stdio` | Transport type: `stdio` or `streamable-http` |
| `--host HOST` | `localhost` | Host for streamable-http transport |
| `--port PORT` | `8888` | Port for streamable-http transport |
| `--no-backup` | - | Don't create a backup of existing config |
| `-f, --force` | - | Overwrite existing server configuration |
| `--json` | - | Output result as JSON |

**Examples:**

```bash
# Configure with default STDIO transport (recommended)
anaconda-mcp claude configure

# Configure with custom server name
anaconda-mcp claude configure --name my-anaconda-server

# Configure with Streamable HTTP transport
anaconda-mcp claude configure --transport streamable-http --port 9000

# Overwrite existing configuration
anaconda-mcp claude configure --force

# Use custom config file location
anaconda-mcp claude configure --config ~/my-claude-config.json
```

---

### `anaconda-mcp claude uninstall`

Remove Anaconda MCP server configuration from Claude Desktop.

```bash
anaconda-mcp claude uninstall [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config PATH` | Auto-detected | Path to Claude Desktop config file |
| `-n, --name NAME` | `anaconda-mcp` | Name of the MCP server entry to remove |
| `--no-backup` | - | Don't create a backup of existing config |
| `--json` | - | Output result as JSON |

**Examples:**

```bash
# Remove default anaconda-mcp entry
anaconda-mcp claude uninstall

# Remove custom-named server
anaconda-mcp claude uninstall --name my-anaconda-server
```

---

### `anaconda-mcp claude show`

Display the current Claude Desktop configuration.

```bash
anaconda-mcp claude show [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config PATH` | Auto-detected | Path to Claude Desktop config file |
| `-n, --name NAME` | - | Show only this server's configuration |
| `--json` | - | Output as JSON |

**Examples:**

```bash
# Show full configuration
anaconda-mcp claude show

# Show specific server configuration
anaconda-mcp claude show --name anaconda-mcp

# Output as JSON (useful for scripting)
anaconda-mcp claude show --json
```

---

### `anaconda-mcp claude path`

Display the default Claude Desktop configuration file path for your operating system.

```bash
anaconda-mcp claude path
```

**Output by OS:**

| Operating System | Default Path |
|------------------|--------------|
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |

---

## Transport Types

### STDIO (Default)

With STDIO transport, Claude Desktop launches Anaconda MCP as a subprocess. This is the recommended approach for most users.

```bash
anaconda-mcp claude configure --transport stdio
```

**How it works:**
- Claude Desktop starts `anaconda-mcp serve` automatically
- Communication happens via stdin/stdout
- No separate server process to manage

**Generated configuration:**

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

### Streamable HTTP

With Streamable HTTP transport, you run the server independently and Claude Desktop connects over HTTP.

```bash
# Configure with HTTP transport
anaconda-mcp claude configure --transport streamable-http --port 8888

# Start the server separately (in another terminal)
anaconda-mcp serve --port 8888
```

**How it works:**
- You start `anaconda-mcp serve` manually
- Claude Desktop connects to the running server
- Allows multiple clients to share one server

**Generated configuration:**

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

---

## Configuration Backup

By default, the CLI creates a timestamped backup before modifying the configuration:

```
claude_desktop_config.20260127_143022.backup.json
```

To skip backup creation:

```bash
anaconda-mcp claude configure --no-backup
```

---

## Troubleshooting

### Config file not found

If Claude Desktop hasn't been run before, the config file may not exist. The `configure` command will create it automatically.

### Server already exists

If you get an error that the server already exists:

```bash
# Either use --force to overwrite
anaconda-mcp claude configure --force

# Or uninstall first
anaconda-mcp claude uninstall
anaconda-mcp claude configure
```

### Changes not taking effect

Restart Claude Desktop after modifying the configuration:

1. Quit Claude Desktop completely
2. Reopen Claude Desktop
3. The new MCP server should appear in the tools list

### Custom config location

If you have a non-standard Claude Desktop installation:

```bash
anaconda-mcp claude configure --config /custom/path/to/claude_desktop_config.json
```

### Verify configuration

Check the current configuration:

```bash
anaconda-mcp claude show
```

---

## Platform Support

The CLI automatically detects the correct configuration path for:

- ✅ **Linux** - `~/.config/Claude/`
- ✅ **macOS** - `~/Library/Application Support/Claude/`
- ✅ **Windows** - `%APPDATA%\Claude\`

---

## See Also

- [Architecture](./ARCHITECTURE.md) - How Anaconda MCP works
- [Configuration Guide](./CONFIGURATION_GUIDE.md) - Customizing Anaconda MCP
- [MCP Compose Documentation](https://mcp-compose.datalayer.tech) - Full configuration reference

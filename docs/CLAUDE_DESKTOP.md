# Claude Desktop Integration

Anaconda MCP provides CLI commands to configure [Claude Desktop](https://claude.ai/download). Claude Desktop launches Anaconda MCP over stdio; no separate server process or local port is required.

## Quick Start

```bash
# Authenticate and accept Terms first
anaconda login
anaconda mcp terms accept

# Add Anaconda MCP to Claude Desktop
anaconda mcp claude-desktop setup-config

# Restart Claude Desktop to apply changes
```

Claude Desktop will then have access to Anaconda MCP tools.

---

## CLI Commands

### `anaconda mcp claude-desktop setup-config`

Add Anaconda MCP server configuration to Claude Desktop.

```bash
anaconda mcp claude-desktop setup-config [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config PATH` | Auto-detected | Path to Claude Desktop config file |
| `-n, --name NAME` | `anaconda-mcp` | Name for the MCP server entry |
| `--no-backup` | - | Don't create a backup of existing config |
| `-f, --force` | - | Overwrite existing server configuration |
| `--json` | - | Output result as JSON |

**Examples:**

```bash
# Configure the default stdio server
anaconda mcp claude-desktop setup-config

# Configure with custom server name
anaconda mcp claude-desktop setup-config --name my-anaconda-server

# Overwrite existing configuration
anaconda mcp claude-desktop setup-config --force

# Use custom config file location
anaconda mcp claude-desktop setup-config --config ~/my-claude-config.json
```

---

### `anaconda mcp claude-desktop remove-config`

Remove Anaconda MCP server configuration from Claude Desktop.

```bash
anaconda mcp claude-desktop remove-config [OPTIONS]
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
anaconda mcp claude-desktop remove-config
anaconda mcp claude-desktop remove-config --name my-anaconda-server
```

---

### `anaconda mcp claude-desktop show`

Display the current Claude Desktop configuration.

```bash
anaconda mcp claude-desktop show [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --config PATH` | Auto-detected | Path to Claude Desktop config file |
| `-n, --name NAME` | - | Show only this server's configuration |
| `--json` | - | Output as JSON |

**Examples:**

```bash
anaconda mcp claude-desktop show
anaconda mcp claude-desktop show --name anaconda-mcp
anaconda mcp claude-desktop show --json
```

---

### `anaconda mcp claude-desktop path`

Display the default Claude Desktop configuration file path for your operating system.

```bash
anaconda mcp claude-desktop path
```

**Output by OS:**

| Operating System | Default Path |
|------------------|--------------|
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |

---

## Transport

Claude Desktop uses stdio for Anaconda MCP. With stdio, Claude Desktop starts Anaconda MCP as a subprocess and communicates over stdin/stdout.

**How it works:**

- Claude Desktop starts `anaconda mcp serve` or `python -m anaconda_mcp serve` automatically.
- Communication happens through stdio.
- No separate server process, host, or port is configured.
- The server itself mounts conda tools in-process and proxies search with bearer auth.

**Generated configuration:**

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

If Claude Desktop cannot find the user's conda executable, add `CONDA_EXE`:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "/path/to/python",
      "args": ["-m", "anaconda_mcp", "serve"],
      "env": {
        "CONDA_EXE": "/path/to/conda"
      }
    }
  }
}
```

---

## Configuration Backup

By default, the CLI creates a timestamped backup before modifying the configuration:

```text
claude_desktop_config.20260127_143022.backup.json
```

To skip backup creation:

```bash
anaconda mcp claude-desktop setup-config --no-backup
```

---

## Troubleshooting

### Config file not found

If Claude Desktop has not been run before, the config file may not exist. The setup command creates it automatically.

### Server already exists

If you get an error that the server already exists:

```bash
# Either use --force to overwrite
anaconda mcp claude-desktop setup-config --force

# Or uninstall first
anaconda mcp claude-desktop remove-config
anaconda mcp claude-desktop setup-config
```

### Changes not taking effect

Restart Claude Desktop after modifying the configuration:

1. Quit Claude Desktop completely.
2. Reopen Claude Desktop.
3. Confirm the MCP server appears in the tools list.

### Custom config location

```bash
anaconda mcp claude-desktop setup-config --config /custom/path/to/claude_desktop_config.json
```

### Verify configuration

```bash
anaconda mcp claude-desktop show
```

### Authentication or Terms errors

Run:

```bash
anaconda login
anaconda mcp terms accept
```

For headless or managed clients, set `ANACONDA_AUTH_API_KEY`, `ANACONDA_MCP_ACCEPTED_TERMS`, and `ANACONDA_MCP_ACCEPTED_TERMS_VERSION` in the config `env` block.

### Conda executable not found

Set `CONDA_EXE` in the config `env` block. GUI apps often do not inherit shell initialization where conda normally sets this value.

---

## Platform Support

The CLI automatically detects the correct configuration path for:

- ✅ **Linux** - `~/.config/Claude/`
- ✅ **macOS** - `~/Library/Application Support/Claude/`
- ✅ **Windows** - `%APPDATA%\Claude\`

---

## See Also

- [Architecture](./ARCHITECTURE.md) - How Anaconda MCP works
- [Configuration Guide](./CONFIGURATION_GUIDE.md) - Runtime authentication, Terms, and environment variables
- [CLI User Guide](./CLI_USER_GUIDE.md) - Command reference

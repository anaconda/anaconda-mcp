# anaconda-mcp

# CLI Quick Reference

## Commands

### serve
Start MCP servers from configuration file.

```bash
anaconda-mcp serve [--config PATH] [--host HOST] [--port PORT]
```

**Examples:**
```bash
anaconda-mcp serve
anaconda-mcp serve --port 8888
anaconda-mcp -v serve --config custom.toml
```

### compose
Compose multiple MCP servers into one.

```bash
anaconda-mcp compose [OPTIONS]
```

**Options:**
- `-p, --pyproject PATH` - Path to pyproject.toml
- `-n, --name NAME` - Name for composed server
- `-c, --conflict-resolution STRATEGY` - Conflict strategy (prefix/suffix/ignore/error/override)
- `--include SERVER` - Include specific servers (repeatable)
- `--exclude SERVER` - Exclude specific servers (repeatable)
- `-o, --output PATH` - Output file
- `--output-format FORMAT` - Output format (text/json)

**Examples:**
```bash
anaconda-mcp compose
anaconda-mcp compose --name my-server
anaconda-mcp compose --include conda_environments --include jupyter_server
anaconda-mcp compose --exclude legacy_server
anaconda-mcp compose --conflict-resolution prefix --output composed.json --output-format json
```

### discover
Discover available MCP servers.

```bash
anaconda-mcp discover [--pyproject PATH] [--output-format FORMAT]
```

**Examples:**
```bash
anaconda-mcp discover
anaconda-mcp discover --output-format json
anaconda-mcp discover -p /path/to/pyproject.toml
```

## Global Options

```bash
-h, --help          Show help
-v, --verbose       Enable verbose logging
```
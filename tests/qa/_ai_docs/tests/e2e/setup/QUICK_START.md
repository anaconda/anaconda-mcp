# Quick Start

For general installation options (latest release, specific versions, from source) see [INSTALL_OPTIONS.md](../../../tech_details/INSTALL_OPTIONS.md).

> **Before you start**: Verify your conda installation is Miniconda (not full Anaconda) — see [CONDA_SETUP.md](../../../tech_details/CONDA_SETUP.md).

> **Windows users**: Follow [WINDOWS_SETUP.md](./WINDOWS_SETUP.md) — contains Windows-specific commands, Claude Desktop config workarounds, and troubleshooting.

---

## Create the RC Environment

**Versions under test**: `anaconda-mcp=1.0.0.rc.2` · `environments-mcp-server=1.0.0.rc.2` · `anaconda-connector-core=0.1.11` · `anaconda-connector-conda=0.1.11` · `anaconda-connector-utilities=0.1.11`

Run once per Python version required. Replace `X.Y` with `3.10` | `3.11` | `3.12` | `3.13`:

```bash
conda create --name anaconda-mcp-rc2-pyXY \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=X.Y \
  anaconda-mcp=1.0.0.rc.2 \
  environments-mcp-server=1.0.0.rc.2 \
  anaconda-connector-core=0.1.11 \
  anaconda-connector-conda=0.1.11 \
  anaconda-connector-utilities=0.1.11

conda activate anaconda-mcp-rc2-pyXY

# Verify
anaconda-mcp --help
conda list | grep -E "anaconda-mcp|environments-mcp|anaconda-connector|python"
```

> For alternative installation options (transitive dependencies, version pinning) see [PINNING_CONNECTOR_VERSIONS.md](../../../tech_details/PINNING_CONNECTOR_VERSIONS.md).

---

## Configure Claude Desktop

### STDIO Transport (default)

```bash
anaconda-mcp claude-desktop setup-config
# Restart Claude Desktop (Cmd+Q, reopen)
```

Config created:
```json
{"command": "/path/to/python", "args": ["-m", "anaconda_mcp", "serve"]}
```

### HTTP Transport

> **Note [KI-009]**: Claude Desktop does not support HTTP transport. Use **Cursor** or direct API calls. See [KNOWN_ISSUES.md](../../../_tracking/KNOWN_ISSUES.md#ki-009).

**Step 1: Start server**
```bash
# Optional: enable debug logging
export ANACONDA_MCP_LOG_LEVEL=DEBUG

./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
```

**Step 2: Configure client**

**Cursor** — add to `~/.cursor/mcp.json`, then restart Cursor:
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

**Claude Code**:
```bash
claude mcp add --transport http anaconda-mcp http://localhost:8888/mcp
```

**curl**:
```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### Restore STDIO

```bash
anaconda-mcp claude-desktop setup-config --force
```

---

## Verify Server

Expected output (both transport modes):

```
✓ All servers started successfully!
Total tools: 6

🔧 Available Tools:
  • conda_create_environment
  • conda_install_packages
  • conda_list_environment_packages
  • conda_list_environments
  • conda_remove_environment
  • conda_remove_packages
```

Press `Ctrl+C` to stop. If server hangs, see [KI-007](../../../_tracking/KNOWN_ISSUES.md#ki-007).

---

For architecture details, see [PRODUCT_OVERVIEW.md](../../../_product/PRODUCT_OVERVIEW.md).

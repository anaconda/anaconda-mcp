# Quick Start

For general installation options (latest release, specific versions, from source) see [INSTALL_OPTIONS.md](./INSTALL_OPTIONS.md).

---

## Pinned RC Versions — Current Test Cycle

**Versions under test**:
- `anaconda-mcp=1.0.0.rc.1`
- `environments-mcp-server=1.0.0.rc.1`
- `anaconda-connector` — resolved as transitive dependency (version determined by RC package metadata)

Run once per Python version required (3.10, 3.11, 3.12, 3.13). Replace `X.Y` with the target version:

```bash
# Replace X.Y with: 3.10 | 3.11 | 3.12 | 3.13
conda create --name anaconda-mcp-rc-pyXY \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=X.Y \
  anaconda-mcp=1.0.0.rc.1 \
  environments-mcp-server=1.0.0.rc.1

conda activate anaconda-mcp-rc-pyXY

# Verify installed versions (anaconda-connector is a transitive dependency — confirm it resolved)
anaconda-mcp --help
conda list | grep -E "anaconda-mcp|environments-mcp|anaconda-connector|python"
```

> **Note on `anaconda-connector`**: it cannot be requested explicitly — it is not published as a standalone package in the configured channels. It is pulled in as a transitive dependency of `anaconda-mcp`. The version resolved is whatever the RC package declares as compatible. Record the version from `conda list` output for traceability.
>
> **To lock or reproduce a specific `anaconda-connector` version** — after verifying the installed version is correct, export an exact spec and reuse it:
> ```bash
> # Export (includes exact URLs + builds for every package)
> conda list --explicit -n anaconda-mcp-rc-pyXY > spec-exact.txt
>
> # Recreate identical environment on any machine (no solver, fully deterministic)
> conda create --name anaconda-mcp-rc-pyXY --file spec-exact.txt
> ```

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
Server auto-starts when Claude Desktop launches.

### HTTP Transport

> **Note [KI-009]**: Claude Desktop does not support HTTP transport. Use **Cursor** or direct API calls for HTTP testing. See [KNOWN_ISSUES.md](./KNOWN_ISSUES.md#ki-009-claude-desktop-does-not-support-http-transport).

**Step 1: Start HTTP server**
```bash
# Optional: enable debug logging
export ANACONDA_MCP_LOG_LEVEL=DEBUG

./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
```

**Step 2: Configure client**

**Option A - Cursor** (recommended for E2E, see [KI-009](./KNOWN_ISSUES.md#ki-009-claude-desktop-does-not-support-http-transport)):
Add to `~/.cursor/mcp.json`:
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
Then restart Cursor.

**Option B - Claude Code**:
```bash
claude mcp add --transport http anaconda-mcp http://localhost:8888/mcp
```

**Option C - API testing** (curl):
```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### Restore STDIO (after HTTP testing)

```bash
anaconda-mcp claude-desktop setup-config --force
```

---

## Verify Server

### Expected Output (both modes)

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

Press `Ctrl+C` to stop server.

**Troubleshooting**: If server hangs, see [KI-007 in KNOWN_ISSUES.md](./KNOWN_ISSUES.md#ki-007-http-transport-hangs-or-fails-to-connect).

---

For architecture details, see [PRODUCT_OVERVIEW.md](./PRODUCT_OVERVIEW.md).

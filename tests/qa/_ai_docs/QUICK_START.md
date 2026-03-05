# Quick Start

## Option A: Install from Conda Channels

**Use when**: Testing a published release version. No codebase needed.

```bash
# Create environment with all dependencies
conda create --name anaconda-mcp-testing \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  anaconda-mcp environments-mcp-server

# Activate
conda activate anaconda-mcp-testing

# Verify
anaconda-mcp --help

# Check installed versions
conda list | grep -E "anaconda-mcp|environments-mcp"
```

To install specific versions (package and/or Python):
```bash
# Specific package versions
conda create --name anaconda-mcp-testing \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  anaconda-mcp=0.1.2 environments-mcp-server=0.1.7

# Specific Python version (e.g., 3.10, 3.11, 3.12, 3.13)
conda create --name anaconda-mcp-py310 \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=3.10 anaconda-mcp environments-mcp-server
```

---

## Option B: Install from Source

**Use when**: Testing unpublished code (specific branch/tag/commit) OR running pytest suite.

### Step 1: Clone and Select Version

```bash
# Clone repository
git clone git@github.com:anaconda/anaconda-mcp.git
cd anaconda-mcp

# Option: Use latest main
git checkout main && git pull

# Option: Use specific tag
git tag --list
git checkout v0.1.2
```

### Step 2: Setup Environment

```bash
# Add required channels
conda config --add channels conda-forge
conda config --add channels datalayer
conda config --add channels anaconda-cloud/label/dev
conda config --add channels 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/'

# Create dev environment
make setup
conda activate anaconda-mcp-dev

# Verify
anaconda-mcp --help

# Check installed versions
conda list | grep -E "anaconda-mcp|environments-mcp"
```

### Step 3: Run Tests (optional)

```bash
# Run pytest suite
make test

# Run with coverage
make test-coverage
```

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

**Option B - API testing** (curl):
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

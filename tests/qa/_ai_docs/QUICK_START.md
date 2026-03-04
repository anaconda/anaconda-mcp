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

To install a specific version, add version numbers to the command:
```bash
conda create --name anaconda-mcp-testing \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  anaconda-mcp=0.1.2 environments-mcp-server=0.1.7
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

## Verify Server Works

### STDIO Mode (default - recommended)

```bash
# Start server - will auto-connect to downstream and show tools
anaconda-mcp serve
```

**Expected output**:
```
✓ All servers started successfully!
📡 MCP Server Mode: STDIO
Total tools: 6

🔧 Available Tools:
  • conda_create_environment
  • conda_install_packages
  • conda_list_environment_packages
  • conda_list_environments
  • conda_remove_environment
  • conda_remove_packages
```

Press `Ctrl+C` to exit.

### HTTP Mode (known issue)

> **Note**: HTTP transport mode may hang during downstream server connection.
> This is being investigated. Use STDIO mode for Claude Desktop testing.

Test script available at: [scripts/test-http-server.sh](./scripts/test-http-server.sh)

---

For troubleshooting and architecture details, see [LOCAL_DEV_SETUP.md](./LOCAL_DEV_SETUP.md).

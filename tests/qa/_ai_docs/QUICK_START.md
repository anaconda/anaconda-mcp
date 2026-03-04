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

### Option 1: STDIO Mode (default)

```bash
# Start server in foreground - it reads JSON-RPC from stdin
anaconda-mcp serve
```

Server will show available tools and wait for input. Press `Ctrl+C` to exit.

### Option 2: HTTP Mode (for API testing)

Use the test script:
```bash
./tests/qa/_ai_docs/scripts/test-http-server.sh 8888
```

Or manually:
```bash
# Create HTTP config with downstream server
cat > /tmp/http-config.toml << EOF
[composer]
name = "anaconda-mcp"
port = 8888

[transport]
stdio_enabled = false
streamable_http_enabled = true

[[servers.proxied.streamable-http]]
name = "conda"
url = "http://localhost:4041/mcp"
auto_start = true
command = ["$(which python)", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "4041"]
startup_delay = 3
EOF

# Start server with HTTP enabled
anaconda-mcp serve --config /tmp/http-config.toml &
sleep 10

# Test API (note: Accept header required for streamable HTTP)
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Stop server
kill %1
```

**Expected**: 6 tools listed (`conda_list_environments`, `conda_create_environment`, `conda_remove_environment`, `conda_install_packages`, `conda_remove_packages`, `conda_list_environment_packages`).

---

For troubleshooting and architecture details, see [LOCAL_DEV_SETUP.md](./LOCAL_DEV_SETUP.md).

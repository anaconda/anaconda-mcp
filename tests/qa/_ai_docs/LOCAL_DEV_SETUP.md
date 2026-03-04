# Anaconda MCP - Local Development Setup for QA

## Prerequisites

- macOS, Linux, or Windows
- Conda/Miniconda installed
- Git installed
- Python 3.10+ available
- Claude Desktop installed (for E2E testing)

## Understanding the Architecture

Before setup, understand that **anaconda-mcp** is a gateway that proxies to downstream servers:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Your Conda Environment                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   anaconda-mcp (gateway)          environments-mcp-server (downstream)  │
│   ├── CLI interface               ├── conda operations                  │
│   ├── Claude Desktop config       ├── list/create/delete envs           │
│   ├── Authentication              └── install/remove packages           │
│   └── mcp-compose framework                                             │
│              │                              ▲                           │
│              │      auto_start=true         │                           │
│              └──────────────────────────────┘                           │
│                    HTTP localhost:4041                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key point**: Both packages must be installed. `environments-mcp-server` is auto-started by `anaconda-mcp`.

## Setup Options

### Option A: Development from Source (Recommended for QA)

#### 1. Clone Repository
```bash
git clone <repo-url>
cd anaconda-mcp
```

#### 2. Create Development Environment
```bash
make setup
```
This creates conda environment `anaconda-mcp-dev`.

#### 3. Activate Environment
```bash
conda activate anaconda-mcp-dev
```

#### 4. Install in Development Mode
```bash
make install-dev
```

#### 5. Verify Installation
```bash
anaconda-mcp --help
```

### Option B: Install from Conda Channels (For Release Testing)

From internal testing channels:
```bash
# Create testing environment with latest version
conda create --name anaconda-mcp-testing \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  anaconda-mcp environments-mcp-server

# Activate
conda activate anaconda-mcp-testing

# Configure Claude Desktop
anaconda-mcp claude-desktop setup-config
```

### Option C: Update Existing Environment

```bash
conda install -c anaconda-cloud/label/dev \
  anaconda-mcp environments-mcp-server \
  -n anaconda-mcp-testing --force-reinstall
```

## Running the Server

### Option A: Using Installed Package
```bash
# Ensure dev environment is active
conda activate anaconda-mcp-dev

# Start server
anaconda-mcp serve
```

### Option B: Using Source Directly
```bash
# From repo root
PYTHONPATH=src python -m anaconda_mcp serve
```

### Option C: With Custom Port
```bash
anaconda-mcp serve --port 8888
```

### Option D: With Verbose Logging
```bash
anaconda-mcp -v serve
```

## Server Startup Verification

When server starts successfully, you should see:
```
INFO: Starting MCP server...
INFO: Listening on http://127.0.0.1:2391
INFO: Starting downstream server: conda
INFO: Downstream server started on port 4041
```

### What Happens During Startup

1. **anaconda-mcp starts** on port 2391
2. **Reads config** from `mcp_compose.toml.template`
3. **Auto-starts downstream server** (because `auto_start = true`):
   ```bash
   python -m environments_mcp_server start --transport streamable-http --port 4041
   ```
4. **Waits 3 seconds** (`startup_delay = 3`)
5. **Connects to downstream** via HTTP on port 4041
6. **Ready** to accept MCP requests

### Ports Used

| Port | Service | Purpose |
|------|---------|---------|
| 2391 | anaconda-mcp | Main gateway (clients connect here) |
| 4041 | environments-mcp-server | Downstream server (internal) |

### Verifying Both Servers

```bash
# Check anaconda-mcp is responding
curl -s http://localhost:2391/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -c 200

# Check downstream server directly
curl -s http://localhost:4041/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head -c 200
```

## Running Existing Tests

### All Tests
```bash
make test
```

### With Coverage
```bash
make test-coverage
```

### Specific Test File
```bash
pytest tests/test_auth.py -v
```

### Specific Test Function
```bash
pytest tests/test_utils.py::test_render_template_with_placeholder -v
```

## Test Environment Variables

```bash
# Disable telemetry during testing
export ANACONDA_MCP_SEND_METRICS=false

# Use staging environment
export ANACONDA_MCP_ENVIRONMENT=staging

# Enable debug logging
export ANACONDA_MCP_LOG_LEVEL=DEBUG
```

## Useful Make Targets

| Command | Description |
|---------|-------------|
| `make setup` | Create dev conda environment |
| `make install-dev` | Install package with dev deps |
| `make test` | Run all tests |
| `make test-coverage` | Run tests with coverage report |
| `make lint` | Run linter (ruff) |
| `make format` | Format code |
| `make mypy` | Run type checker |
| `make clean` | Remove build artifacts |

## Testing Workflow

### Step 1: Start Server
```bash
# Terminal 1
conda activate anaconda-mcp-dev
anaconda-mcp serve --port 2391
```

### Step 2: Run API Tests
```bash
# Terminal 2
# Quick smoke test
curl -X POST http://localhost:2391/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### Step 3: Run Automated Tests
```bash
# Terminal 2
make test
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :2391
# or
lsof -i :4041

# Kill process
kill <PID>
```

### Environment Not Found
```bash
# Recreate environment
make clean
make setup
conda activate anaconda-mcp-dev
make install-dev
```

### Import Errors
```bash
# Ensure PYTHONPATH is set for source runs
PYTHONPATH=src python -m anaconda_mcp serve
```

### Downstream Server Not Starting

The `environments-mcp-server` is a separate package that anaconda-mcp auto-starts.

```bash
# Check if environments-mcp-server is installed
conda list | grep environments-mcp-server

# If missing, install via conda (PREFERRED)
conda install -c anaconda-cloud/label/dev -c datalayer environments-mcp-server

# Alternative: install via pip (if conda not available)
# pip install environments-mcp-server
```

### Downstream Server Connection Issues

```bash
# 1. Check if downstream server is running
curl -s http://localhost:4041/mcp || echo "Server not responding"

# 2. Check port 4041 is not blocked
lsof -i :4041

# 3. Start anaconda-mcp with verbose logging to see downstream startup
anaconda-mcp -v serve

# Expected log output:
# INFO: Starting downstream server: conda
# INFO: Running command: python -m environments_mcp_server start --transport streamable-http --port 4041
# INFO: Waiting 3 seconds for server startup...
# INFO: Downstream server started on port 4041
```

### Manually Testing Downstream Server

You can start the downstream server manually for debugging:

```bash
# Start environments-mcp-server directly
python -m environments_mcp_server start --transport streamable-http --port 4041

# In another terminal, test it
curl -X POST http://localhost:4041/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Expected: list of tools (list_environments, create_environment, etc.)
```

## Directory Structure Reference

```
anaconda-mcp/
├── src/anaconda_mcp/
│   ├── cli.py                      # CLI commands (serve, claude-desktop, etc.)
│   ├── auth.py                     # Anaconda authentication
│   ├── config.py                   # Settings and environment variables
│   ├── claude_desktop.py           # Claude Desktop config management
│   ├── mcp_compose.toml.template   # Main config (EDIT THIS)
│   └── mcp_compose.toml            # Fallback config
├── tests/
│   ├── test_*.py                   # Unit/integration tests
│   └── qa/_ai_docs/                # QA documentation (this folder)
├── docs/                           # Developer documentation
├── environment.yml                 # Production conda environment
├── environment-dev.yml             # Development conda environment
├── Makefile                        # Build automation
└── pyproject.toml                  # Project config
```

## Downstream Server Configuration

The downstream server is configured in `src/anaconda_mcp/mcp_compose.toml.template`:

```toml
[[servers.proxied.streamable-http]]
name = "conda"                    # Server name (used for tool prefix)
url = "http://localhost:4041/mcp" # Where to connect
auto_start = true                 # Auto-start the server
command = ["{{PYTHON_EXECUTABLE}}", "-m", "environments_mcp_server",
           "start", "--transport", "streamable-http", "--port", "4041"]
startup_delay = 3                 # Wait 3 seconds after starting
```

### Key Configuration Options

| Option | Value | Description |
|--------|-------|-------------|
| `name` | "conda" | Prefix for tools (e.g., `conda_list_environments`) |
| `url` | localhost:4041 | HTTP endpoint for downstream server |
| `auto_start` | true | anaconda-mcp starts the downstream server |
| `startup_delay` | 3 | Seconds to wait before connecting |
| `{{PYTHON_EXECUTABLE}}` | Dynamic | Replaced with current Python path |

### Disabling Auto-Start (Advanced)

If you want to start downstream server manually:

```toml
# In mcp_compose.toml.template
auto_start = false
```

Then start manually:
```bash
# Terminal 1: Start downstream server
python -m environments_mcp_server start --transport streamable-http --port 4041

# Terminal 2: Start anaconda-mcp (will connect to existing server)
anaconda-mcp serve
```

## IDE Setup (Optional)

### VS Code
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.conda/anaconda-mcp-dev/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm
1. Set Project Interpreter to `anaconda-mcp-dev` conda env
2. Mark `src` as Sources Root
3. Mark `tests` as Test Sources Root

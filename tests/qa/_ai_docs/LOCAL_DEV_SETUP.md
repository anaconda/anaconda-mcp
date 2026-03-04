# Anaconda MCP - Local Development Setup for QA

## Prerequisites

- macOS, Linux, or Windows
- Conda/Miniconda installed
- Git installed
- Python 3.10+ available
- Claude Desktop installed (for E2E testing)

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
```bash
# Check if environments-mcp-server is installed
pip show environments-mcp-server

# Install if missing
pip install environments-mcp-server
```

## Directory Structure Reference

```
anaconda-mcp/
├── src/anaconda_mcp/     # Source code
│   ├── cli.py            # CLI commands
│   ├── auth.py           # Authentication
│   ├── config.py         # Configuration
│   └── ...
├── tests/                # Test files
│   ├── test_*.py
│   └── qa/_ai_docs/      # QA documentation (this folder)
├── docs/                 # Developer documentation
├── Makefile              # Build automation
└── pyproject.toml        # Project config
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

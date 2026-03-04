# Quick Start

## Step 1: Clone Repo and Select Version

```bash
# Clone repository
git clone git@github.com:anaconda/anaconda-mcp.git
cd anaconda-mcp

# Option: Use latest main
git checkout main
git pull

# Option: Use specific release tag
git tag --list          # See available tags
git checkout v0.1.2     # Example: checkout specific version
```

---

## Step 2: Install

### Option A: Install from Conda Channels (for QA testing)

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
```

### Option B: Install from Source (for development)

```bash
# Add required channels first
conda config --add channels conda-forge
conda config --add channels datalayer
conda config --add channels anaconda-cloud/label/dev
conda config --add channels 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/'

# Then setup
make setup
conda activate anaconda-mcp-dev
```

---

## Step 3: Verify

```bash
anaconda-mcp --help
```

---

## Step 4: Test Server

```bash
# Start server
anaconda-mcp serve --port 8888 &
sleep 5

# Test API
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Stop server
kill %1
```

## Expected Output

```json
{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"conda_list_environments",...}]}}
```

5 tools should be listed: `conda_list_environments`, `conda_create_environment`, `conda_delete_environment`, `conda_install_packages`, `conda_remove_packages`.

---

For detailed setup options, troubleshooting, and architecture info, see [LOCAL_DEV_SETUP.md](./LOCAL_DEV_SETUP.md).

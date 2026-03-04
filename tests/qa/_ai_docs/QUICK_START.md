# Quick Start

## Install (from source)

```bash
cd /your-path-to-project/anaconda-mcp
make setup
conda activate anaconda-mcp-dev
```

## Verify

```bash
anaconda-mcp --help
```

## Test Server

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

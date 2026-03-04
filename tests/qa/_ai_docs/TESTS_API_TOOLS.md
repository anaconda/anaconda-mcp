# API Tool Tests (All Platforms)

## Overview

Direct API calls to MCP tools - validates tool functionality without Claude Desktop.

- **Platforms**: macOS, Windows (Win365), Linux
- **Priority**: Manual first (Win365), automation if time allows

---

## Setup

### Start Server

```bash
# Start server in dev mode
anaconda-mcp serve --port 8888

# Or with debug logging
ANACONDA_MCP_LOG_LEVEL=DEBUG anaconda-mcp serve --port 8888
```

### Verify Server Ready

```bash
# Initialize session
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"api-test","version":"1.0"}}}'

# List available tools
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

**Expected**: 5 conda tools listed

---

## Tool Tests

### TOOL-001: List Environments

```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"conda_list_environments","arguments":{}}}'
```

**Expected**: JSON array of environments (at minimum: base)

---

### TOOL-002: Create Environment

```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"conda_create_environment","arguments":{"name":"api-test-env","python_version":"3.11"}}}'
```

**Expected**: Success message, environment created

**Verify**:
```bash
conda env list | grep api-test-env
```

---

### TOOL-003: Install Packages

```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"conda_install_packages","arguments":{"env_name":"api-test-env","packages":["numpy","requests"]}}}'
```

**Expected**: Success message, packages installed

**Verify**:
```bash
conda list -n api-test-env | grep numpy
conda list -n api-test-env | grep requests
```

---

### TOOL-004: Remove Packages

```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"conda_remove_packages","arguments":{"env_name":"api-test-env","packages":["requests"]}}}'
```

**Expected**: Success message, package removed

**Verify**:
```bash
conda list -n api-test-env | grep requests  # Should be empty
conda list -n api-test-env | grep numpy     # Should still exist
```

---

### TOOL-005: Delete Environment

```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"conda_delete_environment","arguments":{"name":"api-test-env"}}}'
```

**Expected**: Success message, environment deleted

**Verify**:
```bash
conda env list | grep api-test-env  # Should be empty
```

---

## Error Scenarios

### ERR-001: Create Duplicate Environment

```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"conda_create_environment","arguments":{"name":"base"}}}'
```

**Expected**: Error - environment already exists

---

### ERR-002: Delete Non-Existent Environment

```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"conda_delete_environment","arguments":{"name":"nonexistent-env-xyz"}}}'
```

**Expected**: Error - environment not found

---

### ERR-003: Install Non-Existent Package

```bash
curl -X POST http://localhost:8888/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":12,"method":"tools/call","params":{"name":"conda_install_packages","arguments":{"env_name":"base","packages":["fake-package-xyz123"]}}}'
```

**Expected**: Error - package not found (no pip fallback)

---

## Quick Checklist

### Happy Path (5 tools)
- [ ] TOOL-001: List environments
- [ ] TOOL-002: Create environment
- [ ] TOOL-003: Install packages
- [ ] TOOL-004: Remove packages
- [ ] TOOL-005: Delete environment

### Error Handling
- [ ] ERR-001: Duplicate environment
- [ ] ERR-002: Non-existent environment
- [ ] ERR-003: Non-existent package

---

## Full Test Script

```bash
#!/bin/bash
# API Tool Test Script
# Run on Win365 with Python 3.10

set -e
PORT=8888
BASE_URL="http://localhost:$PORT/mcp"

echo "=== Starting server ==="
anaconda-mcp serve --port $PORT &
SERVER_PID=$!
sleep 10

echo "=== Initialize ==="
curl -sf $BASE_URL -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

echo -e "\n=== TOOL-001: List Environments ==="
curl -sf $BASE_URL -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"conda_list_environments","arguments":{}}}'

echo -e "\n=== TOOL-002: Create Environment ==="
curl -sf $BASE_URL -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"conda_create_environment","arguments":{"name":"api-test-env","python_version":"3.11"}}}'

echo -e "\n=== TOOL-003: Install Packages ==="
curl -sf $BASE_URL -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"conda_install_packages","arguments":{"env_name":"api-test-env","packages":["numpy"]}}}'

echo -e "\n=== TOOL-004: Remove Packages ==="
curl -sf $BASE_URL -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"conda_remove_packages","arguments":{"env_name":"api-test-env","packages":["numpy"]}}}'

echo -e "\n=== TOOL-005: Delete Environment ==="
curl -sf $BASE_URL -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"conda_delete_environment","arguments":{"name":"api-test-env"}}}'

echo -e "\n=== Cleanup ==="
kill $SERVER_PID 2>/dev/null || true

echo -e "\n=== All tests passed ==="
```

---

## CI Automation (Phase 2)

If time allows, add to CI workflow:

```yaml
# .github/workflows/api-tool-tests.yml
name: API Tool Tests

jobs:
  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: conda-incubator/setup-miniconda@v3
        with:
          python-version: '3.11'

      - run: conda install anaconda-mcp environments-mcp-server -y

      - name: Run API tool tests
        run: |
          anaconda-mcp serve --port 8888 &
          sleep 15

          # Test each tool
          curl -sf http://localhost:8888/mcp -X POST \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"conda_list_environments","arguments":{}}}' | grep -q "result"

          echo "API tool tests passed"
```

---

## Platform Coverage

| Test | Win365 (3.10) | macOS (3.11) | Linux CI (3.13) |
|------|---------------|--------------|-----------------|
| TOOL-001 | ✅ Manual | Optional | Phase 2 |
| TOOL-002 | ✅ Manual | Optional | Phase 2 |
| TOOL-003 | ✅ Manual | Optional | Phase 2 |
| TOOL-004 | ✅ Manual | Optional | Phase 2 |
| TOOL-005 | ✅ Manual | Optional | Phase 2 |
| ERR-001-003 | ✅ Manual | Optional | Phase 2 |

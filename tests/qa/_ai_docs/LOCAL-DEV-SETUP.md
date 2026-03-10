# Local Development Setup for Testing

This guide explains how to set up and test `anaconda-mcp` with a locally modified `environments-mcp` (or any other local dependency).

---

## Overview

The test architecture involves two conda environments:

```
anaconda-mcp-qa          → runs pytest (test client)
anaconda-mcp-rc-py313    → runs the MCP servers (anaconda-mcp + environments-mcp)
```

To test local changes to `environments-mcp`, you need to install it in **editable mode** into the server environment.

---

## Step 1: Verify Current Installation

Check what's currently installed in the server environment:

```bash
conda run -n anaconda-mcp-rc-py313 pip list | grep -E "(anaconda-mcp|environments-mcp)"
```

**Example output (before local install):**
```
anaconda-mcp              0.1.dev99+...  /Users/iiliukhina/projects/anaconda-mcp
environments-mcp-server   1.0.0rc1       ← from PyPI, NOT local
```

**Example output (after local install):**
```
anaconda-mcp              0.1.dev99+...  /Users/iiliukhina/projects/anaconda-mcp
environments-mcp-server   0.1.dev221+... /Users/iiliukhina/projects/environments-mcp  ← local path
```

The path at the end indicates whether it's a local editable install.

---

## Step 2: Install Local Package in Editable Mode

### Install environments-mcp from local source

```bash
conda run -n anaconda-mcp-rc-py313 pip install -e /Users/iiliukhina/projects/environments-mcp
```

### Install anaconda-mcp from local source (if needed)

```bash
conda run -n anaconda-mcp-rc-py313 pip install -e /Users/iiliukhina/projects/anaconda-mcp
```

### What `-e` (editable) does

```
Normal install:              Editable install:
pip install pkg              pip install -e /path/to/pkg

site-packages/               site-packages/
└── pkg/                     └── pkg.egg-link → /path/to/pkg/src/
    └── (copied files)
                             /path/to/pkg/src/
                             └── (your actual source files)
```

With editable install:
- Python imports directly from your source directory
- Edit a file → restart server → changes are live immediately
- No need to reinstall after each code change

---

## Step 3: Verify Local Code is Being Used

### Method 1: Check pip list

```bash
conda run -n anaconda-mcp-rc-py313 pip list | grep environments-mcp
```

Should show local path:
```
environments-mcp-server   0.1.dev...  /Users/iiliukhina/projects/environments-mcp
```

### Method 2: Inspect source at runtime

```bash
conda run -n anaconda-mcp-rc-py313 python -c "
from environments_mcp_server.tools.environments import install_packages
import inspect
source = inspect.getsource(install_packages.install_packages)
# Check for specific code you added
if 'asyncio.sleep' in source:
    print('Local patched version is loaded')
else:
    print('WARNING: PyPI version is loaded, not local')
"
```

---

## Step 4: Run Tests

### Option A: Auto-start server (recommended)

```bash
conda activate anaconda-mcp-qa
python -m pytest tests/qa/http_tools/ -v \
  --start-server \
  --server-conda-env anaconda-mcp-rc-py313
```

### Option B: Manual server start

**Terminal 1 — Start server:**
```bash
conda activate anaconda-mcp-rc-py313
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
```

**Terminal 2 — Run tests:**
```bash
conda activate anaconda-mcp-qa
python -m pytest tests/qa/http_tools/ -v
```

---

## Step 5: Clean Up / Reset

### Reinstall from PyPI (discard local changes)

```bash
conda run -n anaconda-mcp-rc-py313 pip install --force-reinstall environments-mcp-server
```

### Clear Python bytecode cache

If changes aren't being picked up:

```bash
find /Users/iiliukhina/projects/environments-mcp -name "*.pyc" -delete
find /Users/iiliukhina/projects/environments-mcp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
```

### Kill stuck server processes

```bash
pkill -9 -f "anaconda-mcp"
pkill -9 -f "environments_mcp"
lsof -ti:8888 | xargs kill -9 2>/dev/null
lsof -ti:4041 | xargs kill -9 2>/dev/null
```

---

## Common Issues

### Issue: Changes not reflected after editing

**Cause:** Python cached the old bytecode or server wasn't restarted.

**Fix:**
1. Clear `__pycache__` directories
2. Kill and restart the server
3. Verify with the runtime inspection method above

### Issue: Wrong version installed

**Cause:** pip installed from PyPI instead of local path.

**Fix:**
```bash
# Uninstall first
conda run -n anaconda-mcp-rc-py313 pip uninstall environments-mcp-server -y

# Reinstall from local
conda run -n anaconda-mcp-rc-py313 pip install -e /Users/iiliukhina/projects/environments-mcp
```

### Issue: Import errors after editable install

**Cause:** Missing dependencies in local project.

**Fix:**
```bash
# Install with dev dependencies
conda run -n anaconda-mcp-rc-py313 pip install -e "/Users/iiliukhina/projects/environments-mcp[dev]"
```

---

## Quick Reference

```bash
# === SETUP ===
# Install both local packages
conda run -n anaconda-mcp-rc-py313 pip install -e /Users/iiliukhina/projects/anaconda-mcp
conda run -n anaconda-mcp-rc-py313 pip install -e /Users/iiliukhina/projects/environments-mcp

# Verify installation
conda run -n anaconda-mcp-rc-py313 pip list | grep -E "(anaconda-mcp|environments-mcp)"

# === TESTING ===
# Run HTTP transport tests
conda run -n anaconda-mcp-qa python -m pytest tests/qa/http_tools/ -v \
  --start-server --server-conda-env anaconda-mcp-rc-py313

# Run STDIO transport tests
conda run -n anaconda-mcp-qa python -m pytest tests/qa/stdio_tools/ -v \
  --server-conda-env anaconda-mcp-rc-py313

# Run specific test
conda run -n anaconda-mcp-qa python -m pytest tests/qa/http_tools/test_guard_proxy_error_hang.py \
  -v -k "test_hang_002" --start-server --server-conda-env anaconda-mcp-rc-py313

# === CLEANUP ===
# Kill servers
pkill -9 -f "anaconda-mcp"; pkill -9 -f "environments_mcp"

# Reset to PyPI version
conda run -n anaconda-mcp-rc-py313 pip install --force-reinstall environments-mcp-server
```

---

## Windows Notes

Replace macOS/Linux commands as follows:

| macOS / Linux | Windows |
|---|---|
| `conda run -n ENV pip ...` | Same (works in Miniconda Prompt) |
| `grep -E "..."` | `findstr /R "..."` |
| `pkill -9 -f "..."` | Use Task Manager or `taskkill /IM python.exe /F` |
| `./scripts/start-http-server.sh` | `python -m anaconda_mcp serve --http --port 8888` |

For full Windows setup including Claude Desktop config workarounds, see [WINDOWS_SETUP.md](./WINDOWS_SETUP.md).

---

## Related Documentation

- [HTTP Transport Tests README](../http_tools/README.md)
- [STDIO Transport Tests README](../stdio_tools/README.md)
- [Known Issues](./KNOWN_ISSUES.md)

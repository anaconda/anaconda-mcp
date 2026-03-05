# API Tools Tests

Direct MCP API tests — validate tool behavior by calling the server over HTTP,
without an LLM client in the loop. Deterministic and repeatable.

---

## What these tests cover

| Test | Checks |
|------|--------|
| `test_err_003a_by_name_no_false_env_not_found` | `conda_install_packages(environment=<name>)` must **not** return "environment not found" when the environment exists |
| `test_err_003a_by_name_returns_error` | `conda_install_packages` must return `is_error=true` for a nonexistent package (no silent pip fallback) |
| `test_err_003b_by_prefix_does_not_hang` | `conda_install_packages(prefix=<path>)` must respond within 60 s — a hang means server is stuck |

Both ERR-003a bugs and the ERR-003b hang were reproduced on 2026-03-05 (macOS,
Streamable HTTP, Python 3.13, Cursor client). See the bug report for details.

---

## Setup (once)

### 1. Create the QA conda environment

```bash
conda env create -f tests/qa/api_tools/environment.yml
```

This creates `anaconda-mcp-qa` with `pytest`, `pytest-html`, and `httpx`.
It does **not** need `anaconda-mcp` installed — the server runs separately.

If the environment already exists and needs updating:

```bash
conda env update -f tests/qa/api_tools/environment.yml --prune
```

---

## Running tests

Always use `python -m pytest` (not bare `pytest`) to avoid picking up a
Homebrew/system pytest that shadows the conda env's installation.

### Option A — pre-started server (default)

```bash
# Terminal 1: start the server
conda activate anaconda-mcp-rc-py313
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888

# Terminal 2: run the tests
conda activate anaconda-mcp-qa
python -m pytest tests/qa/api_tools/ -v
```

### Option B — auto-start server

The test session starts and stops the server automatically using
`tests/qa/_ai_docs/scripts/start-http-server.sh`. The script runs
`anaconda-mcp serve` and auto-starts `environments_mcp_server` as a
subprocess, so the target conda env must have both installed.

**One-time setup** — the server env needs the `anaconda-mcp` CLI and its
runtime dependencies. The CLI entry point (`anaconda-mcp serve`) is defined in
this project's `pyproject.toml`, so the project itself must be installed into
the env. The runtime dependencies are listed in the root `environment.yml`.

```bash
# Step 1: create the env with runtime dependencies
#   Option A — fresh env from environment.yml (name comes from the file)
conda env create -f environment.yml --name anaconda-mcp-rc-py313

#   Option B — update an already-created env
#   (use conda env update, NOT conda install --file)
conda env update -n anaconda-mcp-rc-py313 -f environment.yml

# Step 2: install the anaconda-mcp project itself into the env
#   This registers the 'anaconda-mcp' CLI entry point used by start-http-server.sh
conda run -n anaconda-mcp-rc-py313 pip install -e .
```

**Run with auto-start:**

```bash
# Minimal — uses MCP_SERVER_CONDA_ENV env var or the default 'anaconda-mcp-rc-py313'
conda activate anaconda-mcp-qa
python -m pytest tests/qa/api_tools/ -v --start-server

# Explicit env name via flag
python -m pytest tests/qa/api_tools/ -v \
  --start-server \
  --server-conda-env anaconda-mcp-rc-py313

# Explicit env name via environment variable (set once in your shell profile)
export MCP_SERVER_CONDA_ENV=anaconda-mcp-rc-py313
python -m pytest tests/qa/api_tools/ -v --start-server

# Full example with report metadata
python -m pytest tests/qa/api_tools/ -v \
  --start-server \
  --server-conda-env anaconda-mcp-rc-py313 \
  --transport http \
  --python-version 3.13
```

**What happens automatically** when `--start-server` is set:

```mermaid
sequenceDiagram
    participant pytest
    participant conftest as conftest.py<br/>(mcp_server fixture)
    participant script as start-http-server.sh
    participant proxy as anaconda-mcp serve<br/>(port 8888)
    participant backend as environments_mcp_server<br/>(port 4041)

    pytest->>conftest: session starts
    conftest->>script: conda run -n <server-conda-env> bash start-http-server.sh 8888
    script->>script: write /tmp/http-config.toml
    script->>proxy: anaconda-mcp serve --config /tmp/http-config.toml
    proxy->>backend: spawn subprocess (auto_start=true in config)
    backend-->>proxy: ready on port 4041
    proxy-->>conftest: ready on port 8888
    note over conftest: polls every 2 s, up to 60 s
    conftest-->>pytest: server ready — run tests
    pytest->>pytest: run all tests
    pytest->>conftest: session ends
    conftest->>proxy: SIGTERM to process group
    proxy->>backend: terminates subprocess
```

---

## CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--server-url` | `http://localhost:8888/mcp` | MCP server endpoint. Also reads `MCP_SERVER_URL` env var. |
| `--transport` | `http` | Transport label for the HTML report (only `http` supported). |
| `--python-version` | — | Server Python version label for the report (e.g. `3.13`). |
| `--start-server` | off | Auto-start the server before the session; stop it after. |
| `--server-conda-env` | `anaconda-mcp-rc-py313` | Conda env with `anaconda-mcp` (used with `--start-server`). Also reads `MCP_SERVER_CONDA_ENV` env var. |

### Other examples

```bash
# Different port
python -m pytest tests/qa/api_tools/ -v --server-url http://localhost:9999/mcp

# Remote server
python -m pytest tests/qa/api_tools/ -v --server-url http://myserver:8888/mcp
```

---

## HTML report

Generated after every run at:

```
tests/qa/api_tools/reports/report.html
```

Open in any browser. The report includes:
- Pass/fail status per test with full assertion diffs
- Server URL, transport, and Python version in the metadata header
- Captured stdout (conda env creation logs) in the setup section

---

## Expected results

| Test | Bug present | Bug fixed |
|------|-------------|-----------|
| `test_err_003a_by_name_no_false_env_not_found` | **FAIL** | PASS |
| `test_err_003a_by_name_returns_error` | PASS | PASS |
| `test_err_003b_by_prefix_does_not_hang` | PASS (or **FAIL** with timeout) | PASS |

---

## File structure

```
tests/qa/api_tools/
├── README.md                              ← this file
├── environment.yml                        ← QA conda env (pytest + httpx + pytest-html)
├── pytest.ini                             ← local config (HTML report, no asyncio)
├── .gitignore                             ← ignores reports/*.html and caches
├── conftest.py                            ← CLI options, server fixture, HTML metadata
├── test_guard_install_nonexistent_pkg.py  ← GUARD-001 regression tests
└── reports/
    └── report.html                        ← generated, gitignored
```

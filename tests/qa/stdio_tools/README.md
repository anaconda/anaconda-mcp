# stdio_tools — STDIO Transport Tests

Tests validate MCP tool behavior when the server runs in **STDIO mode** — the
same mode used by Claude Desktop. The test process spawns `mcp-compose` as a
subprocess and communicates with it over stdin/stdout, with no pre-started
HTTP server required.

**Stack under test:**

```
test process  ──stdin/stdout pipe──▶  mcp-compose (STDIO mode)
                                              │
                                   Streamable HTTP (port 4042)
                                              │
                                   environments_mcp_server (auto-started)
```

mcp-compose's **internal** connection to `environments_mcp_server` is
Streamable HTTP in both STDIO and HTTP modes — only the upstream transport
(test process → mcp-compose) differs between the two test suites.

---

## What these tests cover

| Test | Mirrors | Checks |
|------|---------|--------|
| `test_stdio_hang_001_remove_nonexistent_env_does_not_hang` | HTTP HANG-001 | `conda_remove_environment` error response must arrive within 60 s across 20 repeated calls, over STDIO |
| `test_stdio_hang_002_install_into_nonexistent_env_does_not_hang` | HTTP HANG-002 | `conda_install_packages` error response — same guard for a different tool code path |
| `test_stdio_hang_003_server_survives_error_response` | HTTP HANG-003 | server must remain functional after forwarding an error — subsequent calls must also complete |

These tests mirror `tests/qa/api_tools/test_guard_proxy_error_hang.py` over
STDIO transport. See [hang_issue/](../_ai_docs/hang_issue/) for root-cause
analysis and a transport comparison.

---

## Setup

The test environment is the same `anaconda-mcp-qa` conda env used by `api_tools/`.
If it already exists, no additional setup is needed.

```bash
# Create the env (first time only)
conda env create -f tests/qa/stdio_tools/environment.yml

# The server env also needs anaconda-mcp installed
conda env update -n anaconda-mcp-rc-py313 -f environment.yml
conda run -n anaconda-mcp-rc-py313 pip install -e .
```

---

## Run

No pre-started server is needed. The test fixture spawns and tears down
`mcp-compose` automatically, one fresh process per test.

```bash
conda activate anaconda-mcp-qa

# Run all STDIO tests
python -m pytest tests/qa/stdio_tools/ -v -s

# Explicit server env (if not using the default 'anaconda-mcp-rc-py313')
python -m pytest tests/qa/stdio_tools/ -v -s \
  --server-conda-env anaconda-mcp-rc-py313

# With report metadata
python -m pytest tests/qa/stdio_tools/ -v -s \
  --server-conda-env anaconda-mcp-rc-py313 \
  --python-version 3.13
```

### What happens automatically during the run

```
pytest session starts
  └── stdio_server fixture (function-scoped — fresh process per test)
        ├── writes /tmp/anaconda-mcp-*-stdio-config.toml
        ├── spawns: conda run -n anaconda-mcp-rc-py313 anaconda-mcp serve --config <file>
        │          stdin=PIPE  stdout=PIPE  stderr=PIPE
        ├── mcp-compose auto-starts environments_mcp_server on port 4042 (~5 s)
        ├── sends MCP initialize → reads response (45 s timeout)
        ├── sends notifications/initialized
        └── yields subprocess to tests

  └── test runs (STDIO JSON-RPC over the pipe)

  └── stdio_server fixture teardown
        ├── SIGTERM to process group
        └── deletes temp config file
```

The fixture is **function-scoped** so each test gets a clean process. Tests
that trigger a proxy hang corrupt mcp-compose's internal state permanently —
isolating each test to its own subprocess prevents cascading failures.

---

## CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--server-conda-env` | `anaconda-mcp-rc-py313` | Conda env with `anaconda-mcp` installed. Also reads `MCP_SERVER_CONDA_ENV` env var. |
| `--python-version` | — | Server Python version label for the HTML report. |

---

## Expected results

| Test | Bug present | Bug fixed |
|------|-------------|-----------|
| `test_stdio_hang_001_remove_nonexistent_env_does_not_hang` | **PASS** or **FAIL** (tool-path dependent) | PASS |
| `test_stdio_hang_002_install_into_nonexistent_env_does_not_hang` | **FAIL** (TimeoutError) | PASS |
| `test_stdio_hang_003_server_survives_error_response` | **FAIL** (health step hangs) | PASS |

A FAIL indicates proxy corruption in mcp-compose's internal HTTP pool to
`environments_mcp_server`. A PASS confirms the fix held. See
[hang_issue/](../_ai_docs/hang_issue/) for full result history and details.

---

## File structure

```
tests/qa/stdio_tools/
├── README.md               ← this file
├── environment.yml         ← QA conda env (pytest + pytest-html + pytest-timeout; no httpx)
├── pytest.ini              ← local config (HTML report, markers)
├── conftest.py             ← --server-conda-env option, HTML report metadata
├── test_guard_proxy_error_hang_stdio.py  ← KI-011 regression tests (STDIO transport)
└── reports/
    └── report.html         ← generated, gitignored
```

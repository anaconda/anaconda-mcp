# stdio_tools — STDIO Transport Tests

Tests that validate MCP tool behavior when the server runs in **STDIO mode** —
the same mode used by Claude Desktop. The test process spawns `mcp-compose` as
a subprocess and communicates with it directly over stdin/stdout.

---

## How these tests work

```
test process
    │  stdin  (newline-delimited JSON-RPC requests)
    ▼
mcp-compose (STDIO mode, spawned as subprocess)
    │  Streamable HTTP (port 4042)
    ▼
environments_mcp_server (auto-started by mcp-compose)
```

Each test gets a **fresh `mcp-compose` process** (function-scoped fixture). The
fixture writes a STDIO config, spawns the process with `stdin=PIPE / stdout=PIPE`,
completes the MCP handshake, runs the test, then terminates the process. No
pre-started server required.

---

## Why test over STDIO

- **Matches Claude Desktop's transport** — exercises the exact code path Claude
  Desktop uses, not just the HTTP path tested by `http_tools/`.
- **Independent hang detection** — mcp-compose's internal connection to
  `environments_mcp_server` is Streamable HTTP in both modes; STDIO tests
  confirm whether a proxy defect is transport-agnostic or HTTP-specific.
- **No external dependencies** — stdlib only (`subprocess`, `threading`, `json`);
  no httpx, no MCP SDK, no pre-started server. Tests are self-contained and
  portable.
- **Simpler timeout mechanism** — a daemon thread with `readline()` enforces
  a hard per-call deadline; if `mcp-compose` stops writing to stdout the thread
  times out and the test fails immediately.

---

## Setup

The test environment is the same `anaconda-mcp-qa` conda env used by `http_tools/`.
If it already exists, no additional setup is needed.

```bash
# Create the env (first time only)
conda env create -f tests/qa/stdio_tools/environment.yml

# The server env needs anaconda-mcp installed
conda env update -n anaconda-mcp-rc-py313 -f environment.yml
conda run -n anaconda-mcp-rc-py313 pip install -e .
```

---

## Run

```bash
conda activate anaconda-mcp-qa

# Run all STDIO tests
python -m pytest tests/qa/stdio_tools/ -v -s

# Explicit server env
python -m pytest tests/qa/stdio_tools/ -v -s \
  --server-conda-env anaconda-mcp-rc-py313
```

---

## CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--server-conda-env` | `anaconda-mcp-rc-py313` | Conda env with `anaconda-mcp` installed. Also reads `MCP_SERVER_CONDA_ENV` env var. |
| `--python-version` | — | Server Python version label for the HTML report. |

---

## File structure

```
tests/qa/stdio_tools/
├── environment.yml         ← QA conda env (pytest + pytest-html + pytest-timeout; no httpx)
├── conftest.py             ← --server-conda-env option, HTML report metadata
├── test_guard_proxy_error_hang_stdio.py  ← regression tests (STDIO transport)
└── reports/report.html     ← generated, gitignored
```

For test results, known issues, and root-cause details see
[`tests/qa/_ai_docs/hang_issue/`](../_ai_docs/hang_issue/).

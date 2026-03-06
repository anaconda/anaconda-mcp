# stdio_tools — STDIO Transport Test Suite

Regression tests for **KI-011** that exercise `mcp-compose` over **STDIO transport** —
the same transport used by Claude Desktop.

These tests are the mirror image of `tests/qa/api_tools/test_guard_proxy_error_hang.py`.
They were created to determine whether the KI-011 hang is upstream-transport-specific
(HTTP only) or lives in `mcp-compose`'s internal connection pool regardless of how
external clients connect.

**Result (2026-03-06):** The hang **also occurs over STDIO**, at iteration 16/20
(vs iteration 4/20 for HTTP). The bug is in `mcp-compose`'s internal Streamable HTTP
pool to `environments_mcp_server`, not in the upstream transport handler.

---

## Transport architecture under test

```
test process  ──stdin/stdout pipe──▶  mcp-compose (STDIO upstream)
                                              │
                                   Streamable HTTP (port 4042)
                                              │
                                   environments_mcp_server (auto-started)
```

`mcp-compose`'s **internal** connection to `environments_mcp_server` is still
Streamable HTTP — the same proxy code path as the HTTP tests.  Only the upstream
transport (test process → mcp-compose) differs.

---

## Key differences from `api_tools/`

| | `api_tools/` | `stdio_tools/` |
|---|---|---|
| Upstream transport | Streamable HTTP | STDIO (stdin/stdout pipe) |
| Server startup | Pre-started or `--start-server` | Spawned by test fixture itself |
| HTTP server required | Yes (port 8888) | No |
| `httpx` dependency | Yes | No — stdlib only |
| Session ID / headers | Yes (MCP-Session-Id) | No (single stateful pipe) |
| Hang detection | `SIGALRM` (Unix signal) | `threading.Thread` timeout |
| KI-011 result (2026-03-06) | **FAIL** (hang at iter 4, all tests) | HANG-001 **PASS**; HANG-002 **FAIL** iter 16; HANG-003 **FAIL** health step iter 20 |

---

## Setup

The test environment is the same `anaconda-mcp-qa` conda env used by `api_tools/`.
If it already exists, no additional setup is needed.

```bash
# Create the env (first time only)
conda env create -f tests/qa/stdio_tools/environment.yml

# The server env also needs anaconda-mcp installed (same as api_tools/ setup)
conda env update -n anaconda-mcp-rc-py313 -f environment.yml
conda run -n anaconda-mcp-rc-py313 pip install -e .
```

---

## Run

No pre-started server is needed. The test fixture spawns and tears down
`mcp-compose` automatically.

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
  └── stdio_server fixture (module-scoped)
        ├── writes /tmp/anaconda-mcp-*-stdio-config.toml
        ├── spawns: conda run -n anaconda-mcp-rc-py313 anaconda-mcp serve --config <file>
        │          stdin=PIPE  stdout=PIPE  stderr=PIPE
        ├── mcp-compose auto-starts environments_mcp_server on port 4042 (~5 s)
        ├── sends MCP initialize → reads response (45 s timeout)
        ├── sends notifications/initialized
        └── yields subprocess to tests

  └── tests run (STDIO JSON-RPC over the pipe)

  └── stdio_server fixture teardown
        ├── SIGTERM to process group
        └── deletes temp config file
```

---

## CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--server-conda-env` | `anaconda-mcp-rc-py313` | Conda env with `anaconda-mcp` installed. Also reads `MCP_SERVER_CONDA_ENV` env var. |
| `--python-version` | — | Server Python version label for the HTML report. |

---

## Test results (2026-03-06)

Results from Run 6 (2026-03-06) — function-scoped fixture, each test gets a fresh process:

| Test | Mirrors HTTP | Result | Detail |
|------|-------------|--------|--------|
| `test_stdio_hang_001_remove_nonexistent_env_does_not_hang` | HANG-001 | **PASS** | All 20 iterations returned in < 2 s |
| `test_stdio_hang_002_install_into_nonexistent_env_does_not_hang` | HANG-002 | **FAIL** | Hung at iteration **16/20** |
| `test_stdio_hang_003_server_survives_error_response` | HANG-003 | **FAIL** | Health step timed out at iteration **20/20** (failure mode 2) |

**Interpretation:**
- The `remove_environment` error path is resilient over STDIO — no hang in 20 standalone iterations.
- The `install_packages` error path hangs at iteration 16 over STDIO (vs iteration 4 over HTTP).
- HANG-003 reveals failure mode 2: the proxy can corrupt its state while forwarding an error so that the *next* call (even a healthy one) hangs, even when the error call itself returned. This occurred on the 20th cycle after 20 warm-up calls.
- The race condition is **not** upstream-transport-dependent but is **tool-path-dependent**.

**Secondary finding — `isError` propagation over STDIO:**
Over STDIO, `mcp-compose` returns `result.isError = false` for tool errors, embedding
the error payload as a JSON string inside `content[0].text`. Over HTTP, `result.isError`
is `true`. This is a separate, lower-severity issue distinct from KI-011.

Once the KI-011 hang is fixed, these tests serve as a regression guard: a FAIL still
indicates server-side proxy corruption; a PASS confirms the fix held.

---

## File structure

```
tests/qa/stdio_tools/
├── README.md               ← this file
├── environment.yml         ← QA conda env (pytest + pytest-html + pytest-timeout; no httpx)
├── pytest.ini              ← local config (HTML report, markers)
├── conftest.py             ← --server-conda-env option, HTML report metadata
├── test_guard_proxy_error_hang_stdio.py  ← KI-011 negative-control (STDIO transport)
└── reports/
    └── report.html         ← generated, gitignored
```

---

## Related files

| File | Description |
|---|---|
| `tests/qa/api_tools/test_guard_proxy_error_hang.py` | HTTP transport hang tests (primary KI-011 regression) |
| `tests/qa/_ai_docs/BUG-REPORT-KI011-MCP-COMPOSE-PROXY-HANG.md` | Bug report with reproduction steps and findings |
| `tests/qa/_ai_docs/KI-011-HTTP-PROXY-HANG.md` | Full investigation log, diagrams, fix plan |

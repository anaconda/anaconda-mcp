# Reporting and logs — `mcp_tools`

Stack and transports: [`architecture.md`](architecture.md). CLI options: [`configuration.md`](configuration.md). Test design: [`test_design.md`](test_design.md).

---

## HTML report

With **`pytest-html`** installed (listed in **`tests/qa/environment.yml`**), each run writes a **self-contained** HTML report to **`tests/qa/mcp_tools/reports/report.html`**. The path is anchored to this suite’s `conftest.py`, so it is the same whether you invoke pytest from the repo root or from **`tests/qa/mcp_tools`**. Use **`pytest … --html /other/path/report.html`** to override.

---

## Where to read logs

**Green rows:** pytest-html still shows **`"extras": []`** for passing tests — **no** server-log attachment is ever added on success.

### 1. pytest-html extras (named attachments)

On **failed** setup or call, `conftest.py` may append **zero or more** extras (each is the last ~48k chars of a temp file — see `_MCP_SERVER_LOG_TAIL_CHARS` in `conftest.py`). **`pytest-html`** must be installed.

| Profile | `--start-server` | Extras on failure (if that log was registered) |
|---------|------------------|------------------------------------------------|
| **`http-http`** | **yes** | **`mcp-server.log (tail)`** — combined stdout+stderr from **`start-http-server.sh`**. |
| **`http-http`** | **no** (external server) | *(none for HTTP autostart)* — use your own server logs. |
| **`stdio-http`** / **`stdio-stdio`** | *(N/A for HTTP log)* | **`mcp-stdio-module-stderr.log (tail)`** when tests use the module-scoped STDIO server (`call_tool`). **`mcp-stdio-hang-stderr.log (tail)`** when a test uses **`stdio_server`** (`hang_stress` / `call_no_hang_unified`). MCP JSON-RPC stays on **stdout**; only **stderr** is captured to disk. **`--start-server`** does not apply to these paths. |

### 2. Every mode — baseline in the report

| Section | Contents |
|---------|----------|
| **Captured log** (setup / call / teardown) | Test harness loggers: **`conftest`**, **`mcp_client`**, **`stdio_client`**, **`httpx`**, test modules, … |
| **Captured stdout / stderr** | Subprocess output the **test process** inherits (e.g. **`conda`** noise during fixture teardown), not the MCP server log file unless redirected there by the test. |
| **Traceback** | Failure location; for STDIO hang tests, often **`stdio_client._recv`** → **`TimeoutError`** then **`pytest.fail`**. |

### 3. STDIO-only — “hang” = bounded wait

KI-011 / hang regressions show up as **`TimeoutError: _recv: no response within …s`** (no full JSON-RPC line within **`TOOL_TIMEOUT`**) plus the test’s **`Failed: …`** message — that **is** the suite’s definition of a hang for STDIO, not an unbounded pytest wait. On failure, open **`mcp-stdio-*-stderr.log (tail)`** if present — anaconda-mcp / mcp-compose diagnostics on stderr are there; stdout remains the JSON-RPC stream only.

### 4. Scope of log capture

The harness captures **one log stream per fixture** (combined stdout+stderr for HTTP; stderr only for STDIO). There are **no separate pytest-managed log files per downstream subprocess** — if an issue is deep inside the conda sub-server (`anaconda_mcp.conda_mcp_lite`) only, you may need to run the stack manually and inspect those process streams directly.

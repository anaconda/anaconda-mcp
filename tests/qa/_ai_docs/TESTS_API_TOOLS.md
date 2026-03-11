# API Tool Tests — Design Document

## Purpose

**Why this test layer exists:**

API Tool tests verify that MCP tools behave correctly when called directly via the MCP protocol (JSON-RPC over HTTP or STDIO). This layer tests the **server's contract with MCP clients** — the same interface used by Claude Desktop, Cursor, and other MCP-compatible tools.

**What this layer catches:**
- Tool input validation and error handling
- Correct JSON-RPC response structure (success vs error)
- Timeout and hang regressions (server must respond within reasonable time)
- Session state corruption across multiple tool calls
- Transport-specific edge cases (SSE streaming, connection pooling)

**What this layer does NOT test:**
- LLM behavior or prompt engineering
- End-to-end user workflows through Claude Desktop UI
- Installation and packaging

---

## Design Rationale

### Why Test at the MCP Protocol Level?

1. **Deterministic**: No LLM variability — same input always produces same output
2. **Fast feedback**: Seconds per test vs minutes for E2E flows
3. **CI-friendly**: Can run in GitHub Actions without GUI or LLM API calls
4. **Regression-focused**: Catches known issues (KI-002, KI-003, KI-010, KI-011) reliably
5. **Transport-agnostic logic**: Same tool behavior expected over HTTP and STDIO

### Test Categories

| Category | Purpose | Example |
|----------|---------|---------|
| **Happy path** | Tools return expected results for valid inputs | `conda_list_environments` returns env list |
| **Error handling** | Tools return proper errors for invalid inputs | Install nonexistent package → `is_error: true` |
| **Regression guards** | Prevent recurrence of known bugs | KI-011: error response must not hang |
| **Protocol compliance** | JSON-RPC structure, error codes, session handling | Invalid tool → error code -32601 |

---

## Architecture

### Transport Abstraction

Tests should be **transport-agnostic** where possible. The same logical test runs over:
- **Streamable HTTP**: `POST /mcp` with JSON-RPC body
- **STDIO**: Newline-delimited JSON-RPC over stdin/stdout

```
┌─────────────────────────────────────────────────────────┐
│                    Test Specification                    │
│  (what behavior we verify, transport-independent)        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Transport Adapter                      │
│  HTTPClient | STDIOClient (how we send/receive)          │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Server Under Test                       │
│  anaconda-mcp serve (HTTP or STDIO mode)                 │
└─────────────────────────────────────────────────────────┘
```

### CI Matrix Support

Tests support GitHub Actions matrix strategy with transport as a dimension:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    transport: [http, stdio]
```

**Execution model**: Each matrix cell runs on a separate runner, so there are no cross-cell conflicts. Within each cell:

1. Fixture starts ONE MCP server (transport and port configurable)
2. Run ALL tests against that single server instance
3. Fixture tears down server after all tests complete

**Requirements:**
- **Configurable transport**: Via `--transport` CLI option (http or stdio)
- **Configurable port**: Via `--port` CLI option (for HTTP transport)
- **Isolated conda env per cell**: Each Python version uses its own env
- **Session-scoped server fixture**: Manages full server lifecycle

### Server Lifecycle via Fixture

The `mcp_server` fixture manages the full server lifecycle — no external scripts needed:

```python
@pytest.fixture(scope="session")
def mcp_server(request):
    """Start server, wait for ready, yield, teardown."""
    transport = request.config.getoption("--transport")
    port = request.config.getoption("--port")

    if transport == "http":
        proc = subprocess.Popen(
            ["anaconda-mcp", "serve", "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        _wait_for_ready(f"http://localhost:{port}/mcp")
    else:  # stdio
        proc = subprocess.Popen(
            ["anaconda-mcp", "serve"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        )

    yield proc
    proc.terminate()
    proc.wait(timeout=10)
```

**Benefits of fixture-only approach:**
- **Platform-independent**: Python `subprocess` works on Linux, macOS, Windows
- **Automatic cleanup**: pytest guarantees teardown even on test failure
- **No script maintenance**: single source of truth for server startup
- **Closer to reality**: starts server the same way a user would

### Fixture Scopes

| Fixture | Scope | Reason |
|---------|-------|--------|
| `mcp_server` | session | Server startup is expensive (~10s); one per test run |
| `mcp_client` | session | Transport adapter (HTTP or STDIO); matches server |
| `session_id` | module | Each test file gets isolated MCP session |
| `conda_env` | module | Env creation is expensive (~30s) |
| `fresh_session_id` | function | For tests that corrupt session state |

---

## Platform Considerations

### OS-Specific Behavior

| Aspect | Linux/macOS | Windows |
|--------|-------------|---------|
| Process signals | `SIGTERM` for cleanup | `taskkill` or process handle |
| Path separators | `/` | `\` (use `pathlib`) |
| Conda activation | `conda run -n env` | Same, but shell differences |
| STDIO line endings | `\n` | `\r\n` possible |

### Python Version Differences

- **3.10**: Baseline — must work
- **3.11-3.13**: May have asyncio/typing changes
- Tests should not rely on version-specific features

---

## Example Scenarios (Illustrative)

These examples show the **type** of tests, not an exhaustive list:

### Happy Path Example
```python
def test_list_environments_returns_base(session_id):
    """conda_list_environments must include 'base' environment."""
    response = call_tool("conda_list_environments", {}, session_id)
    envs = parse_result(response)["environments"]
    assert any(e["name"] == "base" for e in envs)
```

### Error Handling Example
```python
def test_install_nonexistent_package_returns_error(conda_env, session_id):
    """Installing a fake package must return is_error=true, not hang."""
    response = call_tool(
        "conda_install_packages",
        {"environment": conda_env["name"], "packages": ["nonexistent-xyz"]},
        session_id,
    )
    assert parse_result(response)["is_error"] is True
```

### Regression Guard Example
```python
@pytest.mark.timeout(60)
def test_error_response_does_not_hang(fresh_session_id):
    """KI-011: server must respond within timeout after error."""
    for _ in range(10):
        response = call_tool(
            "conda_remove_environment",
            {"prefix": "/nonexistent/path"},
            fresh_session_id,
        )
        assert parse_result(response)["is_error"] is True
```

---

## Current Implementation Status

### What Exists
- `tests/qa/http_tools/`: HTTP transport tests with pytest fixtures
- `tests/qa/stdio_tools/`: STDIO transport tests (parallel structure)
- Regression tests for KI-002, KI-003, KI-010, KI-011

### Known Issues in Test Design
1. **Duplication**: `http_tools/common/` and `stdio_tools/common/` have overlapping code
2. **Transport coupling**: Tests organized by transport, not by functionality

### Recommended Structure (Unified)

```
tests/qa/
├── conftest.py                 # Server fixture, transport selection
├── common/
│   ├── clients/
│   │   ├── base.py             # MCPClient protocol (interface)
│   │   ├── http_client.py      # HTTP transport implementation
│   │   └── stdio_client.py     # STDIO transport implementation
│   ├── constants/              # Shared test data, tool names
│   └── validators/             # Response validation helpers
├── test_tools.py               # Tool tests (transport-agnostic)
└── test_regressions.py         # KI-xxx regression tests
```

**Key changes:**
- One test file, transport selected via `--transport` option
- `mcp_client` fixture returns HTTPClient or STDIOClient based on transport
- Tests use `mcp_client.call_tool()` — don't know which transport

CLI and Config tests live in separate directories (`tests/qa/cli/`, `tests/qa/config/`) — see their respective design docs.

---

## Running Tests

### Local Development
```bash
# HTTP transport
pytest tests/qa/ --transport http --port 9888 -v

# STDIO transport
pytest tests/qa/ --transport stdio -v
```

### CI Invocation
```bash
pytest tests/qa/ \
  --transport ${TRANSPORT} \
  --port ${PORT} \
  -v
```

The fixture handles server startup, readiness check, and teardown automatically.

### Server Log Collection

The fixture captures server logs for debugging test failures:

```python
@pytest.fixture(scope="session")
def mcp_server(request, tmp_path_factory):
    log_dir = tmp_path_factory.mktemp("logs")
    log_file = log_dir / "mcp-server.log"

    proc = subprocess.Popen(
        ["anaconda-mcp", "serve", "--port", str(port)],
        stdout=log_file.open("w"),
        stderr=subprocess.STDOUT,
        env={**os.environ, "ANACONDA_MCP_LOG_LEVEL": "DEBUG"},
    )
    yield proc
    # Log file available for inspection on failure
```

Logs are attached to pytest HTML report on test failure.

---

## Related Documents

- [TESTS_CLI.md](./TESTS_CLI.md) — CLI command tests (no server required)
- [TESTS_CONFIG.md](./TESTS_CONFIG.md) — Configuration and environment variable tests
- [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) — Bug references for regression tests

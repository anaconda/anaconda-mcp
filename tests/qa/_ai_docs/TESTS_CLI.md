# CLI Tests — Design Document

## Purpose

**Why this test layer exists:**

CLI tests verify that the `anaconda-mcp` command-line interface works correctly across all platforms. This layer tests the **user-facing CLI contract** — the commands users run in their terminal before connecting any MCP client.

**What this layer catches:**
- Command parsing and argument handling
- Help text and version output
- Exit codes for success/failure
- Platform-specific path resolution
- Config file generation (`setup-config`)

**What this layer does NOT test:**
- MCP protocol behavior (covered by API Tool tests)
- Tool functionality (covered by API Tool tests)
- Environment variable parsing (covered by Config tests)
- LLM integration

---

## Design Rationale

### Why a Separate CLI Test Layer?

1. **No server required**: Tests run against the CLI binary directly
2. **Fast execution**: Milliseconds per test (no network, no server startup)
3. **Installation verification**: Confirms the package is correctly installed
4. **Platform parity**: Same commands must work on Linux, macOS, Windows
5. **User experience**: Validates what users see before any MCP interaction

### Test Categories

| Category | Purpose | Example |
|----------|---------|---------|
| **Command structure** | Subcommands and flags work | `anaconda-mcp serve --help` |
| **Path resolution** | OS-specific paths correct | `claude-desktop path` returns right location |
| **Config generation** | Generate valid config files | `setup-config` creates valid JSON |
| **Exit codes** | Proper return codes | Invalid args → non-zero exit |

---

## Architecture

### Test Independence

CLI tests should be **stateless** and **independent**:
- Each test starts fresh (no reliance on prior test state)
- Tests clean up any files they create
- No server processes required

### Subprocess Execution

Tests invoke the CLI as a subprocess to match real user behavior:

```python
def test_help_exits_zero():
    result = subprocess.run(
        ["anaconda-mcp", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
```

### CI Matrix Support

CLI tests run across OS and Python versions (no transport dimension — CLI tests don't need a server):

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
```

---

## Platform Considerations

### Shell and Process Differences

| Aspect | Linux/macOS | Windows |
|--------|-------------|---------|
| Executable extension | none | `.exe` |
| Background process | `&` | `start /b` |
| Process group | `start_new_session=True` | `CREATE_NEW_PROCESS_GROUP` |

For OS-specific config paths, see [TESTS_CONFIG.md](./TESTS_CONFIG.md#default-paths-by-os).

---

## Example Scenarios (Illustrative)

### Command Structure Example
```python
def test_serve_requires_no_args():
    """'serve' subcommand works with defaults."""
    result = subprocess.run(
        ["anaconda-mcp", "serve", "--help"],
        capture_output=True,
    )
    assert result.returncode == 0
    assert b"--port" in result.stdout
```

### Path Resolution Example
```python
def test_claude_desktop_path_matches_platform():
    """'claude-desktop path' returns OS-appropriate path."""
    result = subprocess.run(
        ["anaconda-mcp", "claude-desktop", "path"],
        capture_output=True,
        text=True,
    )
    path = Path(result.stdout.strip())

    if sys.platform == "darwin":
        assert "Library/Application Support/Claude" in str(path)
    elif sys.platform == "win32":
        assert "Claude" in str(path) and "AppData" in str(path)
    else:
        assert ".config/Claude" in str(path)
```

### Config Generation Example
```python
def test_setup_config_creates_valid_json(tmp_path):
    """'setup-config' generates parseable JSON."""
    config_path = tmp_path / "claude_desktop_config.json"

    # Mock the config path (platform-specific implementation)
    result = subprocess.run(
        ["anaconda-mcp", "claude-desktop", "setup-config"],
        capture_output=True,
        env={**os.environ, "CLAUDE_CONFIG_PATH": str(config_path)},
    )

    assert config_path.exists()
    config = json.loads(config_path.read_text())
    assert "mcpServers" in config
```

---

## Execution Model

### Test Isolation

```
┌─────────────────────────────────────────────────────────┐
│                      Test Process                        │
│  pytest runner (no server, no network)                   │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼ subprocess.run()
┌─────────────────────────────────────────────────────────┐
│                  anaconda-mcp CLI                        │
│  Executes command, writes to stdout/stderr, exits        │
└─────────────────────────────────────────────────────────┘
```

### Fixture Strategy

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `tmp_path` | function | pytest built-in for temp files |
| `installed_cli` | session | Verify `anaconda-mcp` is in PATH |

---

## Current Implementation Status

### What Exists
- Documentation of manual test flows
- Some regression tests inline with API tests

### What's Missing
- Dedicated `tests/qa/cli/` directory
- Systematic coverage of all subcommands
- Windows-specific test paths

### Recommended Structure
```
tests/qa/cli/
├── conftest.py           # CLI-specific fixtures
├── test_help.py          # --help, --version
├── test_serve.py         # serve subcommand flags
├── test_claude_desktop.py # config management
└── test_env_vars.py      # environment variable handling
```

---

## Running Tests

### Local Development
```bash
# Verify CLI is installed
anaconda-mcp --version

# Run CLI tests (no server needed)
pytest tests/qa/cli/ -v
```

### CI Invocation (planned)
```bash
pytest tests/qa/cli/ \
  --platform ${RUNNER_OS} \
  --python-version ${PYTHON_VERSION}
```

---

## Related Documents

- [TESTS_API_TOOLS.md](./TESTS_API_TOOLS.md) — MCP protocol tests (requires server)
- [TESTS_CONFIG.md](./TESTS_CONFIG.md) — Configuration and environment variable tests
- [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) — Bug references for regression tests

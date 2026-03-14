# Configuration Tests — Design Document

## Purpose

**Why this test layer exists:**

Configuration tests verify that anaconda-mcp correctly handles configuration from all sources: environment variables, config files, and CLI flags. This layer tests the **configuration precedence chain** — ensuring the right value wins when multiple sources conflict.

**What this layer catches:**
- Environment variable parsing and validation
- Config file (TOML) loading and merging
- CLI flag override behavior
- Default value correctness per platform
- Configuration error messages

**What this layer does NOT test:**
- Tool functionality (covered by API Tool tests)
- Full server behavior (covered by API Tool tests)
- LLM integration

---

## Design Rationale

### Why a Separate Config Test Layer?

1. **Isolated verification**: Test config parsing without full server startup
2. **Precedence clarity**: Verify CLI > env var > config file > defaults
3. **Platform defaults**: Validate OS-specific default paths
4. **Error quality**: Ensure helpful messages for invalid config
5. **CI matrix**: Config behavior may vary by Python version

### Configuration Precedence

```
┌─────────────────────────────────────────────────────────┐
│  CLI Flags (highest priority)                            │
│  --port 8888 --config custom.toml                        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Environment Variables                                   │
│  ANACONDA_MCP_LOG_LEVEL=DEBUG                            │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Config File (TOML)                                      │
│  [composer] port = 9999                                  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Built-in Defaults (lowest priority)                     │
│  port = 8080, log_level = "INFO"                         │
└─────────────────────────────────────────────────────────┘
```

### Test Categories

| Category | Purpose | Example |
|----------|---------|---------|
| **Environment vars** | Env vars parsed correctly | `ANACONDA_MCP_LOG_LEVEL=DEBUG` |
| **Env var robustness** | Unknown env vars don't crash (KI-004) | Extra vars ignored |
| **Config file** | TOML loaded and applied | `--config custom.toml` |
| **Precedence** | Higher sources override lower | CLI `--port` beats config file |
| **Platform defaults** | OS-specific paths correct | Config dir on Windows vs macOS |
| **Validation** | Invalid config rejected with message | Bad TOML → clear error |

---

## Configuration Sources

### Environment Variables

| Variable | Type | Default | Purpose |
|----------|------|---------|---------|
| `ANACONDA_MCP_LOG_LEVEL` | str | `INFO` | Logging verbosity |
| `ANACONDA_MCP_SEND_METRICS` | bool | `true` | Telemetry toggle |
| `ANACONDA_MCP_PYTHON_EXECUTABLE` | path | auto | Python for generated configs |
| `ANACONDA_MCP_ENVIRONMENT` | str | `production` | API environment |

### Config File (TOML)

```toml
[composer]
name = "anaconda-mcp"
port = 8888
log_level = "DEBUG"

[transport]
stdio_enabled = true
streamable_http_enabled = true

[api]
enabled = false
```

### CLI Flags

```bash
anaconda-mcp serve \
  --port 9999 \
  --config /path/to/config.toml \
  --delay 5 \
  -v  # verbose logging
```

---

## Platform Considerations

### Default Paths by OS

| Path Type | macOS | Linux | Windows |
|-----------|-------|-------|---------|
| Claude config | `~/Library/Application Support/Claude/` | `~/.config/Claude/` | `%APPDATA%\Claude\` |
| Log directory | `~/Library/Logs/` | `~/.local/share/` | `%LOCALAPPDATA%\` |
| Temp files | `/tmp/` | `/tmp/` | `%TEMP%\` |

### Environment Variable Handling

- **Case sensitivity**: Linux/macOS are case-sensitive; Windows is not
- **Path expansion**: `~` and `$HOME` must expand correctly
- **Boolean parsing**: Accept `true`, `false`, `1`, `0`, `yes`, `no`

---

## Example Scenarios (Illustrative)

### Environment Variable Example
```python
def test_log_level_from_env():
    """ANACONDA_MCP_LOG_LEVEL controls verbosity."""
    env = os.environ.copy()
    env["ANACONDA_MCP_LOG_LEVEL"] = "DEBUG"

    result = subprocess.run(
        ["anaconda-mcp", "--help"],
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0
```

### Env Var Robustness Example (KI-004)
```python
def test_unknown_env_vars_ignored():
    """KI-004: random env vars must not cause pydantic errors."""
    env = os.environ.copy()
    env["RANDOM_UNKNOWN_VAR"] = "some_value"
    env["OPENAI_API_KEY"] = "test123"

    result = subprocess.run(
        ["anaconda-mcp", "--help"],
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0
    assert b"ValidationError" not in result.stderr
```

### Config File Example
```python
def test_custom_config_file(tmp_path):
    """--config flag loads custom TOML."""
    config = tmp_path / "test.toml"
    config.write_text("""
[composer]
port = 7777
log_level = "WARNING"
""")

    result = subprocess.run(
        ["anaconda-mcp", "serve", "--config", str(config), "--help"],
        capture_output=True,
    )
    assert result.returncode == 0
```

### Precedence Example
```python
def test_cli_overrides_config_file(tmp_path):
    """CLI --port beats config file port."""
    config = tmp_path / "test.toml"
    config.write_text("""
[composer]
port = 5555
""")

    # Start server briefly to check which port it binds
    proc = subprocess.Popen(
        ["anaconda-mcp", "serve", "--config", str(config), "--port", "6666"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)

    # Verify port 6666 is used, not 5555
    # (implementation: check stderr logs or attempt connection)
    proc.terminate()
```

### Validation Example
```python
def test_invalid_toml_shows_error(tmp_path):
    """Invalid TOML produces helpful error message."""
    config = tmp_path / "bad.toml"
    config.write_text("this is not valid toml [[[")

    result = subprocess.run(
        ["anaconda-mcp", "serve", "--config", str(config)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "toml" in result.stderr.lower() or "parse" in result.stderr.lower()
```

---

## CI Matrix Considerations

Each GitHub Actions matrix cell runs on a separate runner, so configuration tests don't conflict across cells. Within each cell, tests share a clean environment.

### Environment Isolation

```python
@pytest.fixture
def clean_env():
    """Environment without anaconda-mcp vars from outer scope."""
    env = os.environ.copy()
    for key in list(env.keys()):
        if key.startswith("ANACONDA_MCP_"):
            del env[key]
    return env
```

---

## Current Implementation Status

### What Exists
- Documentation of manual test scenarios
- Some env var handling in API tool tests

### What's Missing
- Dedicated `tests/qa/config/` directory
- Systematic precedence testing
- Invalid config error message tests

### Recommended Structure
```
tests/qa/config/
├── conftest.py           # Config test fixtures
├── test_env_vars.py      # Environment variable tests
├── test_config_file.py   # TOML loading tests
├── test_precedence.py    # Override behavior tests
└── test_validation.py    # Error handling tests
```

---

## Running Tests

### Local Development
```bash
# Run config tests (no server needed for most)
pytest tests/qa/config/ -v

# Test specific env var
ANACONDA_MCP_LOG_LEVEL=DEBUG pytest tests/qa/config/test_env_vars.py -v
```

### CI Invocation (planned)
```bash
pytest tests/qa/config/ \
  --platform ${RUNNER_OS} \
  --python-version ${PYTHON_VERSION}
```

---

## Related Documents

- [TESTS_API_TOOLS.md](./TESTS_API_TOOLS.md) — MCP protocol tests
- [TESTS_CLI.md](./TESTS_CLI.md) — CLI command tests
- [CONFIGURATION.md](../../tech_details/CONFIGURATION.md) — Full configuration reference
- [KNOWN_ISSUES.md](../../KNOWN_ISSUES.md) — KI-004 regression reference

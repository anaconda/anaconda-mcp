# Configuration and CI — `mcp_tools`

How to configure and run the suite: pytest flags, env vars, and CI setup.

---

## Pytest CLI flags and env vars

Every flag has an equivalent **env var** that takes effect when the flag is not passed. Use env vars when:

- **CI / pipeline matrix** — pipeline tools (GitHub Actions, Jenkins) inject env vars per job natively.
- **Persistent session** — `export MCP_SERVER_CONDA_ENV=anaconda-mcp-server` once, run pytest many times.
- **`conda run` without activation** — env vars can be prepended to `conda run -n … pytest …`; CLI flags cannot be set from outside the env the same way.

| CLI flag | Env var | Required? | Default | Purpose |
|----------|---------|-----------|---------|---------|
| `--mcp-profile` | `MCP_PROFILE` | No | `stdio-stdio` | Native stdio profile label: `stdio-stdio` or `stdio` — see [`architecture.md`](architecture.md) |
| `--server-conda-env` | `MCP_SERVER_CONDA_ENV` | Yes | `anaconda-mcp-server` | Conda env that holds `anaconda-mcp` |
| `--skip-hang-stress` | `MCP_QA_SKIP_HANG_STRESS` | No | `0` (set to `1` to enable) | Skip `hang_stress`-marked tests; also: `-m "not hang_stress"` |

Implementation: [`conftest.py`](../conftest.py) (`pytest_addoption`).

---

## Examples

| Scenario | Command |
|----------|---------|
| `stdio-stdio` — minimal (no URL needed) | `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio --server-conda-env anaconda-mcp-server` |
| `stdio-stdio` — skip hang-stress for a faster run | `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio --server-conda-env anaconda-mcp-server --skip-hang-stress` |
| Env var style, no env activation needed | `MCP_PROFILE=stdio-stdio MCP_SERVER_CONDA_ENV=anaconda-mcp-server MCP_QA_SKIP_HANG_STRESS=1 conda run -n anaconda-mcp-qa pytest tests/qa/mcp_tools -o addopts=` |

---

## CI integration

### Matrix

Run the suite across Python versions as independent matrix cells:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    mcp-profile: [stdio-stdio]
```

Each cell spawns `anaconda-mcp serve` over stdio, runs the tool tests, then tears it down. Hang-stress tests use a **function-scoped** fresh stdio process per test.

### Platform notes

| Aspect | Linux / macOS | Windows |
|--------|---------------|---------|
| Process cleanup | `SIGTERM` | process handle / `taskkill` |
| Path separators | `/` | `\` — use `pathlib` in test helpers |
| STDIO line endings | `\n` | `\r\n` possible — handled by JSON-RPC framing |
| Conda run | `conda run -n env` | same; may need `--no-capture-output` |

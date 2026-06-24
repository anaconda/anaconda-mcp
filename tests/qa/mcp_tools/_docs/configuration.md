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
| `--mcp-profile` | `MCP_PROFILE` | No | `http-http` | Transport matrix row: `http-http`, `stdio-http`, `stdio-stdio` — see [`architecture.md`](architecture.md) |
| `--server-url` | `MCP_SERVER_URL` | No | `http://localhost:9888/mcp` | MCP endpoint — used only when **① is HTTP** (`http-http`) |
| `--compose-port` | `MCP_COMPOSE_PORT` | No | `9888` | Outer HTTP port embedded in generated `http-http` composer config |
| `--server-conda-env` | `MCP_SERVER_CONDA_ENV` | **Yes for STDIO profiles and `--start-server`** | `anaconda-mcp-server` | Conda env that holds all server products |
| `--start-server` | `MCP_QA_START_SERVER` | No | `0` (set to `1` to enable) | Auto-start HTTP server via `start-http-server.sh` (`http-http` only); requires `--server-conda-env` |
| `--skip-hang-stress` | `MCP_QA_SKIP_HANG_STRESS` | No | `0` (set to `1` to enable) | Skip `hang_stress`-marked tests; also: `-m "not hang_stress"` |

Implementation: [`conftest.py`](../conftest.py) (`pytest_addoption`).

---

## Examples

| Scenario | Command |
|----------|---------|
| `http-http` — auto-start server, default URL / ports | `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=http-http --start-server --server-conda-env anaconda-mcp-server` |
| `http-http` — external server, custom URL | `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=http-http --server-url http://localhost:9888/mcp` |
| `stdio-stdio` — minimal (no URL needed) | `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio --server-conda-env anaconda-mcp-server` |
| `stdio-stdio` — skip hang-stress for a faster run | `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio --server-conda-env anaconda-mcp-server --skip-hang-stress` |
| Any profile — env var style, no env activation needed | `MCP_PROFILE=stdio-stdio MCP_SERVER_CONDA_ENV=anaconda-mcp-server MCP_QA_SKIP_HANG_STRESS=1 conda run -n anaconda-mcp-qa pytest tests/qa/mcp_tools -o addopts=` |
| `http-http` — auto-start via env vars | `MCP_PROFILE=http-http MCP_QA_START_SERVER=1 MCP_SERVER_CONDA_ENV=anaconda-mcp-server conda run -n anaconda-mcp-qa pytest tests/qa/mcp_tools -o addopts=` |

---

## CI integration

### Matrix

Run the suite across all profiles and Python versions as independent matrix cells:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    mcp-profile: [http-http, stdio-http, stdio-stdio]
```

Each cell spawns one mcp-compose process with the profile's generated TOML, runs the same tool tests through the matching adapter, then tears down. Hang-stress tests use a **function-scoped** fresh process per test (STDIO profiles only).

### Platform notes

| Aspect | Linux / macOS | Windows |
|--------|---------------|---------|
| Process cleanup | `SIGTERM` | process handle / `taskkill` |
| Path separators | `/` | `\` — use `pathlib` in test helpers |
| STDIO line endings | `\n` | `\r\n` possible — handled by JSON-RPC framing |
| Conda run | `conda run -n env` | same; may need `--no-capture-output` |

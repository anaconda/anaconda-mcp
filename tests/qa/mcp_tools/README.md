# mcp_tools — native stdio MCP tool tests

One suite for the native stdio MCP server. Architecture, configuration, test design, and reporting details live under [`_docs/`](_docs/index.md).

## Profiles

`anaconda-mcp serve` composes natively on FastMCP (conda tools mounted in-process,
the remote `search` server proxied) and is **stdio-only** — there is no mcp-compose
config and no HTTP transport. The harness spawns `anaconda-mcp serve` directly over
stdio (no `--config`). `--mcp-profile` is retained only as a pytest/CI report label:

| Profile | Transport |
|---------|-----------|
| `stdio-stdio` (default) | STDIO → native `anaconda-mcp serve` |
| `stdio` | alias of `stdio-stdio` |

## Requirements

You use **two** conda environments:

| Env | Role |
|-----|------|
| **`anaconda-mcp-qa`** | Runs **pytest** (this repo’s `tests/qa/environment.yml`). |
| **`anaconda-mcp-server`** (name is up to you) | Conda env where **`anaconda-mcp`** is installed (it vendors the conda tools) — used for **`conda run -n … anaconda-mcp serve`** (`--server-conda-env`). |

Pass the server env name via **`--server-conda-env`** or **`MCP_SERVER_CONDA_ENV`**. Examples below use **`anaconda-mcp-server`** as a short, generic name.

### Test runner env (`anaconda-mcp-qa`)

```bash
conda env create -f tests/qa/environment.yml              # first time
conda env update -f tests/qa/environment.yml --prune    # after environment.yml changes
conda activate anaconda-mcp-qa
```

Use **`python -m pytest …`** so **`httpx`** / **`pytest`** match the active env (see [`_docs/architecture.md`](_docs/architecture.md) for stack context).

### Server env — how we prepare it

The server env must contain an **installable copy** of:

1. **`anaconda-mcp`** — this repository. It **vendors** the conda MCP tools as `anaconda_mcp.conda_mcp_lite` and pulls in `fastmcp`; no separate `environments-mcp-server` or `anaconda-connector` install is needed.

**Default:** an editable install from a local clone of **`anaconda-mcp`**.

```bash
conda create -n anaconda-mcp-server python=3.13 -y
conda activate anaconda-mcp-server
pip install -e /path/to/anaconda-mcp
```

**More detail:** [`tests/qa/_ai_docs/tech_details/LOCAL-DEV-SETUP.md`](../_ai_docs/tech_details/LOCAL-DEV-SETUP.md), [`INSTALL_OPTIONS.md`](../_ai_docs/tech_details/INSTALL_OPTIONS.md).

**Verify the server env:**

```bash
python -c "import anaconda_mcp; import anaconda_mcp.conda_mcp_lite; print('OK')"
anaconda-mcp --help
```

### Native stdio serve

QA runs start `anaconda-mcp serve` directly over stdio. There is no generated config file and no `--config` flag. See [`_docs/architecture.md`](_docs/architecture.md).

## Examples

From the repo root (with `anaconda-mcp-qa` activated):

```bash
pytest tests/qa/mcp_tools -o addopts= \
  --mcp-profile=stdio-stdio \
  --server-conda-env anaconda-mcp-server
```

Or: `conda run -n anaconda-mcp-qa pytest tests/qa/mcp_tools -o addopts= …`

### Quick suite (no hang stress)

```bash
pytest tests/qa/mcp_tools -o addopts= ... --skip-hang-stress
# or: MCP_QA_SKIP_HANG_STRESS=1 pytest …
# or: pytest … -m "not hang_stress"
```

## HTML report and logs

See [`_docs/reporting.md`](_docs/reporting.md) — default path, pytest-html extras, stderr tails.

## Fixtures

- **`call_tool`** (module): `call_tool(name, arguments)` — stdio JSON-RPC against a module-scoped server.
- **`call_no_hang_unified`**: hang regressions using a fresh stdio server per test.

# mcp_tools — unified MCP tool tests

One suite for all transport profiles. Architecture, configuration, test design, and reporting details live under [`_docs/`](_docs/index.md).

## Profiles

Select setup with **`--mcp-profile`**:

| Profile | Test → mcp-compose | mcp-compose → conda MCP |
|---------|--------------------|---------------------------|
| `http-http` | Streamable HTTP | Streamable HTTP |
| `stdio-http` | STDIO | Streamable HTTP |
| `stdio-stdio` | STDIO | STDIO |

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

1. **`anaconda-mcp`** — this repository. It **vendors** the conda MCP tools as `anaconda_mcp.conda_mcp_lite` (started by mcp-compose over STDIO) and pulls in `fastmcp`; no separate `environments-mcp-server` or `anaconda-connector` install is needed.

**Default:** an editable install from a local clone of **`anaconda-mcp`**.

```bash
conda create -n anaconda-mcp-server python=3.13 -y
conda activate anaconda-mcp-server
pip install -e /path/to/anaconda-mcp
```

**Pinning `mcp-compose`** (fork / branch / git URL) in the same env overrides PyPI—important for **stdio-stdio** proxy behavior. Verify with `python -c "import mcp_compose; print(mcp_compose.__file__)"`.

**More detail:** [`tests/qa/_ai_docs/tech_details/LOCAL-DEV-SETUP.md`](../_ai_docs/tech_details/LOCAL-DEV-SETUP.md), [`INSTALL_OPTIONS.md`](../_ai_docs/tech_details/INSTALL_OPTIONS.md).

**Verify the server env:**

```bash
python -c "import anaconda_mcp; import anaconda_mcp.conda_mcp_lite; print('OK')"
anaconda-mcp --help
```

### Packaged `mcp_compose.toml` vs QA

The file **`src/anaconda_mcp/mcp_compose.toml`** is a **packaged default** when users run `anaconda-mcp serve` without a custom config. **QA runs do not select transport by editing that file.** Tests generate TOML from **`tests/qa/shared/mcp_compose_profiles.py`**, write a temp file, and run `anaconda-mcp serve --config <file>`. See [`_docs/architecture.md`](_docs/architecture.md).

## Examples

From the repo root (with `anaconda-mcp-qa` activated):

```bash
pytest tests/qa/mcp_tools -o addopts= \
  --mcp-profile=http-http \
  --server-url http://localhost:9888/mcp \
  --start-server --server-conda-env anaconda-mcp-server

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

- **`call_tool`** (module): `call_tool(name, arguments)` — HTTP or STDIO from profile.
- **`call_no_hang_unified`**: hang regressions; HTTP uses `fresh_session_id`, STDIO uses a fresh `stdio_server` per test.
- **`session_id`**: set only for `http-http` (MCP session header); otherwise `None`.

Canonical compose TOML generators: `tests/qa/shared/mcp_compose_profiles.py`.

# mcp_tools — unified MCP tool tests

One suite for all transport profiles. Select setup with **`--mcp-profile`**:

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
| **`anaconda-mcp-server`** (name is up to you) | Conda env where **`anaconda-mcp`** and **`environments-mcp-server`** are installed — used for **`conda run -n … anaconda-mcp serve`** (`--server-conda-env`). |

Pass the server env name via **`--server-conda-env`** or **`MCP_SERVER_CONDA_ENV`**. Examples below use **`anaconda-mcp-server`** as a short, generic name.

### Test runner env (`anaconda-mcp-qa`)

Create / update from this repo:

```bash
conda env create -f tests/qa/environment.yml              # first time
conda env update -f tests/qa/environment.yml --prune      # after environment.yml changes
conda activate anaconda-mcp-qa
```

`httpx` is a **conda** dependency (conda-forge) so it stays on the same interpreter as **`pytest`**. If **`pytest`** still fails with **`No module named 'httpx'`**, your shell is probably running a different **`pytest`** than the env’s — use **`python -m pytest …`** (or **`conda run -n anaconda-mcp-qa python -m pytest …`**) so imports match **`which python`**.

### Server env — how we prepare it

This env must contain **installable copies** of:

1. **`anaconda-mcp`** — this repository (`anaconda-mcp`).
2. **`environments-mcp-server`** — provides `python -m environments_mcp_server`, which mcp-compose starts for conda tools.
3. **`anaconda-connector-conda`** (import name **`anaconda_connector_conda`**) — used by **`environments-mcp`** for conda operations. Editable **`pip install -e …/environments-mcp`** does not always pull this in; without it, `python -m environments_mcp_server` fails at import with **`ModuleNotFoundError: No module named 'anaconda_connector_conda'`** and mcp-compose reports **tool registration failed** / **Total tools: 0**.

**Default (assumed here): both packages from local clones.** Pull **`anaconda-mcp`** and **`environments-mcp`** (separate repos), then install both in **editable** mode into **`anaconda-mcp-server`**. `environments-mcp-server` is **not** a dependency of **`anaconda-mcp`** in **`pyproject.toml`**, so you always install it explicitly alongside this repo.

Strings like **`/path/to/anaconda-mcp`** are placeholders — **do not run them verbatim**; use real paths (or **`.`** for this repo when your shell cwd is its root).

```bash
# 1) New env (pick any Python version supported by both packages, e.g. 3.13)
conda create -n anaconda-mcp-server python=3.13 -y
conda activate anaconda-mcp-server

# 2) Editable installs from your local clones (adjust paths)
pip install -e /path/to/anaconda-mcp
pip install -e /path/to/environments-mcp

# Typical layout: sibling directories — from anaconda-mcp repo root:
# pip install -e .
# pip install -e ../environments-mcp

# 3) Conda connector stack (needed by environments-mcp; add if import fails — see list item 3 above)
# conda-forge / anaconda-cloud usually carry the package; channel list may match your org’s environments-mcp docs
conda install -c anaconda-cloud -c conda-forge -c defaults anaconda-connector-conda -y

conda deactivate   # optional before switching back to anaconda-mcp-qa
```

If step 3 is not needed on your machine, **`python -c "import anaconda_connector_conda"`** will already succeed after step 2 — skip or uninstall the extra package only if you know your **`environments-mcp`** install pulls it in.

Without activating: `conda run -n anaconda-mcp-server pip install -e /path/to/anaconda-mcp` and the same for **`environments-mcp`**; run the **`conda install … anaconda-connector-conda`** line the same way with **`conda run -n anaconda-mcp-server`** if required.

**Alternatives (if you are not using local source):** install **`environments-mcp-server`** from conda (**not** on `defaults` alone — e.g. **`conda install -c anaconda-cloud environments-mcp-server`**) or match CI with **`conda install anaconda-mcp environments-mcp-server -y`** when your channels provide both. Public **PyPI** does not ship **`environments-mcp-server`** under that name; prefer conda channels or editable install.

**Verify the server env** (with the env active, or prefix each command with `conda run -n anaconda-mcp-server`):

```bash
conda activate anaconda-mcp-server
python -c "import anaconda_mcp; print('anaconda-mcp OK')"
python -c "import environments_mcp_server; print('environments_mcp_server OK')"
python -c "import anaconda_connector_conda; print('anaconda-connector-conda OK')"
pip list | grep -E "(anaconda-mcp|environments-mcp)"
anaconda-mcp --help
```

You should see **`anaconda-mcp`** and **`environments-mcp-server`** in `pip list`, with **local paths** if you used **`pip install -e`**, and **`import anaconda_connector_conda`** should succeed before you run **`start-http-server.sh`** or pytest with **`--start-server`**.

**More detail** (editable installs, resetting to PyPI, troubleshooting): [`tests/qa/_ai_docs/tech_details/LOCAL-DEV-SETUP.md`](../_ai_docs/tech_details/LOCAL-DEV-SETUP.md).

### Profiles vs `src/anaconda_mcp/mcp_compose.toml`

The file **`src/anaconda_mcp/mcp_compose.toml`** in this repo is a **packaged default / fallback** when someone runs `anaconda-mcp serve` **without** pointing at a custom config. It is **not** what selects transport during these QA runs.

For **`--mcp-profile`** (including **`stdio-stdio`**), tests **generate** mcp-compose TOML from **`tests/qa/shared/mcp_compose_profiles.py`**, write it to a **temporary file**, and spawn:

```text
conda run -n <server-env> … anaconda-mcp serve --config <that-file>
```

So **stdio on mcp-compose** is enforced by that generated file (e.g. `[transport]` with `stdio_enabled = true`, `streamable_http_enabled = false`, plus `[[servers.proxied.stdio]]` for **stdio-stdio**), not by editing `mcp_compose.toml` in `src/`. The pytest process then talks to that process over **stdin/stdout** (newline JSON-RPC) when the profile’s **client edge** is STDIO.

If you run `stdio-stdio` manually outside pytest, use the same idea: **`anaconda-mcp serve --config …`** with TOML from `render_stdio_stdio_toml` / `render_for_profile`, or copy the structure from `mcp_compose_profiles.py`.

## Examples

From the repo root (with `anaconda-mcp-qa` activated):

```bash
# http-http: external or auto-started server on 9888
pytest tests/qa/mcp_tools -o addopts= \
  --mcp-profile=http-http \
  --server-url http://localhost:9888/mcp \
  --start-server --server-conda-env anaconda-mcp-server

# stdio-stdio: subprocess + generated mcp-compose config (see section above)
pytest tests/qa/mcp_tools -o addopts= \
  --mcp-profile=stdio-stdio \
  --server-conda-env anaconda-mcp-server
```

Or without activating:

```bash
conda run -n anaconda-mcp-qa pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio ...
```

### Quick suite (no KI-011 hang stress)

Tests in **`test_guard_*_hang.py`** repeat tool calls many times to stress mcp-compose (KI-011). After a real hang, the proxy can stay unhealthy (~**60s per call** until restart). For a **shorter** run or a **cleaner** server, skip those tests:

```bash
pytest tests/qa/mcp_tools -o addopts= ... --skip-hang-stress
# same: MCP_QA_SKIP_HANG_STRESS=1 pytest tests/qa/mcp_tools -o addopts= ...
# or:    pytest tests/qa/mcp_tools -o addopts= -m "not hang_stress"
```

Hang regressions are marked **`hang_stress`** (and **`slow`** / **`regression`**).

## HTML report

With **`pytest-html`** installed (listed in **`tests/qa/environment.yml`**), each run writes a **self-contained** HTML report to **`tests/qa/mcp_tools/reports/report.html`**. The path is anchored to this suite’s `conftest.py`, so it is the same whether you invoke pytest from the repo root or from **`tests/qa/mcp_tools`**. Use **`pytest … --html /other/path/report.html`** to override.

### Where to read logs

**All-passing runs:** pytest-html still serializes each row with **`"extras": []`**. That is expected — the **`mcp-server.log (tail)`** attachment is **only added when a test’s setup or call fails**. If every test is green, you will **not** see a server log extra anywhere in the report (only **Captured log** / stdout / stderr for the test harness).

| What | Where to look |
|------|----------------|
| **Test harness** (`logging` in tests, `conftest`, `mcp_client`, httpx, …) | In the HTML report: click a test row to expand it — the big text block is the same **Captured log setup / call / teardown** (and stdout/stderr) pytest records. In the terminal, those sections appear in the traceback for failures. |
| **Server process** (anaconda-mcp / mcp-compose + whatever shares stdout/stderr from **`start-http-server.sh`**) | **Only on failed setup or call**, and only with **`--start-server`** + **`http-http`**: an extra named **`mcp-server.log (tail)`** (~last 48k chars). In the table, check the **Links** column for that row, or the expanded details — it is **not** mixed into “Captured log”. One stream covers compose and typical child output; there is no separate pytest-managed file per subprocess. |

If the server was **not** started by pytest (no **`--start-server`**), or you use a **STDIO** profile, there is **no** **`mcp-server.log (tail)`** attachment—inspect whatever process you started yourself.

Design detail: [`tests/qa/_ai_docs/tests/automation/TESTS_API_TOOLS.md`](../_ai_docs/tests/automation/TESTS_API_TOOLS.md) (**Server log collection**).

## Fixtures

- **`call_tool`** (module): `call_tool(name, arguments)` — HTTP or STDIO from profile.
- **`call_no_hang_unified`**: hang regressions; HTTP uses `fresh_session_id`, STDIO uses a fresh `stdio_server` per test.
- **`session_id`**: set only for `http-http` (MCP session header); otherwise `None`.

Canonical compose TOML: `tests/qa/shared/mcp_compose_profiles.py`.

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

#### Pinning **`mcp-compose`** (fork, branch, or exact version)

`anaconda-mcp` declares a **version range** for **`mcp-compose`** in this repo’s **`pyproject.toml`** (currently **`>=0.1.11,<2.0.0`**). A plain **`pip install -e /path/to/anaconda-mcp`** therefore pulls **`mcp-compose`** from **PyPI** like any other dependency.

To use a **different** build — for example a fork with **stdio proxy fixes** ([example PR](https://github.com/j-iliukhina-anaconda/mcp-compose/pull/1)) — install **`anaconda-mcp`** and **`environments-mcp`** as above, then **override** the library in the same env:

```bash
# Editable clone (stdio branch or any local checkout)
pip install -e /path/to/mcp-compose

# Or install a specific Git revision without a full clone (PEP 508)
pip install "mcp-compose @ git+https://github.com/OWNER/mcp-compose.git@BRANCH_OR_TAG"
```

The second **`pip install`** replaces whatever **`mcp-compose`** was installed by **`anaconda-mcp`**. Verify what runs:

```bash
python -c "import mcp_compose; print(mcp_compose.__file__)"
pip show mcp-compose
```

That gives you an independent knob: same **`anaconda-mcp`** and **`environments-mcp`** checkouts, different **`mcp-compose`** transport behavior (**`stdio-stdio`** is especially sensitive to proxy bugs). For more patterns (conda-packaged stack, **`PYTHONPATH`** override, revert), see **[`tests/qa/_ai_docs/tech_details/INSTALL_OPTIONS.md`](../_ai_docs/tech_details/INSTALL_OPTIONS.md)** (Option C).

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

**Green rows:** pytest-html still shows **`"extras": []`** for passing tests — **no** server-log attachment is ever added on success.

**1. pytest-html extras (named attachments)**

On **failed** setup or call, `conftest.py` may append **zero or more** extras (each is the last ~48k chars of a temp file — see `_MCP_SERVER_LOG_TAIL_CHARS`). **`pytest-html`** must be installed.

| Profile | `--start-server` | Extras on failure (if that log was registered) |
|---------|------------------|--------------------------------------------------|
| **`http-http`** | **yes** | **`mcp-server.log (tail)`** — combined stdout+stderr from **`start-http-server.sh`**. |
| **`http-http`** | **no** (external server) | *(none for HTTP autostart)* — use your own server logs. |
| **`stdio-http`** / **`stdio-stdio`** | *(N/A for HTTP log)* | **`mcp-stdio-module-stderr.log (tail)`** when tests use the module-scoped STDIO server (`call_tool`). **`mcp-stdio-hang-stderr.log (tail)`** when a test uses **`stdio_server`** (`hang_stress` / `call_no_hang_unified`). MCP JSON-RPC stays on **stdout**; only **stderr** is captured to disk. **`--start-server`** does not apply to these paths. |

**2. Every mode — same baseline in the report**

| Section | Contents |
|---------|----------|
| **Captured log** (setup / call / teardown) | Test harness loggers: **`conftest`**, **`mcp_client`**, **`stdio_client`**, **`httpx`**, test modules, … |
| **Captured stdout / stderr** | Subprocess output the **test process** inherits (e.g. **`conda`** noise during fixture teardown), not the MCP server log file unless redirected there by the test. |
| **Traceback** | Failure location; for STDIO hang tests, often **`stdio_client._recv`** → **`TimeoutError`** then **`pytest.fail`**. |

**3. STDIO-only — “hang” = bounded wait**

KI-011 / hang regressions show up as **`TimeoutError: _recv: no response within …s`** (no full JSON-RPC line within **`TOOL_TIMEOUT`**) plus the test’s **`Failed: …`** message — that **is** the suite’s definition of a hang for STDIO, not an unbounded pytest wait. On failure, open **`mcp-stdio-*-stderr.log (tail)`** if present — anaconda-mcp / mcp-compose diagnostics on stderr are there; stdout remains the JSON-RPC stream only.

Design detail: [`tests/qa/_ai_docs/tests/automation/TESTS_API_TOOLS.md`](../_ai_docs/tests/automation/TESTS_API_TOOLS.md) (**Server log collection**).

## Fixtures

- **`call_tool`** (module): `call_tool(name, arguments)` — HTTP or STDIO from profile.
- **`call_no_hang_unified`**: hang regressions; HTTP uses `fresh_session_id`, STDIO uses a fresh `stdio_server` per test.
- **`session_id`**: set only for `http-http` (MCP session header); otherwise `None`.

Canonical compose TOML: `tests/qa/shared/mcp_compose_profiles.py`.

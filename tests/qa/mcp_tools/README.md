# mcp_tools — unified MCP tool tests

One suite for all transport profiles covering **20 tools across 3 MCP servers**:

| Server | Tools | Description |
|--------|-------|-------------|
| environments-mcp | 6 | Conda environment management |
| conda-meta-mcp | 9 | Conda metadata queries |
| search-mcp | 5 | Anaconda.com search (remote) |

Architecture, configuration, test design, and reporting details live under [`_docs/`](_docs/index.md).

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
| **`anaconda-mcp-server`** (name is up to you) | Conda env where **`anaconda-mcp`** and **`environments-mcp-server`** are installed — used for **`conda run -n … anaconda-mcp serve`** (`--server-conda-env`). |

Pass the server env name via **`--server-conda-env`** or **`MCP_SERVER_CONDA_ENV`**. Examples below use **`anaconda-mcp-server`** as a short, generic name.

### Test runner env (`anaconda-mcp-qa`)

```bash
conda env create -f tests/qa/environment.yml              # first time
conda env update -f tests/qa/environment.yml --prune    # after environment.yml changes
conda activate anaconda-mcp-qa
```

Use **`python -m pytest …`** so **`httpx`** / **`pytest`** match the active env (see [`_docs/architecture.md`](_docs/architecture.md) for stack context).

### Server env — how we prepare it

The server env must contain **installable copies** of:

1. **`anaconda-mcp`** — this repository.
2. **`environments-mcp-server`** — `python -m environments_mcp_server` (started by mcp-compose for conda tools).
3. **`anaconda-connector-conda`** (`anaconda_connector_conda`) — required by **environments-mcp** for conda operations; without it, tools may not register.

**Default:** editable installs from local clones of **`anaconda-mcp`** and **`environments-mcp`**. `environments-mcp-server` is **not** pulled in automatically by **`anaconda-mcp`**’s `pyproject.toml`; install it explicitly.

```bash
conda create -n anaconda-mcp-server python=3.13 -y
conda activate anaconda-mcp-server
pip install -e /path/to/anaconda-mcp
pip install -e /path/to/environments-mcp
conda install -c anaconda-cloud -c conda-forge -c defaults anaconda-connector-conda -y   # if import fails
conda install -c anaconda-cloud anaconda-anon-usage -y   # required for telemetry
```

**Pinning `mcp-compose`** (fork / branch / git URL) in the same env overrides PyPI—important for **stdio-stdio** proxy behavior. Verify with `python -c "import mcp_compose; print(mcp_compose.__file__)"`.

**More detail:** [`tests/qa/_ai_docs/tech_details/LOCAL-DEV-SETUP.md`](../_ai_docs/tech_details/LOCAL-DEV-SETUP.md), [`INSTALL_OPTIONS.md`](../_ai_docs/tech_details/INSTALL_OPTIONS.md).

### conda-meta-mcp setup

Install the `conda-meta-mcp` package from conda-forge:

```bash
conda activate anaconda-mcp-server
conda install -c conda-forge conda-meta-mcp
# Verify: python -m conda_meta_mcp.cli --help
```

The server starts automatically via mcp-compose config (`python -m conda_meta_mcp.cli run --transport streamable-http --port 4042`).

### Authentication (Required)

**anaconda-mcp requires authentication to function.** The server will not start without valid credentials.

#### Getting an API Key

1. Go to [anaconda.com](https://anaconda.com) and sign in
2. Navigate to **Account Settings** → **Access** → **API Keys**
3. Click **Generate API Key**
4. Copy the generated key (shown only once)

**Required permissions:** Read-only access is sufficient. Standard user keys work for all tests.

#### Local Development: `.env` file (recommended)

Create a `.env` file in the repo root:

```bash
ANACONDA_AUTH_API_KEY=your-api-key-here
```

The test harness loads this automatically via `conftest.py`.

#### Local Development: Environment variable

```bash
export ANACONDA_AUTH_API_KEY=your-api-key-here
```

#### Local Development: Keyring (from `anaconda login`)

```bash
anaconda login
anaconda whoami  # verify login
```

The token from `anaconda login` is used as a fallback when `ANACONDA_AUTH_API_KEY` is not set.

#### GitHub Actions: Repository Secret

Configure the following repository secret:
- **`TEST_API_KEY`** — Your Anaconda API key

The workflow uses this secret as `ANACONDA_AUTH_API_KEY`.

**Auth detection order:**
1. `ANACONDA_AUTH_API_KEY` environment variable
2. Keyring token from `anaconda login`

**If not authenticated:** Server startup fails with:
```
RuntimeError: Not authenticated with Anaconda. Run 'anaconda-auth login' or sign in when prompted.
```

### search-mcp setup

search-mcp is a remote service hosted at `anaconda.com/api/search/mcp` (no local installation required).

**Requirements:**
1. **Anaconda authentication** (see above)
2. **Network access** to anaconda.com

**Verify the server env:**

```bash
python -c "import anaconda_mcp; import environments_mcp_server; import anaconda_connector_conda; import conda_meta_mcp; print('OK')"
anaconda-mcp --help
python -m conda_meta_mcp.cli --help  # conda-meta-mcp
```

### Packaged `mcp_compose.toml` vs QA

The file **`src/anaconda_mcp/mcp_compose.toml`** is a **packaged default** when users run `anaconda-mcp serve` without a custom config. **QA runs do not select transport by editing that file.** Tests generate TOML from **`tests/qa/shared/mcp_compose_profiles.py`**, write a temp file, and run `anaconda-mcp serve --config <file>`. See [`_docs/architecture.md`](_docs/architecture.md).

## Examples

From the repo root (with `anaconda-mcp-qa` activated):

```bash
# Full suite with stdio-http profile (recommended for CI)
pytest tests/qa/mcp_tools -o addopts= \
  --mcp-profile=stdio-http \
  --server-conda-env anaconda-mcp-server

# HTTP-HTTP profile (requires --start-server)
pytest tests/qa/mcp_tools -o addopts= \
  --mcp-profile=http-http \
  --server-url http://localhost:9888/mcp \
  --start-server --server-conda-env anaconda-mcp-server

# STDIO-STDIO profile
pytest tests/qa/mcp_tools -o addopts= \
  --mcp-profile=stdio-stdio \
  --server-conda-env anaconda-mcp-server
```

Or: `conda run -n anaconda-mcp-qa pytest tests/qa/mcp_tools -o addopts= …`

**Note**: The full suite tests all 20 tools across environments-mcp, conda-meta-mcp, and search-mcp. Ensure all three servers are properly configured (see setup sections above).

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

# Windows Setup Guide

Before running anything on Windows, check your conda installation: [CONDA_SETUP.md](./CONDA_SETUP.md).

---

## Create the RC Environment

Use **Miniconda Prompt** or **PowerShell** (not plain `cmd`). Paste the entire block at once — do not run line by line.

Replace `X.Y` with: `3.10` | `3.11` | `3.12` | `3.13`

```bat
conda create --name anaconda-mcp-rc-pyXY ^
  -c datalayer ^
  -c anaconda-cloud/label/dev ^
  -c defaults ^
  -c conda-forge ^
  --channel "https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/" ^
  python=X.Y ^
  anaconda-mcp=1.0.0.rc.1 ^
  environments-mcp-server=1.0.0.rc.1

conda activate anaconda-mcp-rc-pyXY
```

Verify:

```bat
python -m anaconda_mcp --help
conda list | findstr /R "anaconda-mcp environments-mcp anaconda-connector python"
```

---

## Command Substitutions

Throughout the QA docs, replace macOS/Linux commands as follows:

| macOS / Linux | Windows |
|---|---|
| `anaconda-mcp <cmd>` | `python -m anaconda_mcp <cmd>` |
| `export VAR=value` | `set VAR=value` |
| `grep -E "..."` | `findstr /R "..."` |
| `./tests/qa/_ai_docs/scripts/start-http-server.sh 8888` | `python -m anaconda_mcp serve --http --port 8888` |

**Why `anaconda-mcp` doesn't work on Windows**: conda installs an extensionless Unix-style script into `Scripts\`. Windows only executes `.exe`, `.bat`, or `.cmd` files, so the script is silently ignored. Use `python -m anaconda_mcp` instead. See [PI-001](./KNOWN_ISSUES.md#pi-001-anaconda-mcp-cli-not-executable-on-windows--missing-exe-wrapper).

---

## Running from Local Source Code

Use this when testing unpublished changes from a local git checkout.

### Step 1: Clone and setup

```cmd
git clone git@github.com:anaconda/anaconda-mcp.git
cd anaconda-mcp
git checkout main && git pull
```

### Step 2: Create dev environment with dependencies

**Option A — Using environment-dev.yml:**

```cmd
conda env create -f environment-dev.yml
conda activate anaconda-mcp-dev
```

**Option B — Create custom env with editable install:**

```cmd
REM Create env with required channels
conda create --name anaconda-mcp-local -c datalayer -c anaconda-cloud/label/dev -c defaults -c conda-forge ^
  --channel "https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/" ^
  python=3.11 environments-mcp-server

conda activate anaconda-mcp-local

REM Install anaconda-mcp from source in editable mode
pip install -e .
```

### Step 3: Verify installation

```cmd
REM Check that local path is shown (editable install)
pip list | findstr anaconda-mcp
REM Expected: anaconda-mcp  0.1.dev...  c:\path\to\anaconda-mcp

REM Test the CLI
python -m anaconda_mcp --help
```

### Step 4: Run the server from source

**STDIO mode (simple):**

```cmd
cd %USERPROFILE%
conda activate anaconda-mcp-local
python -m anaconda_mcp serve --delay 5
```

**HTTP mode (with config file):**

```cmd
cd %USERPROFILE%
conda activate anaconda-mcp-local
.\path\to\anaconda-mcp\tests\qa\_ai_docs\scripts\start-http-server.ps1 8888
```

Or using CMD:

```cmd
cd %USERPROFILE%
conda activate anaconda-mcp-local
path\to\anaconda-mcp\tests\qa\_ai_docs\scripts\start-http-server.cmd 8888
```

### Step 5: Run tests against local server

**Terminal 1 — Start server:**

```cmd
cd %USERPROFILE%
conda activate anaconda-mcp-local
python -m anaconda_mcp serve --delay 5
```

**Terminal 2 — Run tests (verbose logging):**

```cmd
conda activate anaconda-mcp-qa
python -m pytest tests/qa/http_tools/ -v --log-cli-level=INFO
```

For maximum debug output:

```cmd
python -m pytest tests/qa/http_tools/ -v --log-cli-level=DEBUG -s
```

### Rebuilding after code changes

With editable install (`pip install -e .`), code changes take effect immediately after restarting the server — no reinstall needed.

```cmd
REM Kill existing server (Ctrl+C or close terminal)
REM Start fresh
python -m anaconda_mcp serve --delay 5
```

---

## Troubleshooting Windows-Specific Issues

### Server hangs or tests timeout

1. **Check server logs** — run with debug logging:
   ```cmd
   set ANACONDA_MCP_LOG_LEVEL=DEBUG
   python -m anaconda_mcp serve --delay 5
   ```

2. **Verify Python path** — ensure you're using the conda env's Python:
   ```cmd
   where python
   REM Should show: C:\...\anaconda3\envs\<your-env>\python.exe
   ```

3. **Check for .env conflicts** — run server from `%USERPROFILE%` to avoid loading test `.env` files:
   ```cmd
   cd %USERPROFILE%
   python -m anaconda_mcp serve
   ```

### Wrong Python version detected

Windows may find a different Python via `PATH`. Always use the conda env's Python explicitly:

```cmd
REM Bad: relies on PATH
python -m anaconda_mcp serve

REM Better: use conda run
conda run -n anaconda-mcp-local python -m anaconda_mcp serve

REM Or use full path
%CONDA_PREFIX%\python.exe -m anaconda_mcp serve
```

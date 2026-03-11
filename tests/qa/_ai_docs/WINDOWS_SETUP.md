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

## Configure Claude Desktop

Run in Miniconda Prompt:

```cmd
python -m anaconda_mcp claude-desktop setup-config
```

> **Important**: Claude Desktop on Windows reads config from a different location than where the command writes it. See [WINDOWS_CLAUDE_CODE.md](./WINDOWS_CLAUDE_CODE.md) for the workaround.

---

## Local Development Setup

For testing local code changes (editable installs, running from source), see [LOCAL-DEV-SETUP.md](./LOCAL-DEV-SETUP.md).

Windows-specific notes are included at the bottom of that guide.

---

## Install Latest Main into an Existing RC Environment

If you already have the RC environment created (via the `conda create` above) and want to replace the released packages with the latest `main` from local clones of both repos:

**Step 1 — Activate the environment and install from local source:**

```bat
conda activate anaconda-mcp-rc-pyXY

pip install -e C:\path\to\anaconda-mcp
pip install -e C:\path\to\environments-mcp
```

Replace `C:\path\to\...` with the actual clone paths on your machine, e.g. `C:\Users\JuliaIliukhina\projects\anaconda-mcp`.

**Step 2 — Verify the local versions are active:**

```bat
pip list | findstr /R "anaconda-mcp environments-mcp"
```

Expected output shows the local path instead of a version number:
```
anaconda-mcp              0.1.dev...  C:\path\to\anaconda-mcp
environments-mcp-server   0.1.dev...  C:\path\to\environments-mcp
```

**Step 3 — Restart Claude Desktop** (kill all processes — see [WINDOWS_CLAUDE_CODE.md](./WINDOWS_CLAUDE_CODE.md)) so it picks up the updated packages.

**To reset back to the released RC versions:**

```bat
pip install --force-reinstall anaconda-mcp==1.0.0.rc.1 environments-mcp-server==1.0.0.rc.1
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

# Windows Setup Guide

Before running anything on Windows, check your conda installation: [CONDA_SETUP.md](../../../tech_details/CONDA_SETUP.md).

---

## Before Every Test Session

Follow this checklist at the start of every session to avoid interference from previous runs.

### 1. Kill Claude Desktop and leftover processes

**Do not just click the X button** — Claude Desktop may keep running in the system tray or background.

Fully terminate Claude Desktop via Task Manager:
1. Press `Ctrl + Shift + Esc` to open Task Manager
2. Find all **Claude** entries in the Processes list
3. Right-click each → **End Task**
4. Confirm no Claude processes remain before continuing

Then clear any orphaned server processes on port 4041 (Claude Desktop does not kill child processes on Windows — see [KI-017](./KNOWN_ISSUES.md#ki-017)):

```cmd
netstat -ano | findstr :4041
taskkill /F /PID <each PID listed>
```

Verify the port is clear before continuing — it should return no output:

```cmd
netstat -ano | findstr :4041
```

### 2. [If needed] Install the version under test

To test a specific branch or local fix for either MCP, install both packages from local source into the RC environment:

```bat
conda run -n anaconda-mcp-rc-pyXY pip install -e C:\projects\anaconda-mcp
conda run -n anaconda-mcp-rc-pyXY pip install -e C:\projects\environments-mcp
```

Verify:

```bat
conda run -n anaconda-mcp-rc-pyXY pip list | findstr /R "anaconda-mcp environments-mcp"
```

Expected output shows local paths and dev versions:
```
anaconda-mcp              1.0.0rc2.dev1+g...  C:\projects\anaconda-mcp
environments-mcp-server   0.1.dev...          C:\projects\environments-mcp
```

To revert to the released RC:
```bat
conda run -n anaconda-mcp-rc-pyXY pip install --force-reinstall anaconda-mcp==1.0.0.rc.1 environments-mcp-server==1.0.0.rc.1
```

### 3. Open Claude Desktop and wait for connection

Open Claude Desktop and wait until anaconda-mcp shows as **connected** (~10–13 seconds). Do not send any requests until it is connected.

> **⚠️ Use Anaconda logged-out state for testing** ([DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386)): when the user is logged in to Anaconda, the retry after the first-call hang also fails — making the session fully unusable. Until DESK-1386 is fixed, **log out of Anaconda before opening Claude Desktop** to ensure the retry recovers successfully.
>
> **Known**: The first tool call after startup always hangs on Windows ([DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385)). This affects both logged-in and logged-out users. Wait for the timeout (~4 minutes), then retry — the retry succeeds when logged out.

---

## Collecting Evidence for Bug Reports

When filing a bug, attach:

### Conversation log
Copy the full Claude conversation text from the chat window (select all, copy).

### MCP server log
1. In Claude Desktop: **File → Settings → Developer → anaconda-mcp → Open Logs**
2. The log file opens in your default text editor
3. Copy only the portion covering the time window of your test (timestamps are included on every line)
4. Save as a `.log` file and attach to the ticket

The log contains both the Claude Desktop transport layer (`[anaconda-mcp] [info] ...`) and the `mcp-compose` / `environments_mcp_server` output — everything needed to diagnose hangs, errors, and session issues.

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

For testing local code changes (editable installs, running from source), see [LOCAL-DEV-SETUP.md](../../../tech_details/LOCAL-DEV-SETUP.md).

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

## Use a Specific Branch or Local Fix with Claude Desktop

Use this when you want Claude Desktop to run against a specific branch — e.g. latest `main` for `anaconda-mcp` and a bug-fix branch for `environments-mcp`.

**Prerequisites:** repos cloned locally and the desired branch checked out.

**Step 1 — Install both packages from local source (no activation needed):**

```bat
conda run -n anaconda-mcp-rc-pyXY pip install -e C:\projects\anaconda-mcp
conda run -n anaconda-mcp-rc-pyXY pip install -e C:\projects\environments-mcp
```

**Step 2 — Verify both show local paths and dev versions:**

```bat
conda run -n anaconda-mcp-rc-pyXY pip list | findstr /R "anaconda-mcp environments-mcp"
```

Expected:
```
anaconda-mcp              1.0.0rc2.dev1+g...  C:\projects\anaconda-mcp
environments-mcp-server   0.1.dev223+g...     C:\projects\environments-mcp
```

**Step 3 — Restart Claude Desktop** so it picks up the new code. See [WINDOWS_CLAUDE_CODE.md](./WINDOWS_CLAUDE_CODE.md) for how to fully kill and relaunch it.

**To revert to the released RC version:**

```bat
conda run -n anaconda-mcp-rc-pyXY pip install --force-reinstall anaconda-mcp==1.0.0.rc.1 environments-mcp-server==1.0.0.rc.1
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

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

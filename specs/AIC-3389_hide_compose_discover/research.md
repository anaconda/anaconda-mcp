# Research: Hide compose/discover commands from --help output

**Feature**: AIC-3389_hide_compose_discover · **Date**: 2026-05-29

## Bug Report

`compose` and `discover` still appear in `--help` despite being hidden in PR #57.

### Steps to Reproduce

```bash
CONDA_SUBDIR=osx-arm64 conda create -n mcp-test -y \
  --override-channels -c https://repo.anaconda.cloud/repo/main \
  python=3.13 anaconda-mcp=1.1.1
conda activate mcp-test
anaconda mcp --help      # new entrypoint
anaconda-mcp --help      # legacy entrypoint
```

### Expected

Both list only: `serve, clients, setup, remove, terms`.

### Actual (all 12 cells run on real packages)

| Command | 1.0.3 | 1.1.0 | 1.1.1 |
|---------|-------|-------|-------|
| `anaconda mcp --help` | LEAKS | clean | clean |
| `anaconda mcp` (no subcmd) | LEAKS | clean | clean |
| `anaconda-mcp --help` (legacy) | LEAKS | **LEAKS** | **LEAKS** |
| `anaconda-mcp` (no subcmd, legacy) | LEAKS | **LEAKS** | **LEAKS** |

Only the legacy `anaconda-mcp` binary still leaks on current releases. (`anaconda mcp` was fixed in 1.1.0 by commit `8355453`.)

### Root Cause

`cli.py` `compose` (line 238) and `discover` (line 276) use `@cli.command(...)` without `hidden=True`, so the legacy Click group lists them. The `anaconda mcp` Typer wrapper (`app.py`) never registers these commands, so it is already clean.

Separately, `app.py` (lines 29-30) has a `click_cli.main(["--help"])` fallback that is unreachable on current releases (`no_args_is_help=True` short-circuits first) — dead code, safe to remove as defensive cleanup but not the cause of any leak.

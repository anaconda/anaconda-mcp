# SETUP-001: Installation Disclaimer Verification

Verify terms and conditions disclaimer is displayed during/after installation.

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | None | — | | + |
| 1 | Run installation command (see below) | Disclaimer about terms and conditions appears in terminal output | | + |
| 2 | Document exact text shown | Record for release notes verification | | + |
| Post | None | — | | + |

## Installation Command (RC2)

```bash
conda create --name anaconda-mcp-rc2-pyXY \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=X.Y \
  anaconda-mcp=1.0.0.rc.2 \
  environments-mcp-server=1.0.0.rc.2

conda activate anaconda-mcp-rc2-pyXY
anaconda-mcp claude-desktop setup-config --force
```

> Replace `X.Y` with target Python version (e.g., `3.10` or `3.13`).

## Release Notes

| Release | Status |
|---------|--------|
| RC1 | Not applicable (feature not implemented) |
| RC2 | New feature: terms & conditions disclaimer shown after install |

## Pass Criteria

- Disclaimer is visible and clearly readable during install process

# AUTH-001: Anonymous Mode

Verify anonymous user can create environments and install packages using public channels.

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | Terminal: `anaconda logout 2>/dev/null \|\| true` | Logged out | + | + |
| 1 | "List my conda environments" | Environment list returned | + | + |
| 2 | "Create environment anon-test with Python 3.11" | Environment created | + | + |
| 3 | Terminal: `conda list -n anon-test --show-channel-urls` | All URLs are public channels (`pkgs/main`, `pkgs/r`, `conda-forge`). No `repo.anaconda.cloud` URLs. | + | + |
| Post | Terminal: `conda remove -n anon-test --all -y` | Cleanup | + | + |

## Release Notes

| Release | Additional Verification |
|---------|------------------------|
| RC1 | — |
| RC2 | — |

## Notes

- **Fresh environment required**: Step 3 is only reliable for freshly created environments. Previously existing environments retain their original channel metadata.
- For testing anonymous denial on PRIVATE channels, see [AUTH-001a](./AUTH-001a.md)

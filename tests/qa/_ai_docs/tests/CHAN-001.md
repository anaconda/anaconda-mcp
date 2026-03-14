# CHAN-001: Override Channels Behavior

Verify `override_channels` parameter is hidden by default and can be enabled.

## Background

The `environments-mcp-server` has an `override_channels: list[str]` parameter on `conda_create_environment` and `conda_install_packages`. By default, this parameter is **stripped from the tool schema** so the agent cannot use it.

**Config options:**
- CLI flag: `--allow-override-channels`
- Env var: `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS=true`

## Part A: Default Behavior (disabled)

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](../AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | | + |
| Pre | Verify `mcp_compose.toml` does NOT have `--allow-override-channels` flag | Default config | | + |
| Pre | Restart Claude Desktop | Config reloaded | | + |
| 1 | "What parameters does conda_create_environment accept?" | `override_channels` NOT in list | | + |
| 2 | "Create environment chan-test with Python 3.11 using only conda-forge channel" | Environment created (agent may try workaround) | | + |
| 3 | Terminal: `conda list -n chan-test --show-channel-urls` | Packages from DEFAULT channels (not restricted to conda-forge) | | + |
| Post | Terminal: `conda remove -n chan-test --all -y` | Cleanup | | + |

## Part B: Enabled via Config

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](../AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | | + |
| Pre | Edit `mcp_compose.toml`: add `--allow-override-channels` to command (see below) | Config updated | | + |
| Pre | Restart Claude Desktop | Config reloaded | | + |
| 1 | "What parameters does conda_create_environment accept?" | `override_channels` IS in list | | + |
| 2 | "Create environment chan-test-override with Python 3.11 using only conda-forge channel" | Environment created | | + |
| 3 | Terminal: `conda list -n chan-test-override --show-channel-urls` | Packages from conda-forge ONLY | | + |
| Post | Terminal: `conda remove -n chan-test-override --all -y` | Cleanup | | + |
| Post | Revert `mcp_compose.toml` changes, restart Claude Desktop | Restore default | | + |

## Config Change for Part B

Edit `mcp_compose.toml` (location: `<env>/lib/python3.X/site-packages/anaconda_mcp/mcp_compose.toml`):

```toml
# Before:
command = ["python", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "4041"]

# After:
command = ["python", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "4041", "--allow-override-channels"]
```

## Release Notes

| Release | Status |
|---------|--------|
| RC1 | Not applicable (feature not implemented) |
| RC2 | New feature: `override_channels` disabled by default, can be enabled |

## Pass Criteria

- **Part A**: `override_channels` NOT visible in schema; channels cannot be overridden
- **Part B**: `override_channels` visible in schema; agent passes `override_channels: ["conda-forge"]`

## Notes

- If Part A shows agent passing `--channel` flags in packages array, that's expected (agent workaround) but packages should still come from default channels
- The test verifies the **server-side control** over the parameter visibility

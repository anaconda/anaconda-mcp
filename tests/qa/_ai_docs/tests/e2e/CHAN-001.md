# CHAN-001: Override Channels Behavior

> ← [Back to Test Catalog](../../QA_WALKTHROUGH.md#3-test-catalog)

Verify `override_channels` parameter visibility based on env var setting.

## Background

The `environments-mcp-server` has an `override_channels: list[str]` parameter on `conda_create_environment` and `conda_install_packages`. Visibility is controlled by:

**Env var**: `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS`

## Part A: No Config (default)

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](./setup/AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | | + |
| Pre | Verify Claude Desktop config has NO `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS` | Default config | | + |
| Pre | Restart Claude Desktop | Config reloaded | | + |
| 1 | "What parameters does conda_create_environment accept?" | `override_channels` NOT in list | | + |
| 2 | "Create environment chan-test-default with Python 3.11 using only conda-forge" | Created (agent may try workaround) | | + |
| 3 | Terminal: `conda list -n chan-test-default --show-channel-urls` | Packages from mixed channels (defaults + conda-forge) — NOT restricted to conda-forge only | | + |
| Post | Terminal: `conda remove -n chan-test-default --all -y` | Cleanup | | + |

## Part B: Env Var = "true"

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](./setup/AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | | + |
| Pre | Set `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS`: `"true"` in Claude Desktop config | Config updated | | + |
| Pre | Restart Claude Desktop | Config reloaded | | + |
| 1 | "What parameters does conda_create_environment accept?" | `override_channels` IS in list | | + |
| 2 | "Create environment chan-test-true with Python 3.11 using only conda-forge" | Created with override_channels param | | + |
| 3 | Terminal: `conda list -n chan-test-true --show-channel-urls` | Packages from conda-forge ONLY | | + |
| Post | Terminal: `conda remove -n chan-test-true --all -y` | Cleanup | | + |

## Part C: Env Var = "false"

> **Known issue**: [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403) — any non-empty string (including `"false"`, `"0"`) is parsed as truthy.
>
> **Workaround**: Use `""` (empty string) or remove the env var entirely to disable the feature.

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](./setup/AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | | + |
| Pre | Set `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS`: `"false"` in Claude Desktop config | Config updated | | + |
| Pre | Restart Claude Desktop | Config reloaded | | + |
| 1 | "What parameters does conda_create_environment accept?" | `override_channels` NOT in list | | + |
| 2 | "Create environment chan-test-false with Python 3.11 using only conda-forge" | Agent workaround, mixed channels | | + |
| 3 | Terminal: `conda list -n chan-test-false --show-channel-urls` | Packages from mixed channels — NOT restricted to conda-forge only | | + |
| Post | Terminal: `conda remove -n chan-test-false --all -y` | Cleanup | | + |
| Post | Remove env var from Claude Desktop config, restart | Restore default | | + |

## Claude Desktop Config

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "...",
      "args": ["..."],
      "env": {
        "CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS": "true"
      }
    }
  }
}
```

## Release Notes

| Release | Status |
|---------|--------|
| RC1 | Not applicable (feature not implemented) |
| RC2 | New feature: `override_channels` disabled by default |

## Expected Results Summary

| Part | Env Var | `override_channels` visible? | Channels used |
|------|---------|------------------------------|---------------|
| A | (not set) | No | Normal resolution (mixed channels) |
| B | `"true"` | Yes | conda-forge ONLY |
| C | `"false"` | No (but see DESK-1403) | Normal resolution (mixed channels) |

## Notes

- Part A and C should behave identically (explicit false = default)
- **DESK-1403 workaround**: To explicitly disable, use `""` (empty string) or remove the env var entirely
- If agent puts `--channel` flags in packages array, that's a workaround — verify packages still come from default channels
- **Other MCP hosts**: Examples use Claude Desktop config. For other hosts (Cursor, Claude Code, etc.), set `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS` via their environment variable configuration mechanism.

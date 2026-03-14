# CHAN-001: Override Channels Behavior

Verify `override_channels` is disabled by default and can be enabled via environment variable.

## Part A: Default Behavior (disabled)

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](../AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | | + |
| Pre | Terminal: `unset ALLOW_OVERRIDE_CHANNELS` then restart Claude Desktop | Env var cleared | | + |
| 1 | "Create environment chan-test with Python 3.11 using only conda-forge channel" | Environment created | | + |
| 2 | Terminal: `conda list -n chan-test --show-channel-urls` | Packages from default channels (NOT restricted to conda-forge) | | + |
| Post | Terminal: `conda remove -n chan-test --all -y` | Cleanup | | + |

## Part B: Enabled via Environment Variable

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](../AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | | + |
| Pre | Terminal: `export ALLOW_OVERRIDE_CHANNELS=true` then restart Claude Desktop | Env var set | | + |
| 1 | "Create environment chan-test-override with Python 3.11 using only conda-forge channel" | Environment created | | + |
| 2 | Terminal: `conda list -n chan-test-override --show-channel-urls` | Packages from conda-forge ONLY | | + |
| Post | Terminal: `conda remove -n chan-test-override --all -y; unset ALLOW_OVERRIDE_CHANNELS` | Cleanup | | + |

## Release Notes

| Release | Status |
|---------|--------|
| RC1 | Not applicable (feature not implemented) |
| RC2 | New feature: `override_channels` disabled by default |

## Notes

- If Part A fails (channels ARE being overridden without env var), file bug — default should be disabled per release notes

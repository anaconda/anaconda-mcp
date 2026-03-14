# AUTH-002: Authenticated Mode

> ← [Back to Test Catalog](../../QA_WALKTHROUGH.md#3-test-catalog)

Verify authenticated user can access private channels via MCP.

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged In](./setup/AUTH_SETUP.md#prerequisites-logged-in-core-001-auth-002) | Auth state configured | + | + |
| 1 | "List my conda environments" | Environment list returned | + | + |
| 2 | "Create environment auth-test with Python 3.11" | Environment created | + | + |
| 3 | "Install numpy in auth-test" | Package installed | + | + |
| 4 | Terminal: `conda list -n auth-test --show-channel-urls \| grep numpy` | URL contains `repo.anaconda.cloud` | + | + |
| Post | [Cleanup](./setup/AUTH_SETUP.md#post-conditions--cleanup) | State restored | + | + |

## Verification

Step 4 proves:
- `anaconda token config` correctly redirected `defaults` to `repo.anaconda.cloud`
- MCP install call respected the conda config

## Release Notes

| Release | Status |
|---------|--------|
| RC1 | Blocked by DESK-1358 (URL routing) |
| RC2 | Blocked by DESK-1401 (credentials not passed by MCP subprocess) |

## Notes

- **Account requirement**: Use account with `repo.anaconda.cloud` access (e.g., Anaconda employee)
- **Fresh environment required**: Always run cleanup between test runs — cached package metadata persists

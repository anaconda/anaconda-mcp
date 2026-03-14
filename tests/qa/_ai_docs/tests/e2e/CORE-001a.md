# CORE-001a: Full Tools Flow — Logged Out

> ← [Back to Test Catalog](../../INDEX.md#3-test-catalog)

E2E happy path covering all 6 conda tools with anonymous user (public channels).

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](./setup/AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Auth state configured | + | + |
| 1 | "List my conda environments" | Environment list returned | + | + |
| 2 | "Create environment e2e-test with Python 3.11" | Environment created | + | + |
| 3 | "Search packages matching numpy" | Package list returned | + | + |
| 4 | "Install numpy in e2e-test" | Package installed | + | + |
| 5 | "List packages in e2e-test" | numpy in list | + | + |
| 6 | "Remove numpy from e2e-test" | Package removed | + | + |
| 7 | "Delete e2e-test environment" | Environment removed | + | + |
| 8 | "List my conda environments" | e2e-test not in list | + | + |
| Post | [Cleanup](./setup/AUTH_SETUP.md#post-conditions--cleanup) | State restored | + | + |

## Release Notes

| Release | Additional Verification |
|---------|------------------------|
| RC1 | Step 7 may fail with wrong prefix (DESK-1342) |
| RC2 | Count tool calls (expect 8 total); Step 7: single call with `environment_name` param; DESK-1342 fixed |

## Notes

- Uses PUBLIC channels (`repo.anaconda.com`), not private (`repo.anaconda.cloud`)
- For testing anonymous denial on private channels, see [AUTH-001a](./AUTH-001a.md)

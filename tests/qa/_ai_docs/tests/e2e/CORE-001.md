# CORE-001: Full Tools Flow — Logged In

> ← [Back to Test Catalog](../../QA_WALKTHROUGH.md#3-test-catalog)

E2E happy path covering all 6 conda tools with authenticated user.

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged In](./setup/AUTH_SETUP.md#prerequisites-logged-in-core-001-auth-002) | Auth state configured | + | + |
| 1 | "List my conda environments" | Environment list returned | + | + |
| 2 | "Create environment e2e-test with Python 3.11" | Environment created | + | + |
| 3 | "Search packages matching numpy" | numpy described (no tool call — no `conda_search_packages` tool) | + | + |
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
| RC2 | Count tool calls (expect **7 total** — step 3 uses no tool call); Step 7: single call with `environment_name` param; DESK-1342 fixed |

## Pass Criteria

- **Step 3**: Claude describes numpy availability (name, versions, channel) from its own knowledge; **no MCP tool is called** — `conda_search_packages` does not exist in this product; the step contributes 0 to the tool-call count
- **Step 7**: single `conda_remove_environment` call with `environment_name` param (RC2+)
- **Tool call total**: 7 across the full flow (steps 1, 2, 4, 5, 6, 7, 8 — one call each)

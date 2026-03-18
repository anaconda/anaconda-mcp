# CORE-001: Full Tools Flow — Logged In

> ← [Back to Test Catalog](../../QA_WALKTHROUGH.md#3-test-catalog)

E2E happy path covering all 6 conda tools with authenticated user (interactive login).

> **Important**: Use EITHER interactive login OR API key auth — not both. For API key authentication, see [CORE-001b](./CORE-001b.md).

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
| Post | [Cleanup](./setup/AUTH_SETUP.md#cleanup-interactive-login) | State restored | + | + |

## Release Notes

| Release | Additional Verification |
|---------|------------------------|
| RC1 | Step 7 may fail with wrong prefix (DESK-1342) |
| RC2 | Count tool calls (expect **7 total** — step 3 uses no tool call); Step 7: single call with `environment_name` param; DESK-1342 fixed |

## Pass Criteria

- **Step 3**: Claude describes numpy availability (name, versions, channel) from its own knowledge; **no MCP tool is called** — `conda_search_packages` does not exist in this product; the step contributes 0 to the tool-call count
  - **Alternative behavior**: Claude may interpret "search packages" as "list installed packages matching X" and call `conda_list_environment_packages` to filter results. This is acceptable but adds 1 to tool-call count.
- **Step 7**: single `conda_remove_environment` call with `environment_name` param (RC2+)
- **Tool call total**: 7 across the full flow (steps 1, 2, 4, 5, 6, 7, 8 — one call each)
  - If Step 3 alternative behavior: 8 total

## Expected Channel Information (Logged-In User)

When user is authenticated to Anaconda, `conda_list_environment_packages` response includes channel details:

| Field | Expected Value |
|-------|---------------|
| `base_url` | `https://repo.anaconda.cloud/repo/main` |
| `channel` | `repo/main` |
| `platform` | `osx-arm64` (or user's platform) |
| `platform` (noarch) | `noarch` for pure-Python packages (pip, tzdata, etc.) |

Example package entry:
```json
{
  "name": "numpy",
  "version": "1.26.4",
  "channel": "repo/main",
  "base_url": "https://repo.anaconda.cloud/repo/main",
  "platform": "osx-arm64",
  "build_string": "py311h7125f55_0",
  "build_number": 0,
  "dist_name": "numpy-1.26.4-py311h7125f55_0"
}
```

# CORE-001b: Full Tools Flow — API Key Authentication

> ← [Back to Test Catalog](../../QA_WALKTHROUGH.md#3-test-catalog)

E2E happy path covering all 6 conda tools with API key authentication (no interactive login).

**Use case**: User cannot run `anaconda login` due to port 8000 conflict with running Claude Desktop (see [KI-026/DESK-1411](../../bug_details/port_conflict/KI-026-port-8000-conflict-anaconda-login.md)).

| Step | Action | Expected | RC2 |
|------|--------|----------|:---:|
| Pre | [API Key Auth](./setup/AUTH_SETUP.md#prerequisites-api-key-authentication-core-001b-blocked) | Auth state configured via API key | |
| 1 | "List my conda environments" | Environment list returned | |
| 2 | "Create environment e2e-test with Python 3.11" | Environment created | |
| 3 | "Search packages matching numpy" | numpy described (no tool call — no `conda_search_packages` tool) | |
| 4 | "Install numpy in e2e-test" | Package installed | |
| 5 | "List packages in e2e-test" | numpy in list | |
| 6 | "Remove numpy from e2e-test" | Package removed | |
| 7 | "Delete e2e-test environment" | Environment removed | |
| 8 | "List my conda environments" | e2e-test not in list | |
| Post | [Cleanup](./setup/AUTH_SETUP.md#cleanup-api-key-auth) | State restored | |

## Prerequisites

See [AUTH_SETUP.md — API Key Authentication](./setup/AUTH_SETUP.md#prerequisites-api-key-authentication-core-001b).

## Release Notes

| Release | Additional Verification |
|---------|------------------------|
| RC2 | Same as CORE-001; API key auth should behave identically to interactive login |

## Pass Criteria

- **Authentication**: User is authenticated via API key (no interactive login required)
- **Step 3**: Claude describes numpy availability from its own knowledge; **no MCP tool is called**
  - **Alternative behavior**: Claude may call `conda_list_environment_packages` to filter results (adds 1 to tool-call count)
- **Step 7**: single `conda_remove_environment` call with `environment_name` param
- **Tool call total**: 7 across the full flow (steps 1, 2, 4, 5, 6, 7, 8 — one call each)
  - If Step 3 alternative behavior: 8 total

## Expected Channel Information (API Key Auth)

Same as [CORE-001](./CORE-001.md#expected-channel-information-logged-in-user) — API key provides same access as interactive login:

| Field | Expected Value |
|-------|---------------|
| `base_url` | `https://repo.anaconda.cloud/repo/main` |
| `channel` | `repo/main` |

## Post-Conditions / Cleanup

See [AUTH_SETUP.md — Cleanup: API Key Auth](./setup/AUTH_SETUP.md#cleanup-api-key-auth).

## Comparison with Other CORE-001 Variants

| Test | Auth Method | Channels | Port 8000 Conflict |
|------|-------------|----------|-------------------|
| CORE-001 | Interactive login | Private (repo.anaconda.cloud) | Requires quit Claude Desktop to login |
| CORE-001a | Logged out | Public (repo.anaconda.com) | N/A |
| **CORE-001b** | **API key** | **Private (repo.anaconda.cloud)** | **No conflict — can stay running** |

## Related

- [CORE-001](./CORE-001.md) — Same test with interactive login
- [CORE-001a](./CORE-001a.md) — Same test logged out (public channels)
- [KI-026/DESK-1411](../../bug_details/port_conflict/KI-026-port-8000-conflict-anaconda-login.md) — Port 8000 conflict issue
- [KI-027](../../bug_details/api_key_auth/KI-027-api-key-auth-not-working-mcp.md) — API key auth doesn't work (blocks this test)

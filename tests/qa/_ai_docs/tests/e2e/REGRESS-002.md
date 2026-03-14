# REGRESS-002: Remove Environment by Name

> ← [Back to Test Catalog](../../QA_WALKTHROUGH.md#3-test-catalog)

Verify `conda_remove_environment` resolves correct prefix when called by name (DESK-1342 fix).

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](./setup/AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | + | + |
| Pre | Terminal: `conda create -n regress-remove-test python=3.11 -y` | Test env created | + | + |
| 1 | "Delete the regress-remove-test environment" | Single `conda_remove_environment` call with `environment_name` param | + | + |
| 2 | Terminal: `conda env list \| grep regress-remove-test` | Empty (env is gone) | + | + |
| Post | Terminal: `conda remove -n regress-remove-test --all -y 2>/dev/null` | Cleanup (if test failed) | + | + |

## Release Notes

| Release | Additional Verification |
|---------|------------------------|
| RC1 | Step 1 may fail with wrong prefix (DESK-1342); agent self-recovers with 3+ tool calls |
| RC2 | Step 1: exactly 1 tool call, `environment_name` param (not `prefix`); DESK-1342 fixed |

## Pass Criteria

- **Tool calls**: exactly 1 (`conda_remove_environment` by name)
- **No** `conda_list_environments` lookup first
- **No** retry with `prefix` parameter
- **Result**: `is_error: false`, environment removed

## Fail Symptoms (DESK-1342 present)

- First call returns: `"Conda environment not found"` with wrong prefix in details
- Agent self-recovers: calls `conda_list_environments`, then retries with `prefix` — 3+ tool calls total
- Or agent gives up and reports the environment doesn't exist

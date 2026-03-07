# E2E Flows (macOS Only)

> **Clients**: Claude Desktop (STDIO), Cursor (HTTP or STDIO), or Claude Code (HTTP). See [TEST_MATRIX.md](./TEST_MATRIX.md) for transport/client assignment per QA.

## Prerequisites

**Before running any test flow**, complete these steps:

### 1. Determine Test Configuration

Record the configuration you are testing:

| Setting | Your Value |
|---------|------------|
| Client | _______ (Claude Desktop, Cursor, or Claude Code) |
| Python version | _______ (3.10, 3.11, 3.12, or 3.13) |
| Transport mode | _______ (STDIO or HTTP — note: Claude Desktop only supports STDIO, see [KI-009](./KNOWN_ISSUES.md#ki-009-claude-desktop-does-not-support-http-transport)) |
| anaconda-mcp version | _______ (run: `conda list \| grep anaconda-mcp`) |
| environments-mcp-server version | _______ (run: `conda list \| grep environments-mcp`) |

See [TEST_MATRIX.md](./TEST_MATRIX.md) for recommended combinations.

### 2. Setup Environment

Follow [QUICK_START.md](./QUICK_START.md):

1. Install from conda channels OR source (Option A or B)
2. Configure your client:

**For STDIO (Claude Desktop)**:
```bash
anaconda-mcp claude-desktop setup-config
# Restart Claude Desktop (Cmd+Q, then reopen)
```

**For HTTP (Cursor or Claude Code)**:
```bash
# Start server first
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
# Cursor: add config to ~/.cursor/mcp.json (see QUICK_START.md), restart Cursor
# Claude Code: claude mcp add --transport http anaconda-mcp http://localhost:8888/mcp
```

### 3. Verify Ready State

**All tests start from this state:**
- Your client (Claude Desktop, Cursor, or Claude Code) is running
- Anaconda MCP server is connected (check for tools icon in your client)
- You can ask: "List my conda environments" and get a response

If this doesn't work, troubleshoot per [KNOWN_ISSUES.md](./KNOWN_ISSUES.md#troubleshooting) before proceeding.

---

## Flow Summary

| Flow ID | Name | Priority |
|---------|------|----------|
| CORE-001 | Full Tools Flow | P0 |
| GUARD-001 | Guardrails | P0 |
| AUTH-001 | Anonymous Mode | P1 |
| AUTH-001a | Anonymous Mode — Private Channel Denial | P1 — ⛔ BLOCKED by [KI-005](./KNOWN_ISSUES.md#ki-005-channel-credentials-not-picked-up) |
| AUTH-002 | Authenticated Mode | P1 |
| REGRESS-001 | Known Issues | P0 |
| REGRESS-002 | Remove Environment by Name (KI-003) | P0 |

---

## CORE-001: Full Tools Flow

**Purpose**: E2E happy path covering all 6 tools.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "List my conda environments" | Uses `conda_list_environments` |
| 2 | Ask: "Create environment e2e-test with Python 3.11" | Uses `conda_create_environment` |
| 3 | Ask: "Install numpy in e2e-test" | Uses `conda_install_packages` |
| 4 | Ask: "What packages are in e2e-test?" | Uses `conda_list_environment_packages` |
| 5 | Ask: "Remove numpy from e2e-test" | Uses `conda_remove_packages` |
| 6 | Ask: "Delete e2e-test environment" | Uses `conda_remove_environment` |
| 7 | Ask: "List my conda environments" | e2e-test not in list |

---

## GUARD-001: Guardrails

**Purpose**: Verify guardrail behaviors.

### Prep
```bash
conda create -n guard-test python=3.11 -y
conda env list | grep guard-test        # note the prefix path for Step 1b
# or: conda info -e | grep guard-test
```

| Step | Action | Expected |
|------|--------|----------|
| 1a | Ask: "Install nonexistent-package-xyz123 in guard-test" | Error, no pip fallback. Single `conda_install_packages` call |
| 1b | New conversation. Ask: "Install nonexistent-package-xyz123 in `<prefix>`" | Error, no pip fallback |
| 2 | Ask: "Delete guard-test environment" | Client asks confirmation |
| 3 | Confirm deletion | Environment removed |

### Cleanup
```bash
conda remove -n guard-test --all -y 2>/dev/null
```

---

## AUTH-001: Anonymous Mode

**Purpose**: Verify the server works with public channels and is correctly denied access to private Anaconda channels when not authenticated.

### Prep
```bash
anaconda logout 2>/dev/null || true
```

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "List my conda environments" | Works |
| 2 | Ask: "Create environment anon-test with Python 3.11" | Environment created |
| 2a | Run: `conda list -n anon-test --show-channel-urls` | All package URLs contain only public channels (e.g. `pkgs/main`, `pkgs/r`, `conda-forge`). No `repo.anaconda.cloud` URLs present. This is the primary auth signal — symmetric with AUTH-002 step 3a. |
| 3 | Ask: "Install numpy in anon-test from the repo.anaconda.cloud channel" | HTTP 404 — channel not accessible. See note below. |
| 3a | Run: `conda list -n anon-test --show-channel-urls \| grep numpy` | numpy not listed — confirms no silent fallback to a public channel occurred |

> **Note on Step 2 (fresh environment required)**: The channel URL check in step 2a is only a reliable auth signal for **freshly created** environments. If `anon-test` already exists and was previously created while authenticated, its package metadata will still reference `repo.anaconda.cloud` regardless of current auth state — conda stores channel provenance locally at install time and never updates it. Always run the cleanup step between test runs.

> **Note on Step 3**: Due to a URL routing issue, conda resolves the channel name `repo.anaconda.cloud` to `https://conda.anaconda.org/repo.anaconda.cloud` (404) rather than the actual private channel endpoint. This error occurs for both authenticated and unauthenticated users, so it is **not** a reliable auth signal. The key assertion is step 3a (no silent fallback). The routing issue is tracked in [KI-005](./KNOWN_ISSUES.md#ki-005-channel-credentials-not-picked-up).

### Cleanup
```bash
conda remove -n anon-test --all -y
```

---

## AUTH-001a: Anonymous Mode — Private Channel Denial

> ⛔ **BLOCKED by [KI-005](./KNOWN_ISSUES.md#ki-005-channel-credentials-not-picked-up)** — Do not execute until KI-005 is resolved.

**Purpose**: Verify that an anonymous user receives an explicit authentication error (not a silent failure or 404) when attempting to install a package from a private Anaconda channel.

**Why AUTH-001 does not cover this**: AUTH-001 step 3 hits an HTTP 404 due to a URL routing bug — conda resolves `repo.anaconda.cloud` to `conda.anaconda.org` before credentials are ever checked. This error is identical for authenticated and unauthenticated users and therefore cannot prove auth gating.

**What KI-005 must fix for this test to be executable**: The request to a private channel (e.g. `repo.anaconda.cloud` or `anaconda-internal/msys2`) must reach the actual channel endpoint, where an unauthenticated request should receive a `401 Unauthorized` or equivalent auth error.

### Prep
```bash
anaconda logout 2>/dev/null || true
```

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "Install numpy in anon-test from the repo.anaconda.cloud channel" | Explicit authentication/authorization error — **not** HTTP 404, **not** silent fallback to public channel |
| 1a | Run: `conda list -n anon-test --show-channel-urls \| grep numpy` | numpy not listed |

### Cleanup
```bash
conda remove -n anon-test --all -y 2>/dev/null
```

---

## AUTH-002: Authenticated Mode

**Purpose**: Verify the login flow works and the server picks up credentials for private Anaconda channels after authentication.

### Prep
```bash
# Login to Anaconda (browser will open)
anaconda login

# Verify logged in
anaconda whoami
# [EXPECTED] Shows your username
```

> Restart your client (Claude Desktop: Cmd+Q then reopen; Cursor: reload window; Claude Code: exit and restart the session) to pick up the new auth state.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "List my conda environments" | Works |
| 2 | Ask: "Create environment auth-test with Python 3.11" | Environment created |
| 3 | Ask: "Install numpy in auth-test" | Package installed |
| 3a | Run: `conda list -n auth-test --show-channel-urls \| grep numpy` | numpy URL contains `repo.anaconda.cloud` (confirms credentials were picked up). If URL only shows `pkgs/main` or `conda-forge`, credentials were **not** picked up — **fail**. |

> **Note on Step 2 (fresh environment required)**: Same constraint as AUTH-001 — the channel URL check in step 3a is only meaningful for a freshly created environment. Packages installed in a prior run while authenticated retain their `repo.anaconda.cloud` metadata even after logout. Always run the cleanup step between test runs.

> **Note on Step 3a (open question — KI-005)**: This step is the *intended* auth signal, but whether authenticated users actually see `repo.anaconda.cloud` in channel URLs is **unconfirmed**. The same credential routing issue (KI-005) that breaks explicit private channel installs may also prevent `repo.anaconda.cloud` from appearing here — meaning both authenticated and unauthenticated users might only see public channel URLs. If step 3a shows only public channels even after confirmed login (`anaconda whoami` in prep), treat it as a KI-005 symptom rather than a test failure. Tracked in [KI-005](./KNOWN_ISSUES.md#ki-005-channel-credentials-not-picked-up).

### Cleanup
```bash
conda remove -n auth-test --all -y
```

---

## REGRESS-001: Known Issues

**Purpose**: Regression tests for fixed bugs.

### Prep
```bash
conda create -n regress-test python=3.11 -y
conda create -n regress-remove-test python=3.11 -y
```

| Step | Issue | Action | Expected |
|------|-------|--------|----------|
| 1 | KI-002 | Ask: "List my conda environments" | Shows "regress-test" (not "base") |
| 2 | KI-003 | Ask: "Install numpy in regress-test" | Found by name, installs |
| 3 | KI-001 | Ask: "Delete regress-test" | Actually deleted |
| 4 | KI-001 | Run: `conda env list \| grep regress-test` | Empty (gone) |

---

### REGRESS-002: Remove Environment by Name (KI-003)

**Purpose**: Verify that `conda_remove_environment` resolves the correct prefix when called by name — not the prefix of a misclassified "base" environment.

**Coverage scope**: Run in **two configurations only** (see TEST_MATRIX.md — Regression Tests section). The bug is in server-side prefix resolution logic, not transport- or client-specific; the API regression test covers the remaining combinations.

**API regression test**: `test_ki003_remove_environment_by_name`

#### Prep
```bash
conda create -n regress-remove-test python=3.11 -y
```

#### Steps

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ask: "Delete the regress-remove-test environment" | **Exactly one** `conda_remove_environment` tool call with `environment_name="regress-remove-test"`. Agent confirms deletion. |
| 2 | Run: `conda env list \| grep regress-remove-test` | Empty (env is gone) |

#### Pass criteria

- **Tool calls**: exactly 1 (`conda_remove_environment` by name). No `conda_list_environments` retry, no second call with `prefix`.
- **Result**: `is_error: false`, environment removed.

#### Fail symptoms (KI-003 present)

- First tool call returns: `"Conda environment not found"` with wrong prefix in details, e.g. `/opt/miniconda3/envs/anaconda-mcp-rc-py313/envs/regress-remove-test`
- Agent self-recovers: calls `conda_list_environments`, then retries with `prefix` — 3+ tool calls total
- Or agent gives up and tells the user the environment doesn't exist

#### Cleanup (if test fails and agent did not remove it)
```bash
conda remove -n regress-remove-test --all -y 2>/dev/null
```

---

## Test Execution Order

1. REGRESS-001 - Verify fixed issues first
2. CORE-001 - Full happy path
3. GUARD-001 - Guardrails
4. AUTH-001 - Anonymous mode
5. AUTH-002 - Authenticated mode

---

## Cleanup

```bash
conda remove -n e2e-test --all -y 2>/dev/null
conda remove -n guard-test --all -y 2>/dev/null
conda remove -n regress-test --all -y 2>/dev/null
conda remove -n regress-remove-test --all -y 2>/dev/null
conda remove -n anon-test --all -y 2>/dev/null
```

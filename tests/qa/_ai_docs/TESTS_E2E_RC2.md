# E2E Flows — RC2

> **Delta from RC1**: This file documents RC2-specific test changes. See [TESTS_E2E.md](./TESTS_E2E.md) for base test definitions.

## RC2 Release Notes Summary

| Change | Test Impact |
|--------|-------------|
| Terms & conditions disclaimer shown after install | New: SETUP-001 |
| More context in tools — agents more precise | CORE-001: verify reduced tool call count |
| Better understanding of destructive tools | GUARD-001: verify confirmation triggers reliably |
| Environment name operations more reliable | **Verify DESK-1342 fix** — CORE-001 step 6, REGRESS-002 |
| `override_channels` disabled by default | New: CHAN-001 |
| Improved stability (anaconda-mcp + mcp-compose) | General regression |
| Server may get stuck (not fixed) | Document workaround |
| Private repos not working (not fixed) | AUTH-001a remains blocked |

---

## Installation Command (RC2)

```bash
conda create --name anaconda-mcp-rc2-pyXY \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=X.Y \
  anaconda-mcp=1.0.0.rc.2 \
  environments-mcp-server=1.0.0.rc.2

conda activate anaconda-mcp-rc2-pyXY
anaconda-mcp claude-desktop setup-config --force
```

> Replace `X.Y` with target Python version (e.g., `3.10` or `3.13`).

---

## New Tests for RC2

### SETUP-001: Installation Disclaimer Verification

**Purpose**: Verify that terms and conditions disclaimer is displayed during/after installation.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Run installation command (see above) | Disclaimer about terms and conditions appears in terminal output |
| 2 | Document exact text shown | Record for release notes verification |

**Pass criteria**: Disclaimer is visible and clearly readable during install process.

---

### CHAN-001: Override Channels Behavior

**Purpose**: Verify `override_channels` is disabled by default and can be enabled via environment variable.

#### Part A: Default Behavior (disabled)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ensure `ALLOW_OVERRIDE_CHANNELS` is NOT set: `unset ALLOW_OVERRIDE_CHANNELS` | — |
| 2 | Restart Claude Desktop | — |
| 3 | Ask: "Create environment chan-test with Python 3.11 using only conda-forge channel" | Environment created; **verify channels used** |
| 4 | Run: `conda list -n chan-test --show-channel-urls` | Should show packages from default channels (not restricted to conda-forge) |

#### Part B: Enabled via Environment Variable

| Step | Action | Expected |
|------|--------|----------|
| 1 | Set: `export ALLOW_OVERRIDE_CHANNELS=true` | — |
| 2 | Restart Claude Desktop (or server if HTTP) | — |
| 3 | Ask: "Create environment chan-test-override with Python 3.11 using only conda-forge channel" | Environment created |
| 4 | Run: `conda list -n chan-test-override --show-channel-urls` | Should show packages from conda-forge only |

#### Cleanup
```bash
conda remove -n chan-test --all -y 2>/dev/null
conda remove -n chan-test-override --all -y 2>/dev/null
unset ALLOW_OVERRIDE_CHANNELS
```

**Note**: If Part A fails (channels ARE being overridden without env var), file bug — default should be disabled per release notes.

---

## Modified Tests for RC2

### CORE-001: Full Tools Flow — Logged In (RC2 Modifications)

Base test steps unchanged — see [TESTS_E2E.md](./TESTS_E2E.md#core-001-full-tools-flow).

**Prerequisites** (logged-in state with full token setup):
```bash
# Step 1: Login
anaconda login

# Verify logged in
anaconda whoami
# [EXPECTED] Shows your username

# Step 2: Apply token configuration (required — not done by login alone)
anaconda token install
anaconda token config

# Step 3: Verify default_channels now point to repo.anaconda.cloud
conda config --show default_channels
# [EXPECTED]
#   - https://repo.anaconda.cloud/repo/main
#   - https://repo.anaconda.cloud/repo/r
#   - https://repo.anaconda.cloud/repo/msys2

# Step 4: Verify channel_settings in .condarc
conda config --show channel_settings
# [EXPECTED] Entry for 'https://repo.anaconda.cloud/*' → 'anaconda-auth'

# Step 5: Restart Claude Desktop to pick up .condarc changes
```

> **Gate**: If `default_channels` still points to `repo.anaconda.com` or is unset, do not proceed — token config did not apply correctly.

**RC2-specific verification**:

| Step | RC2 Addition |
|------|--------------|
| All steps | **Count tool calls** — with improved tool context, agent should complete each step with exactly 1 tool call (no retries, no `conda_list_environments` lookups before operations) |
| Step 6 | **DESK-1342 fix verification** — "Delete e2e-test environment" should succeed with single `conda_remove_environment` call using `environment_name`, not `prefix` |

**RC2 Pass criteria** (in addition to base):
- Total tool calls for flow: 7 (one per step)
- Step 6 uses `environment_name="e2e-test"` parameter, not `prefix`
- No agent self-recovery patterns (retry after "environment not found")

**RC2 Fail symptoms** (DESK-1342 not fixed):
- Agent calls `conda_list_environments` before step 6 to look up prefix
- Step 6 returns "environment not found" with wrong prefix
- Agent retries with `prefix` parameter — 2+ tool calls for step 6

**Cleanup** (after test, before CORE-001a):
```bash
# Remove test environment if not already removed
conda remove -n e2e-test --all -y 2>/dev/null

# Logout
anaconda logout

# Remove token configuration to restore default channels
anaconda token remove
# Or manually:
# conda config --remove-key default_channels
# conda config --remove-key channel_settings

# Verify logged out
anaconda whoami
# [EXPECTED] "You are not logged in"

# Verify default_channels restored
conda config --show default_channels
# [EXPECTED] Empty or pointing to repo.anaconda.com (not repo.anaconda.cloud)

# Restart Claude Desktop to pick up .condarc changes
```

---

### CORE-001a: Full Tools Flow — Logged Out (RC2 Modifications)

Base test steps unchanged — see [TESTS_E2E.md](./TESTS_E2E.md#core-001-full-tools-flow).

**Prerequisites** (logged-out state):
```bash
# Step 1: Ensure logged out
anaconda logout 2>/dev/null || true

# Verify logged out
anaconda whoami
# [EXPECTED] "You are not logged in"

# Step 2: Ensure no token configuration
anaconda token remove 2>/dev/null || true

# Step 3: Verify default_channels do NOT point to repo.anaconda.cloud
conda config --show default_channels
# [EXPECTED] Empty or pointing to repo.anaconda.com / defaults (NOT repo.anaconda.cloud)

# Step 4: Restart Claude Desktop to pick up .condarc changes
```

**RC2-specific verification**:

Same as CORE-001 — count tool calls, verify DESK-1342 fix.

**RC2 Pass criteria** (in addition to base):
- Total tool calls for flow: 7 (one per step)
- Step 6 uses `environment_name="e2e-test"` parameter, not `prefix`
- No agent self-recovery patterns

**Cleanup**:
```bash
conda remove -n e2e-test --all -y 2>/dev/null
```

---

### GUARD-001: Guardrails (RC2 Modifications)

Base test unchanged — see [TESTS_E2E.md](./TESTS_E2E.md#guard-001-guardrails).

**RC2-specific verification**:

| Step | RC2 Addition |
|------|--------------|
| Step 2 | With improved destructive tool understanding, confirmation should trigger **immediately** — no ambiguity, no "are you sure?" from agent before tool call |

**RC2 Pass criteria** (in addition to base):
- Step 2: Client-level confirmation prompt appears on first attempt (not after agent hesitation)
- Agent response before confirmation should indicate it understands this is a destructive operation

---

### REGRESS-002: Remove Environment by Name (RC2 Modifications)

Base test unchanged — see [TESTS_E2E.md](./TESTS_E2E.md#regress-002-remove-environment-by-name-ki-003).

> This test is critical for RC2 — environment name operations were listed as "more reliable now" in release notes. Verifies DESK-1342 fix.

**RC2-specific verification**:

| Step | RC2 Addition |
|------|--------------|
| Step 1 | Verify single `conda_remove_environment` call — no `conda_list_environments` lookup first |
| Step 1 | Tool call must use `environment_name` parameter, not `prefix` |

**RC2 Pass criteria** (in addition to base):
- Exactly 1 tool call (`conda_remove_environment`)
- Tool call uses `environment_name` parameter, not `prefix`
- No agent self-recovery patterns

**RC2 Fail symptoms** (DESK-1342 not fixed):
- Tool returns "environment not found" with wrong prefix (e.g., nested path)
- Agent performs lookup via `conda_list_environments` then retries with `prefix`
- More than 1 tool call total

---

## Bug Fix Verification Checklist

Verify fixes claimed in RC2 release notes:

| Bug | Verification Method | Status |
|-----|---------------------|--------|
| DESK-1342 (env name operations) | REGRESS-002, CORE-001 step 6 | [ ] |
| DESK-1355 (mcp-compose hang) | Run 15+ tool calls without hang | [ ] |
| DESK-1366 (logger hang) | Run 15+ tool calls without hang | [ ] |
| General stability | Complete full CORE-001 without errors | [ ] |

**Note**: Check with dev team which specific bugs are fixed in RC2 before testing. Not all RC1 bugs may be addressed.

---

## Tests NOT Changed for RC2

| Test | Reason |
|------|--------|
| AUTH-001 | Anonymous mode — no RC2 changes affect this |
| AUTH-001a | **Unblocked in RC2** — URL routing fixed, anonymous users correctly get 403 auth error |

---

### AUTH-002: Authenticated Mode (RC2 Modifications)

Base test unchanged — see [TESTS_E2E.md](./TESTS_E2E.md#auth-002-authenticated-mode).

**Prerequisites**: Same as CORE-001 (logged in) — see [CORE-001 prerequisites](#core-001-full-tools-flow--logged-in-rc2-modifications).

**Cleanup** (after test):
```bash
# Remove test environment if not already removed
conda remove -n auth-test --all -y 2>/dev/null

# Logout
anaconda logout

# Remove token configuration to restore default channels
anaconda token remove
# Or manually:
# conda config --remove-key default_channels
# conda config --remove-key channel_settings

# Verify logged out
anaconda whoami
# [EXPECTED] "You are not logged in"

# Verify default_channels restored
conda config --show default_channels
# [EXPECTED] Empty or pointing to repo.anaconda.com (not repo.anaconda.cloud)

# Restart Claude Desktop to pick up .condarc changes
```

---

## RC2 Test Matrix Assignment

Per [TEST_MATRIX_rc2.md](./TEST_MATRIX_rc2.md):

### QA 1 (3 configs)

```
macOS, Python 3.13:
[ ] SETUP-001: Installation disclaimer
[ ] CORE-001: Full tools flow (with RC2 tool count verification)
[ ] GUARD-001: Guardrails (with RC2 confirmation verification)
[ ] AUTH-002: Authenticated mode
[ ] CHAN-001: Override channels behavior (both parts)
[ ] REGRESS-002: DESK-1342 fix verification

macOS, Python 3.10:
[ ] SETUP-001: Installation disclaimer
[ ] CORE-001: Full tools flow

Windows, Python 3.10 — logged out:
[ ] SETUP-001: Installation disclaimer
[ ] CORE-001: Full tools flow (verifies DESK-1385 fix)

Windows, Python 3.10 — logged in:
[ ] CORE-001: Full tools flow (verifies DESK-1386 fix)
```

### QA 2 (1 config)

```
Windows, Python 3.13 — logged out:
[ ] SETUP-001: Installation disclaimer
[ ] CORE-001: Full tools flow (if DESK-1344 fixed)

Windows, Python 3.13 — logged in:
[ ] CORE-001: Full tools flow
[ ] AUTH-002: Authenticated mode
[ ] GUARD-001: Guardrails
```

---

## Known Limitations (Not Fixed in RC2)

| Issue | Impact | Workaround |
|-------|--------|------------|
| MCP doesn't pass credentials (DESK-1401) | AUTH-002 blocked — authenticated users get 403 | AUTH-001a passes (anonymous denial works); AUTH-002 cannot be completed |
| Server may get stuck | Session becomes unresponsive | Restart Claude Desktop / server |

---

## Server Stuck Recovery Procedure

If the server becomes unresponsive during testing:

```bash
# macOS
pkill -f "anaconda-mcp"
pkill -f "environments-mcp-server"
# Restart Claude Desktop (Cmd+Q, reopen)

# Windows
taskkill /F /IM "anaconda-mcp.exe" 2>nul
taskkill /F /IM "environments-mcp-server.exe" 2>nul
# Restart Claude Desktop
```

Document when this occurs — helps track stability improvement.

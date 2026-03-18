# Anaconda MCP - Known Issues & Testing Findings

## Source
Issues documented from internal testing conversations (Feb 2026).

---

## Resolved Issues

### KI-001: Environment Not Actually Deleted
**Status**: Fixed (PR merged)
**Version Fixed**: 0.1.2+
**Description**: MCP reported environment deletion as complete, but environment was still present.
**Root Cause**: Issue with deletion logic when environment was activated in CLI.
**Test Case**: Verify deletion works when environment is:
- [ ] Not activated
- [ ] Activated in another terminal
- [ ] The current active environment

---

### KI-024: RC2 Installation Fails with Python 3.10 / 3.11 / 3.12
**Status**: Fixed — [DESK-1405](https://anaconda.atlassian.net/browse/DESK-1405)
**Version Fixed**: 1.0.0.rc.2 (resolved 2026-03-16)
**Severity**: High
**Description**: `conda create` with `anaconda-mcp=1.0.0.rc.2` and `environments-mcp-server=1.0.0.rc.2` failed on Python 3.10, 3.11, and 3.12. RC2 is now installable on all supported Python versions (3.10 – 3.13).

---

### KI-004: Extra Fields in Settings Causes Crash
**Status**: Fixed (PR #20)
**Version Fixed**: Post-0.1.2
**Description**: `pydantic_core.ValidationError: Extra inputs are not permitted` when user has extra env vars like `openai_api_key`.
**Root Cause**: Pydantic settings was set to forbid extra fields.
**Test Case**:
- [ ] Set random environment variables and run anaconda-mcp
- [ ] Verify no crash on extra env vars

---

## Open Issues

### KI-002: Environment Misclassified as "base"
**Status**: Open
**Severity**: Medium
**Description**: The `anaconda-mcp-testing` environment was incorrectly classified as "base" in list output.
**Reproduction**: Create environment, list environments, check name field.
**Test Case**:
- [ ] Verify environment names are correctly reported
- [ ] Verify "base" only refers to actual base environment

---

### KI-003: Environment Operations Fail by Name — Wrong Prefix Resolved
**Status**: Fixed — [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342)
**Severity**: High
**Version Fixed**: 1.0.0.rc.2
**Regression test**: `tests/qa/http_tools/test_env_name_resolution.py::TestEnvironmentNameResolution::test_ki003_remove_environment_by_name`
**Related**: KI-002 (misclassified "base" environment is the root cause)

**Description**: `conda_remove_environment(environment_name="<name>")` — and other tools that accept a name — resolve the wrong prefix for the target environment and return `"Conda environment not found"` even though the environment exists. Only passing the full `prefix` path works as a workaround.

**Root cause**: The `environments-mcp-server` subprocess runs inside its own conda environment (e.g. `anaconda-mcp-rc-py313` at `/opt/miniconda3/envs/anaconda-mcp-rc-py313`). Due to KI-002, that environment is misclassified as "base". When a tool resolves a named environment it constructs the prefix as `<base>/envs/<name>` — but `<base>` is incorrectly set to the server's own environment path, not the real conda root. The resulting prefix (`/opt/miniconda3/envs/anaconda-mcp-rc-py313/envs/<name>`) does not exist, so `EnvironmentLocationNotFound` is raised.

**Example**:
```
# Requested:  conda_remove_environment(environment_name="guard-env-remove-test")
# Resolved:   /opt/miniconda3/envs/anaconda-mcp-rc-py313/envs/guard-env-remove-test  ← WRONG
# Correct:    /opt/miniconda3/envs/guard-env-remove-test
```

**Expected behavior**: The tool resolves the correct prefix from `conda env list` (or equivalent), finds `/opt/miniconda3/envs/guard-env-remove-test`, and removes it successfully. Single tool call, `is_error: false`.

**Observed behavior**: `is_error: true` — `"Conda environment not found. Perhaps wrong name or prefix? Details: ('conda:environment:not-found', 'requested conda environment not found: prefix=\"/opt/miniconda3/envs/anaconda-mcp-rc-py313/envs/guard-env-remove-test\"', ...)"`.
The LLM then self-recovers: calls `conda_list_environments`, retries with the full prefix — resulting in 3+ tool calls instead of 1.

**Affected tools**: Any tool that resolves `environment_name → prefix` using `context.target_prefix`. Confirmed on `conda_remove_environment`; likely affects `conda_install_packages`, `conda_remove_packages`, `conda_list_environment_packages`.

**Observed on**:

| Client | Transport | Python | Result |
|--------|-----------|--------|--------|
| Cursor | Streamable HTTP | 3.13 | Confirmed — wrong prefix, `EnvironmentLocationNotFound` |
| (likely all) | (likely all) | (likely all) | Bug is in prefix resolution logic, not transport/client-specific |

**Workaround**: Pass the full `prefix` path instead of `environment_name`.

**E2E fail symptoms** (see REGRESS-002):
- First tool call returns `"Conda environment not found"` with wrong prefix in the error details
- Agent self-recovers with `conda_list_environments` + retry by prefix — 3+ tool calls total
- Or agent gives up and reports the environment does not exist

---

### KI-005: Channel Credentials Not Picked Up (URL Routing)
**Status**: Done — URL routing fixed; replaced by [KI-020](#ki-020-mcp-returns-403-on-repoanacondacloud-despite-valid-authentication) / [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401)
**Severity**: Medium
**Bug**: [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358)
**Description**: Originally reported as URL routing issue (requests going to `conda.anaconda.org` instead of `repo.anaconda.cloud`). Investigation in RC2 showed URL routing is now correct — requests reach `repo.anaconda.cloud`. The actual issue is credentials not being passed (see KI-020).
**Resolution**:
- URL routing fixed — requests now go to correct URL
- AUTH-001a **unblocked and passing** — anonymous users correctly get 403 auth error
- AUTH-002 still blocked by KI-020/DESK-1401 — authenticated users also get 403 (credentials not passed)

---

### KI-020: MCP Returns 403 on repo.anaconda.cloud Despite Valid Authentication
**Status**: Open
**Severity**: Major
**Bug**: [DESK-1401](https://anaconda.atlassian.net/browse/DESK-1401)
**Description**: `conda_create_environment` (and likely other conda operations) fails with HTTP 403 Forbidden on `repo.anaconda.cloud` when invoked via MCP, even though authentication is fully configured and the same operation succeeds in terminal.

**Evidence**:
| Check | Result |
|-------|--------|
| `anaconda-auth` in MCP env | ✓ installed |
| `anaconda whoami` from MCP env | ✓ authenticated |
| `channel_settings` configured | ✓ `anaconda-auth` handler |
| `default_channels` | ✓ points to `repo.anaconda.cloud` |
| Terminal `conda create` | ✓ works |
| MCP `conda_create_environment` | ✗ 403 Forbidden |

**Impact**:
- Cannot create environments or install packages via MCP when `default_channels` points to `repo.anaconda.cloud`
- AUTH-002 blocked — authenticated flows fail (credentials not passed)
- AUTH-001a passing — anonymous users correctly get 403 (expected behavior)

**Root cause (hypothesis)**: `environments-mcp-server` spawns conda in a way that doesn't trigger the `anaconda-auth` plugin (possibly missing environment variables, subprocess isolation, or invoking conda as library instead of CLI).

**Workaround**: None — authenticated channel access via MCP tools is not functional until resolved.

**Blocks**: AUTH-002

**Does NOT block**: AUTH-001a (anonymous denial works correctly)

**Related**: [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358) / KI-005 (different issue — URL routing vs credentials)

---

### KI-021: Tool "Not Loaded Yet" Error on First Call to `conda_install_packages`
**Status**: Open — [DESK-1402](https://anaconda.atlassian.net/browse/DESK-1402)
**Severity**: Medium
**Observed**: 2026-03-13 (macOS, Python 3.13, Claude Desktop STDIO) — reproduced multiple times

**Description**: First call to `conda_install_packages` fails with error:
```
Error: 'anaconda-mcp:conda_install_packages' has not been loaded yet. You do not have the correct parameter names for this tool. Call tool_search with a relevant query first to load the tool definition and discover the correct parameters...
```
Retry with identical parameters succeeds immediately after "Loading tools" appears.

**Key observation**: Agent uses correct parameters both times — this is a tool initialization/loading issue, not an agent behavior issue.

**Affected tool**: Only observed for `conda_install_packages` so far. Other tools (`conda_list_environments`, `conda_create_environment`) work on first call.

**Impact**: Extra tool call required. Does not block functionality — retry always succeeds.

**Possible causes**:
- Lazy loading of tool definitions
- Race condition in tool discovery/registration
- Client-side tool schema caching not populated until first use attempt

---

### KI-022: `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS=false` Parsed as Truthy
**Status**: Open — [DESK-1403](https://anaconda.atlassian.net/browse/DESK-1403)
**Severity**: Low
**Component**: `environments-mcp-server`
**Observed**: 2026-03-13 (macOS, Python 3.13, Claude Desktop)

**Description**: Setting `CONDA_MCP_SERVER_ALLOW_OVERRIDE_CHANNELS=false` does not hide the `override_channels` parameter. The string `"false"` is parsed as truthy instead of boolean `False`.

**Root cause**: In Python, `bool("false")` → `True` (non-empty string). Pydantic Settings should parse boolean strings but isn't doing so for this field.

**Impact**: Users cannot explicitly disable `override_channels` via env var.

**Workaround**: Don't set the env var at all — default is `False`.

**Related**: CHAN-001 Part C, [BUG_REPORT_KI-022.md](./BUG_REPORT_KI-022.md)

---

### KI-023: Claude Desktop 1.1.6679 — MCP Server Launch/Kill Loop, `tools/call` Never Dispatched
**Status**: Open — [DESK-1408](https://anaconda.atlassian.net/browse/DESK-1408)
**Severity**: High
**Component**: Claude Desktop (client-side regression)
**Platform**: macOS
**Observed**: 2026-03-13 (after Claude Desktop auto-updated to v1.1.6679)

**Description**: After Claude Desktop updated to v1.1.6679 on macOS, the anaconda-mcp server enters a launch/kill loop on startup. The server completes a healthy handshake and registers all 6 tools, but no `tools/call` ever arrives. All MCP operations silently fail — the client never dispatches any tool calls.

The same config works without issue in Cursor (STDIO) and in lower Claude Desktop versions.

**Root cause (hypothesis)**: A timing/race condition introduced in Claude Desktop v1.1.6679. Claude Desktop appears to request the MCP server connection twice in rapid succession during startup — the second request kills the first before the server stabilizes. The `mcp-compose` internal HTTP server on port 4041 takes ~3 seconds to initialize before stdio is ready; the default `--delay 5` no longer provides sufficient margin.

This is consistent with known Anthropic issues:
- [#22299](https://github.com/anthropics/claude-code/issues/22299) — server handshake completes but `tools/call` never arrives, same `UtilityProcess Check: Extension not found` warning
- [#31864](https://github.com/anthropics/claude-code/issues/31864) — identical launch/kill loop with same warning

**Evidence** (from `~/Library/Logs/Claude/main.log`):
```
15:10:41 Launching MCP Server: anaconda-mcp
15:10:41 Shutting down MCP Server: anaconda-mcp  ← killed immediately
15:10:41 Launching MCP Server: anaconda-mcp
15:10:41 Shutting down MCP Server: anaconda-mcp  ← killed again
[warn] UtilityProcess Check: Extension anaconda-mcp not found in installed extensions
```

**Workaround**: Add `--delay 15` to the server startup args in `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
"anaconda-mcp": {
  "command": "/opt/miniconda3/envs/anaconda-mcp-rc2-py312/bin/python",
  "args": ["-m", "anaconda_mcp", "serve", "--delay", "15"],
  "env": {
    "ANACONDA_MCP_PYTHON_EXECUTABLE": "/opt/miniconda3/envs/anaconda-mcp-rc2-py312/bin/python",
    "MCP_COMPOSE_CONFIG_DIR": "/opt/miniconda3/envs/anaconda-mcp-rc2-py312/lib/python3.12/site-packages/anaconda_mcp"
  }
}
```

**Affected versions**: `anaconda-mcp=1.0.0.rc.2`, `environments-mcp-server=1.0.0.rc.2`, `mcp SDK=1.26.0`, `fastmcp=3.0.2`, `mcp_compose=0.1.11`

---

### KI-006: Tool Selection Conflicts
**Status**: By Design (Claude behavior)
**Severity**: Low
**Description**: When multiple MCP tools are installed, Claude may pick wrong tool for generic requests like "List all environments".
**Workaround**: Explicitly mention "anaconda-mcp" or "conda" in request.
**Test Case**:
- [ ] Test with only anaconda-mcp installed
- [ ] Test with multiple MCP tools installed
- [ ] Document recommended phrasing

---

### KI-007: HTTP Transport Hangs or Fails to Connect

**If you experience**:
- Server hangs at "Connecting to Streamable HTTP server..."
- Never shows "Discovered X tools"
- Error: "address already in use"
- Empty response from API calls

**Then do**:
```bash
# Kill all zombie processes
pkill -9 -f "anaconda-mcp"
pkill -9 -f "environments_mcp"
lsof -ti:8888 | xargs kill -9 2>/dev/null
lsof -ti:4041 | xargs kill -9 2>/dev/null

# Wait and retry
sleep 2
anaconda-mcp serve --config /tmp/http-config.toml
```

**Root cause**: Zombie processes from previous test runs hold ports 8888 or 4041, preventing new server from connecting to downstream.

**Prevention**: Always cleanly stop servers with Ctrl+C. The `start-http-server.sh` script includes cleanup.

---

### KI-008: HTTP Setup Suggests Wrong Server Command
**Status**: Open (Bug) — [DESK-1356](https://anaconda.atlassian.net/browse/DESK-1356)
**Severity**: High
**Version**: 1.0.0.rc.1
**Description**: When running `anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888`, the CLI suggests:
```
Start the server manually: anaconda-mcp serve --port 8888
```
But this command starts server in **STDIO mode**, not HTTP mode. Claude Desktop cannot connect.

**Note**: The `serve` command has no `--transport` flag. HTTP mode **requires a config file**.

**Workaround** - use the script which creates proper config:
```bash
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
```

**Root cause**: CLI suggests impossible command. Should either:
1. Add `--transport` flag to `serve` command, or
2. Suggest using a config file for HTTP mode

---

### KI-009: Claude Desktop Does Not Support HTTP Transport
**Status**: By Design (Not a bug)
**Severity**: N/A - Use Cursor for HTTP testing
**Description**: Claude Desktop only supports STDIO transport. The `url`/`transport` config format is not supported.

**Evidence**:
- Official MCP quickstart only shows STDIO examples: https://modelcontextprotocol.io/quickstart/user
- Claude Desktop "Remote servers" feature uses OAuth/cloud, not direct HTTP: https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp
- MCP clients page doesn't list transport support per client: https://modelcontextprotocol.io/clients

**Observed behavior**: Claude Desktop crashes with `TypeError: Cannot read properties of undefined (reading 'value')` when config contains:
```json
{
  "anaconda-mcp": {
    "url": "http://localhost:8888/mcp",
    "transport": "streamable-http"
  }
}
```

**Solution**:
- **Claude Desktop**: Use STDIO transport only
- **HTTP transport testing**: Use **Cursor** (confirmed working) or direct API calls (curl)

---

### KI-010: False "Environment Not Found" When Installing Nonexistent Package
**Status**: Open (Bug) — [DESK-1341](https://anaconda.atlassian.net/browse/DESK-1341)
**Severity**: Medium
**Version**: 1.0.0rc1
**Regression test**: `tests/qa/http_tools/test_guard_install_nonexistent_pkg.py`

**Description**: `conda_install_packages(environment="<name>", packages=["nonexistent-package-xyz123"])` returns `is_error=true` with `"The environment was not found. Make sure you are providing the correct name or prefix"` even though the environment exists. The misleading error causes the LLM to list environments and retry by prefix, producing extra tool calls.

**Root cause**: `anaconda_connector_conda` creates a `Context(search_path=())` for each call. With an empty search path conda does not populate `envs_dirs`, so `context.target_prefix` raises `EnvironmentLocationNotFound` before the solver is invoked. `install_packages.py:93` catches this and returns the wrong error message.

**Expected behavior**: Returns `is_error=true` with a package-resolution error (e.g. `"Could not resolve the packages"`). Single tool call, no retry.

**Observed on**:

| Client | Transport | Python | Result |
|--------|-----------|--------|--------|
| Cursor | Streamable HTTP | 3.13 | Incorrect error message |
| Cursor | STDIO | 3.10, 3.13 | Incorrect error message |
| Claude Desktop | STDIO | 3.10 | Incorrect error message |

**Note on hanging**: In one isolated run (Cursor / Streamable HTTP / Python 3.13) the session hung after the retry-by-prefix call and did not recur on retest. This is consistent with the `mcp-compose` proxy bug documented in [KI-011 / DESK-1355](./KNOWN_ISSUES.md#ki-011-mcp-compose-proxy-hangs-and-corrupts-session-on-tool-error).

---

### KI-018: First `conda_list_environments` Call Always Hangs on Windows (Cold-Start Timeout)
**Status**: Open — [DESK-1385](https://anaconda.atlassian.net/browse/DESK-1385)
**Severity**: High
**Component**: `environments_mcp_server`
**Platform**: Windows only
**Auth state**: Any (logged in or logged out)
**Bug report**: [`KI-018-bug-report.md`](../bug_details/win_start/KI-018-bug-report.md)

The first conda tool call after server startup always exceeds the 30-second GET SSE stream timeout on Windows. Windows cold-start overhead (DLL loading, Windows Defender scanning, conda batch script activation) makes the first `conda` invocation take >30 seconds. The result is computed and returned by the server ("duplicate response suppressed") but is lost in the proxy layer. On macOS the identical call completes in <1 second. Fix: pre-warm conda in `environments_mcp_server` at startup time.

---

### KI-019: After First-Call Hang on Windows, Retry Also Fails When User Is Logged In
**Status**: Open — [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386)
**Severity**: High
**Component**: `environments_mcp_server` / `anaconda_mcp` auth/telemetry
**Platform**: Windows only
**Auth state**: Logged in (telemetry initialized)
**Bug report**: [`KI-019-bug-report.md`](../bug_details/win_start/KI-019-bug-report.md)

When the user is logged in, the retry after the KI-018 first-call hang also fails with `unhandled errors in a TaskGroup`. Telemetry initialization causes additional background work per tool call; after the GET SSE stream disconnects and reconnects, this work encounters an unhandled error that corrupts the async task group. Logged-out sessions recover on retry (no telemetry work → no corruption). Fix KI-018 to eliminate the trigger; additionally harden telemetry error handling to degrade gracefully on session invalidation.

---

### KI-011: mcp-compose Proxy Hangs and Corrupts Session on Tool Calls
**Status**: Open — Root cause identified (SSE stream timeout after 30 seconds)
**Jira**: [DESK-1409](https://anaconda.atlassian.net/browse/DESK-1409) (new), [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355) (partial fix)
**Component**: `mcp-compose` / MCP SDK SSE handling
**Report to**: https://github.com/datalayer/mcp-compose
**Detailed docs**: `tests/qa/_ai_docs/bug_details/proxy_hang/`

**Root cause identified (2026-03-17)**: Live diagnostics captured during hang show the SSE stream disconnects after exactly 30 seconds when the response stops arriving:
```
17:39:55 - GET http://localhost:4041/mcp "HTTP/1.1 200 OK"   <- SSE stream opened
... 30 SECONDS - RESPONSE NEVER ARRIVES ...
17:40:25 - GET stream disconnected, reconnecting in 1000ms... <- TIMEOUT!
```

After ~17 tool calls, responses stop being forwarded. The 30-second SSE read timeout fires, and TaskGroup state becomes corrupted. All subsequent requests fail with "unhandled errors in a TaskGroup (1 sub-exception)".

**Root cause confirmed (2026-03-16)**: Isolation testing definitively proved the bug is in `mcp-compose` library itself, NOT in `environments_mcp_server` or `anaconda-mcp` wrapper:

| Test | Result | Hang at |
|------|--------|---------|
| `environments_mcp_server` direct (50 iterations) | PASS | — |
| `mcp-compose` direct, no anaconda-mcp wrapper (20 iterations) | FAIL | iteration 18 |
| `anaconda-mcp serve` full stack (20 iterations) | FAIL | iteration 18 |

**Key evidence**:
- `environments_mcp_server` handles 50+ rapid sequential calls without any hang
- `mcp-compose` hangs at iteration 18 when invoked directly via `python -m mcp_compose serve` (no `anaconda-mcp` code involved)
- Same hang iteration (~18) whether using `anaconda-mcp serve` or `mcp-compose` directly

**Diagnostic scripts**: `tests/qa/_ai_docs/scripts/test-env-mcp-direct.sh`, `tests/qa/_ai_docs/scripts/test-mcp-compose-direct.sh`

**Severity**: High (process-wide corruption; server restart required to recover)
**Version**: mcp-compose 0.1.10 (original), 0.1.11 (partial fix, still hangs at ~17-18)
**Regression tests**: `tests/qa/http_tools/test_guard_proxy_error_hang.py`, `tests/qa/http_tools/test_guard_happy_path_hang.py`, `tests/qa/stdio_tools/test_guard_proxy_error_hang_stdio.py`

**Description**: When `mcp-compose` receives a tool result (whether a success or an error response), it can hang and corrupt the httpx connection pool under rapid sequential calls. All subsequent calls block indefinitely. Only restarting `mcp-compose` recovers.

The hang was originally observed only on error-returning calls; testing on 2026-03-16 confirmed it also occurs on happy-path (success) calls — see **Happy-path hang** observation below.

**Root cause (updated 2026-03-17)**: After ~17 tool call sessions, responses stop being forwarded from downstream server. The SSE stream has a 30-second read timeout; when no data arrives, the stream disconnects and mcp-compose attempts reconnection which fails to recover the pending request. TaskGroup internal state becomes corrupted, blocking all subsequent requests.

**Previous hypothesis**: `mcp-compose` uses deprecated `streamablehttp_client` which has a hidden 5-minute SSE read timeout. When FastMCP serves results inline (200 OK) instead of via SSE, the SSE cleanup hangs waiting for the timeout, leaking the connection pool slot.

**Fix status** (as of 2026-03-10):
- PR #28 merged into mcp-compose 0.1.11 on 2026-03-07
- Fix replaces deprecated `streamablehttp_client` with `streamable_http_client` + explicit `httpx.AsyncClient`
- **Improvement**: Hang threshold improved from ~4 iterations to ~16-17 iterations
- **Still failing**: After ~16-17 rapid sequential calls, the hang still occurs

**Test results** (mcp-compose 0.1.11, MCP SDK 1.26.0):

| Test | Before Fix | After Fix (0.1.11) | Date |
|------|------------|-------------------|------|
| HANG-001 (remove_environment × 20) | Hangs at iteration 4 | ✅ **Passed** (all 20) | 2026-03-10 |
| HANG-002 (install_packages × 20, error path) | Hangs at iteration 4 | ❌ Hangs at iteration ~16-17 | 2026-03-10 |
| HANG-003 (mixed error + health × 40) | Hangs early | ❌ Other error (see below) | 2026-03-10 |
| HANG-004 (install_packages × 20, **happy path**) | — | ❌ Hangs at iteration 17-18 | 2026-03-16 |

**HANG-003 note**: Now fails with `'NoneType' object has no attribute 'kill'` — this is an unrelated bug in `environments_mcp_server`, not KI-011.

**HANG-004 note**: Happy-path installs (success response, `is_error=false`) trigger the same hang as error-path installs. See **Happy-path hang** observation below.

**Isolation test results** (2026-03-16, mcp-compose 0.1.11):

| Test | Iterations | Result | Conclusion |
|------|------------|--------|------------|
| `test-env-mcp-direct.sh` (environments_mcp_server only) | 50 | ✅ All passed | Server is NOT the problem |
| `test-env-mcp-direct.sh` with DELAY=0 | 30 | ✅ All passed | Server handles max pressure |
| `test-mcp-compose-direct.sh` (mcp-compose, no anaconda-mcp) | 20 | ❌ Hangs at 18 | Bug is in mcp-compose |
| pytest `test_guard_happy_path_hang.py` (anaconda-mcp serve) | 20 | ❌ Hangs at 18 | Confirms mcp-compose is root cause |

**Remaining issue**: The SSE response handler receives 0 events and times out after 60 seconds. Debug logging shows:
1. `POST tools/call` returns 200 OK with `content-type: text/event-stream`
2. `EventSource created, starting aiter_sse loop...`
3. 60 seconds pass with no events
4. `[SSE_RESP] EXCEPTION: after 0 events elapsed=60.001s`
5. `GET stream disconnected, reconnecting in 1000ms...`

**Root cause** (confirmed 2026-03-16): The bug is in `mcp-compose`'s connection/session management. When handling rapid sequential tool calls, `mcp-compose` fails to forward the response to the client after ~17-18 iterations. The downstream server (`environments_mcp_server`) processes all requests correctly — isolation testing confirmed it handles 50+ rapid calls without issue. The response is computed and returned by `environments_mcp_server`, but `mcp-compose` drops it.

**Additional observation — hang on happy-path install (2026-03-16, reproducible)**:

The hang is **not limited to error responses**. HANG-004 (`test_guard_happy_path_hang.py`) demonstrated the same hang at iteration 17/20 of back-to-back `conda_install_packages` calls that all returned `is_error=false`.

**Server-side signature** (from `mcp-compose` log, iteration 17, starting at 21:32:26):

```
POST  → 200 OK       (initialize)
GET   → 200 OK       (SSE stream — opened BEFORE 202, indicating the race condition)
POST  → 202 Accepted (notifications/initialized — out of order)
POST  → 200 OK       (tools/call dispatched)
— 60 seconds of silence —
GET stream disconnected, reconnecting in 1000ms...
```

The **5th POST** (result forwarded to client) and the **DELETE** (session cleanup) never arrived. The proxy received the tool result from `environments_mcp_server` but failed to forward it to the test client, which hit the 60-second `httpx.ReadTimeout`.

Compare with a healthy iteration (e.g. iteration 16):
```
POST  → 200 OK       (initialize)
POST  → 202 Accepted (notifications/initialized — correct order)
GET   → 200 OK       (SSE stream)
POST  → 200 OK       (tools/call)
POST  → 200 OK       (5th POST — result forwarded ✓)
DELETE → 200 OK      (session cleanup ✓)
```

**Why this matters for Claude Desktop**: Real sessions mix `conda_install_packages` success calls with `conda_list_environments` and other tools. The hang does not require any error to be present — any rapid sequence of tool calls can trigger the proxy race. This explains the extended Claude Desktop sessions hanging on happy-path installs that motivated this test.

**Regression test**: `tests/qa/http_tools/test_guard_happy_path_hang.py::TestHappyPathHangHttp::test_hang_004_repeated_install_does_not_hang`

---

**Additional observation — hang on first single call (2026-03-11, one-time, not reproducible)**:

The hang was observed **once** on the very first `conda_list_environments` tool call — no prior error-returning calls, no prior disconnects. Observed once, not reproduced in subsequent sessions. Kept here as field evidence supporting KI-011/KI-013, not as a standalone reproducible bug.

**Exact sequence (2026-03-11, first Claude session of the day)**:

1. Claude Desktop had `anaconda3\envs\anaconda-mcp-rc-py311\python.exe` in config — that env no longer existed
2. PI-004 ENOENT retry loop fired: 3 rapid failed spawns (18:42:53–18:42:58)
3. Config updated to `miniconda3\envs\anaconda-mcp-rc-py310\python.exe`; Claude Desktop reconnected with several rapid init/shutdown cycles
4. Server eventually came up; tools registered
5. First tool call `conda_list_environments` → hung: GET stream dropped at ~30s (= `timeout=30`), reconnect succeeded, result never arrived
6. Claude Desktop restarted; all subsequent sessions ran `conda_list_environments` successfully in ~1s

**Key evidence — "duplicate response suppressed"**:

```
Request 4 cancelled - duplicate response suppressed
```

This confirms `mcp-compose` **received the result from `environments_mcp_server`** but discarded it because the GET SSE stream had already disconnected and Claude had timed out. The server did its job — the response was lost in the proxy layer. This is the same response-loss mechanism documented in KI-011/KI-013, triggered here by a degraded startup (ENOENT loop + rapid init/close cycles) rather than many rapid error calls.

**Note on March 10 session**: A similar first-call hang with "duplicate response suppressed" was observed on 2026-03-10 (rapid init/close cycles, full Anaconda install). Same proxy response-loss pattern; different precondition.

**Windows first-call hang (2026-03-11)**: The same `duplicate response suppressed` mechanism was reproduced on Windows (stdio transport, Claude Desktop). Root cause and full investigation — including 5 test sessions, macOS comparison, and auth-state analysis — are documented in [KI-018](../bug_details/win_start/KI-018-bug-report.md) (cold-start hang, any auth state) and [KI-019](../bug_details/win_start/KI-019-bug-report.md) / [DESK-1386](https://anaconda.atlassian.net/browse/DESK-1386) (telemetry blocks retry when logged in).

**Workaround**: Restart `mcp-compose` when hangs occur:
```bash
pkill -9 -f "anaconda-mcp"
pkill -9 -f "environments_mcp"
lsof -ti:8888 | xargs kill -9 2>/dev/null
lsof -ti:4041 | xargs kill -9 2>/dev/null
sleep 2
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
```
---

### KI-012: MCP Server Initialization Hangs When Port 4041 Is Occupied by a Non-Responsive Process
**Status**: Open — [DESK-1359](https://anaconda.atlassian.net/browse/DESK-1359)
**Severity**: Medium
**Version**: 1.0.0.rc.1

**Description**: When port 4041 is occupied by a process that accepts TCP connections but never replies, `mcp-compose` connects silently and waits indefinitely. Cursor times out after 60 seconds (`MCP error -32001: Request timed out`), restarts `anaconda_mcp serve`, and the loop repeats. No error identifies the cause.

**Root cause**: `health_check_enabled = false` in `mcp_compose.toml`. `reconnect_on_failure` only fires on refused connections — a silent hung connection never errors, so neither reconnect nor any diagnostic fires.

**Natural trigger**: A KI-011 hang leaves `environments_mcp_server` in a corrupted state — port 4041 stays bound but stops responding. The next Cursor restart connects to the existing hung server.

**Reproduce deterministically**:
```bash
nc -lk 4041   # accepts connections, never replies
```
Then open/reload Cursor.

**Note**: `Login failed — OSError: [Errno 48] Address already in use` that appears in logs is a red herring — it is caused by a separate process holding the OAuth redirect port and does not affect server initialization.

**Workaround**:
```bash
lsof -ti:4041 | xargs kill -9 2>/dev/null
```
Then reload Cursor.

---

### KI-025: Claude Desktop fails to create conda environment after user adds PYTHONASYNCIODEBUG=1 to MCP config
**Status**: Open — [DESK-1410](https://anaconda.atlassian.net/browse/DESK-1410)
**Severity**: Low (production) / Medium (debug mode)
**Component**: environments_mcp_server (conda transaction layer)
**Detailed docs**: `tests/qa/_ai_docs/bug_details/asyncio_thread/`

**Description**: User extends their Claude Desktop MCP server configuration with `PYTHONASYNCIODEBUG=1` (e.g., for debugging KI-011 proxy hang). After this change, `conda_create_environment` fails with "Non-thread-safe operation invoked on an event loop other than the current one" error.

**User action that triggers the bug**: Adding `"PYTHONASYNCIODEBUG": "1"` to the `env` section of anaconda-mcp configuration.

**Key finding**: The bug only manifests when `PYTHONASYNCIODEBUG=1` is set. Without this flag, environment creation works normally. The flag exposes a latent thread-safety violation that is silent in production.

**Workaround**: Remove `PYTHONASYNCIODEBUG=1` from MCP config.

**Related**: KI-011 (proxy hang) - this issue was discovered while debugging KI-011.

---

### KI-026: Cannot run `anaconda login` while Claude Desktop with anaconda-mcp is running (port 8000 conflict)
**Status**: Open — [DESK-1411](https://anaconda.atlassian.net/browse/DESK-1411)
**Severity**: Medium
**Component**: anaconda-mcp / mcp-compose
**Detailed docs**: `tests/qa/_ai_docs/bug_details/port_conflict/`

**Description**: User cannot login to Anaconda from command line while Claude Desktop with anaconda-mcp is running. Both mcp-compose and `anaconda login` OAuth flow require port 8000, causing "Address already in use" error.

**User scenario**: User has Claude Desktop running → opens terminal → runs `anaconda login` → fails with `OSError: [Errno 48] Address already in use`.

**Root cause**: Port 8000 conflict:
- mcp-compose uses port 8000 for upstream HTTP server
- anaconda-auth uses port 8000 for OAuth redirect callback

**Workarounds**:
1. Quit Claude Desktop → `anaconda login` → restart Claude Desktop
2. Login before starting Claude Desktop
3. ~~Use API key instead~~ — **blocked by KI-027** (API key auth doesn't work for MCP channel access)

**Proposed resolution (feature request)**: Make mcp-compose upstream port configurable, or change default to avoid conflict with anaconda-auth.

---

### KI-027: `conda_create_environment` fails with "Token not found" when using API key authentication instead of interactive login
**Status**: Open — [DESK-1413](https://anaconda.atlassian.net/browse/DESK-1413)
**Severity**: Medium
**Component**: anaconda-auth / anaconda-mcp
**Detailed docs**: `tests/qa/_ai_docs/bug_details/api_key_auth/`

**Description**: API key authentication via `ANACONDA_AUTH_API_KEY` environment variable or `~/.anaconda/config.toml` does not grant access to private conda channels when using anaconda-mcp. The `anaconda-auth` plugin requires a repo token installed via `anaconda token install`.

**User scenario**: User sets API key → configures `.condarc` with private channels → asks Claude to create environment → fails with "Token not found for defaults. Please install token with `anaconda token install`."

**Root cause**: The `anaconda-auth` plugin distinguishes between:
- **API key**: Authenticates identity (works for `anaconda whoami`)
- **Repo token**: Grants channel access (required for conda operations)

The API key alone is insufficient for conda channel access.

**Additional issue**: Even if API key auth worked, `ANACONDA_AUTH_API_KEY` set in Claude Desktop config is NOT passed to `environments-mcp-server` subprocess.

**Workaround**: Use interactive login instead (quit Claude Desktop first due to KI-026 port conflict).

**Related**: [KI-026](#ki-026-cannot-run-anaconda-login-while-claude-desktop-with-anaconda-mcp-is-running-port-8000-conflict) — the port 8000 conflict that motivated API key auth as a workaround.

---

## Troubleshooting

### Accessing MCP server logs

**Claude Desktop**

Logs are written per MCP server under `~/Library/Logs/Claude/`:

```bash
open ~/Library/Logs/Claude/mcp-server-anaconda-mcp.log   # server stdout/stderr
open ~/Library/Logs/Claude/mcp.log                        # MCP protocol traffic
```

**Cursor**

Cursor does not write persistent MCP log files. Use the **Output** panel:
`View → Output`, then select **MCP** or **Cursor** from the dropdown.

For server-side logs when running HTTP transport, start the server manually
and observe its terminal output directly:

```bash
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
```

---

## Platform Issues

### PI-001: `anaconda-mcp` CLI Not Executable on Windows — Missing `.exe` Wrapper

**Status**: Open — [DESK-1344](https://anaconda.atlassian.net/browse/DESK-1344) (packaging bug — fix required by Anaconda MCP developers)
**Severity**: High (blocks all CLI usage on Windows without workaround)
**Platform**: Windows only

**Title**: `anaconda-mcp` command not recognized on Windows despite correct installation

**Steps to reproduce**:
1. Install `anaconda-mcp` via conda on Windows (Anaconda Prompt or PowerShell with `conda init powershell`)
2. Activate the environment: `conda activate anaconda-mcp-rc-pyXY`
3. Run: `anaconda-mcp --help`
4. Observe: `'anaconda-mcp' is not recognized as an internal or external command`
5. Run: `where anaconda-mcp`
6. Observe: script found at `...\Scripts\anaconda-mcp` (no extension)

**Root cause**: The conda package installs a Unix-style extensionless script into `Scripts\`. On Windows, `cmd.exe` and PowerShell only execute files with `.exe`, `.bat`, or `.cmd` extensions. The `.exe` wrapper that pip/conda normally generates from a `console_scripts` entry point was not created during the conda build.

**Expected**: `anaconda-mcp --help` works on Windows, consistent with macOS/Linux behavior. A `Scripts\anaconda-mcp.exe` wrapper should be present.

**Workaround**: Use `python -m anaconda_mcp <cmd>` as a drop-in replacement for all `anaconda-mcp` commands.

**Fix required**: Verify `console_scripts` entry point is correctly declared in `pyproject.toml` and that the conda recipe generates the `.exe` wrapper on Windows.

---

### PI-003: `anaconda-connector` Packages Fail to Download — `conda-anaconda-telemetry` Sends Oversized Headers to S3

**Status**: Root cause confirmed — workaround available; bug to be filed against `conda-anaconda-telemetry`
**Severity**: Critical (blocks environment creation without workaround)
**Platform**: Any OS — triggered by full Anaconda install (large base env), not by OS. Confirmed on Windows (full Anaconda). Not reproduced on Mac (trimmed ~130-package base). Would reproduce on Mac with full Anaconda too.
**Discovered**: Mar 2026, Windows testing with full Anaconda

**Root cause**: The `conda-anaconda-telemetry` plugin (present in the Anaconda base environment as `conda-anaconda-telemetry-0.1.2`) injects an `Anaconda-Telemetry-Packages` header into every conda HTTP request. This header contains the full package list of the base environment — on a full Anaconda installation this is hundreds of packages and several kilobytes of text.

The `anaconda-connector` packages are served via `conda.anaconda.org`, which issues a **302 redirect** to `binstar-cio-packages-prod.s3.amazonaws.com`. When conda follows that redirect it carries all its headers (including the large telemetry headers) to S3. **AWS S3 has a hard 8192-byte limit on request header sections.** The telemetry payload exceeds this limit and S3 responds with:

```xml
<Error>
  <Code>RequestHeaderSectionTooLarge</Code>
  <Message>Your request header section exceeds the maximum allowed size.</Message>
  <MaxSizeAllowed>8192</MaxSizeAllowed>
</Error>
```

Conda surfaces this as `HTTP 400 BAD REQUEST`. Packages from `repo.anaconda.com` (Cloudflare CDN) succeed because Cloudflare does not enforce the same strict limit. Only `anaconda-connector-*` packages are affected because they are the only ones whose channel redirects to S3.

**Evidence from `conda create -vvv` log**:
- `conda.anaconda.org` returns `302` for all three packages — token is valid ✓
- Conda follows redirect to `binstar-cio-packages-prod.s3.amazonaws.com` and sends multi-kilobyte `Anaconda-Telemetry-Packages` header
- S3 responds `RequestHeaderSectionTooLarge` (max 8192 bytes) → conda reports `HTTP 400`

**Workaround — disable conda telemetry before creating the environment**:
```bat
conda config --set anaconda_anon_usage false
conda create --name anaconda-mcp-rc-py310 -c datalayer -c anaconda-cloud/label/dev -c defaults -c conda-forge --channel "https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/" python=3.10 anaconda-mcp=1.0.0.rc.1 environments-mcp-server=1.0.0.rc.1
```

Re-enable after if desired:
```bat
conda config --set anaconda_anon_usage true
```

Or set for just the one command (no permanent config change):
```bat
set CONDA_ANACONDA_ANON_USAGE=false
conda create ...
```

**Trigger condition — base environment size**: The `Anaconda-Telemetry-Packages` header is built from the *base* environment's installed package list. The issue triggers when that list is large enough to push the total request header section over S3's 8192-byte limit.

| conda install type | Base env packages | Reproduces? |
|--------------------|-------------------|-------------|
| Full Anaconda | ~500+ | ✗ Yes — HTTP 400 |
| Trimmed / partial conda | ~130 (confirmed on Mac) | ✓ No — downloads succeed |
| Miniconda | ~30–50 | ✓ No — downloads succeed |

**This is not an OS issue.** Full Anaconda on Mac would reproduce the same failure. Miniconda on Windows would not. Run `conda list -n base | wc -l` before testing — if significantly above ~130, apply the workaround.

**Bug to file**: Against `conda-anaconda-telemetry` — it should not forward `Anaconda-Telemetry-*` headers when following redirects to non-Anaconda hosts (e.g. S3 presigned URLs). The fix should strip these headers before any cross-domain redirect.

**Impact**:
- Without workaround: environment creation fully blocked on systems with a large Anaconda base install
- With workaround: creation should succeed

**Ruled out**:
- Token validity — `conda.anaconda.org` returns `302` correctly; token is valid ✓
- Conda cache — same failure after `conda clean --all -y`
- SSL/TLS — not the cause

---

## PI-002: Claude Desktop on Windows — MCP Server Setup Requires Manual Config and Full Process Restart
- **Status**: Resolved (workaround documented) — see DESK-1363 for fix tracking
- **Severity**: High (blocks STDIO MCP setup without manual steps)
- **Platform**: Windows (MSIX / Microsoft Store install of Claude Desktop)
- **Original finding**: On organizational Windows 365 instances, Claude Desktop appeared unable to spawn local subprocess MCP servers. This was initially suspected to be an AppContainer/org policy restriction.
- **Actual root cause**: The issue is not org policy. It is caused by two Windows-specific bugs in the setup-config command flow, both present on any Windows MSIX install — managed or personal:

Wrong config path:
- setup-config writes to %APPDATA%\Roaming\Claude\
- but Claude Desktop (MSIX) reads from a virtualized path under %LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\.

Incomplete restart:
- Closing the Claude Desktop window leaves background processes alive.
- The new config is never read until all Claude processes are fully killed.

- **Workaround**: See [WINDOWS_CLAUDE_DESKTOP.md](./tests/e2e/setup/WINDOWS_CLAUDE_DESKTOP.md) for full step-by-step instructions.

### KI-016: `create_environment` Fails with `frozen_instance` Error When `environment_root_path` Is Provided
**Status**: Fixed locally — fix not yet committed or released
**Jira**: [DESK-1384](https://anaconda.atlassian.net/browse/DESK-1384)
**Bug introduced**: commit `b9184c8` ("feat: create environment with custom root", 2026-02-19) — added `environment_root_path` support with wrong implementation
**Severity**: High (blocks environment creation when `environment_root_path` is supplied)
**Component**: `environments_mcp_server`
**Affected versions**: 1.0.0.rc.1 and current `main`
**Discovered**: March 2026, Windows QA
**Regression test**: `tests/qa/http_tools/test_create_environment_root_path.py`

**Description**: Calling `create_environment` with a non-null `environment_root_path` raises a Pydantic validation error and the tool returns an unhandled exception. The LLM receives no meaningful error message.

**Error**:
```
1 validation error for ContextConfig
root_path
  Instance is frozen [type=frozen_instance, input_value=WindowsPath('C:/Users/.../miniconda3/envs'), input_type=WindowsPath]
```

**Root cause** — two bugs on the same line in `create_environment.py`:

1. **Wrong field name**: `ContextConfig` has no `root_path` field. The correct field is `root_prefix`.
2. **Frozen model mutation**: `ContextConfig` uses `model_config = ConfigDict(frozen=True)`, so direct attribute assignment always raises `frozen_instance`. The correct pattern is the `.merge()` method, which is already used correctly in the `else` branch.

**Buggy code** (`create_environment.py`):
```python
if environment_root_path is not None:
    conda_config.root_path = Path(environment_root_path)  # wrong field + frozen model
```

**Fix**:
```python
if environment_root_path is not None:
    conda_config = conda_config.merge(root_prefix=Path(environment_root_path))
```

**Actual call sequence observed in logs (2026-03-11)**:

This bug is a *secondary* failure — the LLM's self-recovery attempt after a prior silent failure. The full sequence:

1. `conda_list_environments` → returns environments, but **KI-002 is active**: the server's own env (`anaconda-mcp-rc-py310`) is labeled `"name": "base"`, and the real conda root (`miniconda3`) is labeled `"name": "miniconda3"`.

2. `conda_create_environment(environment_name="e2e-test", packages=["python=3.11"])` — **no `environment_root_path`** → silent `"There was an error while creating the environment."` (id=5). **This first failure is caused by KI-002/KI-003**: `get_distributions()` returns the server's own env as the first distribution (misclassified as "base"), so `root_prefix` is set to `miniconda3\envs\anaconda-mcp-rc-py310` (wrong). Conda tries to create the env under that path, fails, and the broad `except Exception` swallows the real error.

3. LLM self-recovers by retrying with an explicit `environment_root_path: "C:\\Users\\...\\miniconda3\\envs"` (id=6) → hits the frozen_instance bug (KI-016).

```
conda_list_environments → KI-002: wrong "base" label
  ↓
create_environment (no environment_root_path)
  → get_distributions() returns wrong prefix (KI-003)
  → conda fails under wrong root
  → broad except swallows real error
  → "There was an error while creating the environment."
  ↓
LLM retries with environment_root_path
  → frozen_instance bug (KI-016) ← THIS IS WHAT THE USER SEES
```

**Why `environment_root_path` is never passed on macOS**: On macOS, `get_distributions()` returns the correct conda root (KI-002 does not trigger, or the default distribution resolution works correctly), so the first create attempt succeeds and the LLM never reaches the retry with `environment_root_path`. The KI-016 code path is never hit.

**Affected tools**: `create_environment` only (when `environment_root_path` is provided).

**Related**: KI-002/KI-003 (root cause of the first silent failure that triggers the LLM retry), KI-014 (same `get_conda_config` area).

---

### PI-004: Claude Desktop Retries Indefinitely with Deleted Environment Path (`ENOENT`)
**Status**: Open — configuration/UX issue
**Severity**: Medium
**Platform**: Windows (Claude Desktop)
**Discovered**: 2026-03-11

**Description**: When the Python executable referenced in Claude Desktop's MCP config no longer exists (e.g. the conda environment was deleted or renamed), Claude Desktop reports `spawn ENOENT` but immediately retries with the same broken path in a tight loop, printing the error 3+ times in rapid succession before giving up.

**Observed in logs (2026-03-11 18:42)**:
```
spawn C:\Users\JuliaIliukhina\anaconda3\envs\anaconda-mcp-rc-py311\python.exe ENOENT
... (repeated 3 times)
Server disconnected.
```

**Context**: The `anaconda3\envs\anaconda-mcp-rc-py311` environment had been deleted (replaced by a `miniconda3`-based env), but the Claude Desktop config (`claude_desktop_config.json`) still pointed to the old path. Claude Desktop does not validate the path before spawning or surface a clear "file not found" message to the user.

**Impact**: MCP server is completely non-functional until the config is updated to point to the new environment path. The repeated retry loop provides no additional diagnostic value.

**Fix required**: Update `claude_desktop_config.json` to point to the correct Python executable. On Windows MSIX this requires writing to the virtualized config path (see PI-002 / WINDOWS_CLAUDE_DESKTOP.md).

**Workaround**: After deleting or renaming the conda environment used by the MCP server, update the config manually and do a full Claude Desktop restart (kill all processes — see PI-002).

---

### KI-014: `get_conda_config` Not Awaited in `remove_environment` — Causes AttributeError
**Status**: Open (Bug)
**Severity**: Medium
**Component**: `environments_mcp_server`
**Version**: 1.0.0.rc.3
**Discovered**: 2026-03-10

**Description**: In `remove_environment.py`, the async function `get_conda_config()` is called without `await`, causing:
```
AttributeError: 'coroutine' object has no attribute 'merge'
RuntimeWarning: coroutine 'get_conda_config' was never awaited
```

**Location**: `environments_mcp_server/tools/environments/remove_environment.py` line 72:
```python
conda_config = get_conda_config(environment_root_path)  # Missing await!
```

**Impact**: The `remove_environment` tool may fail or behave incorrectly when `environment_root_path` is provided.

**Fix**: Add `await`:
```python
conda_config = await get_conda_config(environment_root_path)
```

---

### KI-015: `logger.exception()` Causes Server Hang After ~15 Calls
**Status**: Open (Bug) — [DESK-1366](https://anaconda.atlassian.net/browse/DESK-1366)
**Severity**: Critical
**Component**: `environments_mcp_server`
**Version**: 1.0.0.rc.3
**Discovered**: 2026-03-10
**Transports Affected**: HTTP and STDIO (transport-independent)

**Description**: Repeated calls to `logger.exception()` in exception handlers cause the `environments_mcp_server` to stop processing new requests after approximately 15 calls. The server accepts HTTP connections but never dispatches requests to tool functions.

**Root Cause**: `logger.exception()` accumulates state that eventually blocks the MCP request dispatch layer.

**Problematic Code** (`install_packages.py:101-102`):
```python
except conda_exceptions.EnvironmentLocationNotFound as ex:
    logger.exception(ex)  # <-- CAUSES HANG AFTER ~15 CALLS
    return ServerToolResult(...)
```

**Why `remove_environment` passes but `install_packages` hangs**:
- `remove_environment` catches `CondaEnvironmentNotFoundError` → NO `logger.exception()`
- `install_packages` catches `EnvironmentLocationNotFound` → YES `logger.exception()`

**Evidence**:
- With `logger.exception()`: Hangs at iteration ~15
- Without `logger.exception()`: Passes all 20 iterations

**Fix**: Replace `logger.exception(ex)` with `logger.warning(f"...")` in exception handlers.

**Affected Files**:
- `install_packages.py` lines 102, 109, 127
- Possibly other tool files with same pattern

---

### KI-013: mcp-compose Delays All Responses by Exactly the Configured Timeout Value
**Status**: Confirmed — to be reported to mcp-compose maintainers
**Severity**: High
**Component**: `mcp-compose`
**Version**: mcp-compose 0.1.11 / mcp 1.26.0
**Observed**: 2026-03-09, macOS, Python 3.13, anaconda-mcp-dev environment

**Description**: After the "GET stream disconnected" message appears, every subsequent MCP tool call is delayed by exactly the `timeout` value configured in `mcp_compose.toml` — even simple, successful operations like `conda_list_environments` that should complete in <1 second.

**Confirmed behavior** (2026-03-09):
- With `timeout = 30`: all responses delayed by exactly ~30.01-30.03s
- With `timeout = 5`: all responses delayed by exactly ~5.01-5.03s

**Symptoms in test logs** (timeout=5):
```
[TIMING] tool=conda__conda_list_environments completed in 5.01s session_id=...
[TIMING] tool=conda__conda_list_environments completed in 5.02s session_id=...
[TIMING] tool=conda__conda_list_environments completed in 5.03s session_id=...
... (all exactly ~5s, matching timeout config)
```

**Server-side behavior**:
- `Processing request of type CallToolRequest` appears immediately
- HTTP 200 OK with `text/event-stream` content-type sent immediately
- But the SSE body (actual result) is delayed by exactly the configured timeout

**Trigger** — key log line before the slowdown begins:
```
mcp.client.streamable_http - INFO - GET stream disconnected, reconnecting in 1000ms...
```

**Root cause**: After the GET stream disconnects, `mcp-compose` waits for the full `timeout` duration before forwarding SSE responses from the downstream server. This is a bug in the proxy's SSE response handling — it should forward responses immediately, not wait for timeout.

**Relation to KI-011**: Different manifestation of the same underlying proxy state corruption:
- KI-011: Proxy hangs indefinitely (no response) — tool returns error quickly
- KI-013: Proxy delays response by exactly timeout value — tool returns success

**Trade-off with KI-011** (discovered 2026-03-10):

| timeout | KI-013 Delays | KI-011 Hangs | Test Results |
|---------|---------------|--------------|--------------|
| 5 | Yes (5s per call) | Fewer | 5 pass / 3 fail |
| 60 | No | More | 4 pass / 4 fail |

The KI-013 delays accidentally **prevent** KI-011 hangs by acting as a cooldown between calls, giving the connection pool time to recover. With `timeout=60`, calls happen rapidly and the pool corrupts faster.

**Impact**:
- Test suite takes 10+ minutes instead of <1 minute with timeout=30
- Any interactive use becomes unusable
- Reducing timeout trades speed for stability (fewer hangs)

**Workaround**:
- `timeout = 60`: Fast but more hangs (use for interactive work, restart when hang occurs)
- `timeout = 5`: Slow but fewer hangs (use for long test runs)

**To report**: File issue against `mcp-compose` — the root cause is connection pool management, not timeout handling

---

### KI-014: Anaconda Login Initiated on Every Startup Without User Request; Telemetry Silently Uninitialized When Skipped
**Status**: Open — to be filed
**Severity**: Medium
**Component**: `anaconda_mcp` — auth / telemetry initialization
**Observed**: 2026-03-11, Windows, Claude Desktop (stdio transport)

**Description**: On every server startup `anaconda_mcp` immediately launches an Anaconda login flow in the background, opening a browser authentication page without any user request. If the user ignores the browser window (e.g. is working with local conda environments and does not use Anaconda cloud), the auth poll times out after ~60 seconds and telemetry is left uninitialized for the entire session — silently, with no user-facing indication.

**Observed log sequence**:
```
2026-03-11 17:49:21 - anaconda_mcp.auth - INFO - Starting Anaconda login in background
2026-03-11 17:50:22 - anaconda_mcp.auth - INFO - Timed out waiting for login; telemetry not initialized
```

**Problems**:
1. **Uninvited browser window**: Browser opens on every startup regardless of whether the user is authenticated or intends to authenticate. Unexpected for users doing local, offline, or unauthenticated conda work.
2. **~60-second background wait**: Auth polling runs through the first tool call window, adding unnecessary background activity during a sensitive startup period.
3. **Silent telemetry failure**: After timeout, telemetry is uninitialized with no user-visible message — analytics and error-reporting are silently dropped for the whole session.
4. **Unauthenticated use case not handled**: Users with no Anaconda cloud account (or who simply skip login) get a browser popup + a timeout log on every restart.

**Expected behavior**:
- If a cached token exists and is valid: re-use it silently; do not open a browser.
- If no token exists: do not open a browser unprompted; either skip auth entirely or surface a non-blocking, opt-in prompt.
- Telemetry initialization should not depend on a 60-second interactive login wait; it should degrade gracefully and immediately when auth is unavailable.

**Impact**: Poor UX for unauthenticated users; browser window opened without consent; silent telemetry loss for every non-authenticated session.

**Workaround (authenticated users)**:
1. Fully close Claude Desktop
2. Kill leftover server processes — on Windows, closing Claude Desktop does **not** reliably terminate child processes; `environments_mcp_server` keeps running and holds port 4041:
   ```
   taskkill /F /IM python.exe /FI "WINDOWTITLE eq environments_mcp*"
   ```
   Or identify and kill the PID directly (visible in the previous `mcp_server.log` as `Process started (PID: XXXX)`).
3. Complete the Anaconda login in the browser (already open, or navigate to `anaconda.cloud` manually)
4. Reopen Claude Desktop — the cached token is picked up on startup, auth completes silently, telemetry initializes normally

**Confirmed (2026-03-11, Windows test)**:
- Step 1–4 above: auth fix **confirmed** — log opened with `Initializing telemetry` immediately; no browser window, no timeout
- However: port 4041 was still held by the previous `environments_mcp_server` (step 2 was skipped) → new session returned HTTP 404 on all requests after initial handshake → tool registration failed → **0 tools registered** → Claude Desktop showed anaconda-mcp as non-active with a warning
- This confirms that killing leftover processes (step 2) is required as part of the workaround; see also KI-012 (port 4041 occupied by stale process)

**Note for unauthenticated / non-auth testing**: No clean workaround exists. Closing the browser window or ignoring it always results in the 60-second timeout and uninitialized telemetry. The fix must come from the server side (graceful degradation when no credentials are present).

---

## Setup Quirks

### KI-017: `environments_mcp_server` Survives Claude Desktop Shutdown on Windows — Port 4041 Held by Stale Process on Restart
**Status**: Open — to be filed (mcp-compose + defensive fix in our code)
**Severity**: Medium
**Component**: `mcp-compose` (primary) / `anaconda_mcp` startup (secondary)
**Platform**: Windows (process orphaning is default OS behavior; Unix signal propagation makes this less likely on macOS/Linux)
**Observed**: 2026-03-11, Windows, Claude Desktop (stdio transport)

**Description**: When Claude Desktop is closed, the STDIO pipe to `python -m anaconda_mcp serve` breaks, but `environments_mcp_server` (a grandchild process) is not terminated. On Windows, processes orphan by default when their parent exits unless the parent explicitly cleans them up. `mcp-compose` does not do this. On next Claude Desktop startup, `mcp-compose` attempts to start a new `environments_mcp_server` on port 4041 — but the stale process from the previous session still holds the port.

**Observed failure sequence (2026-03-11)**:
```
# Previous session: environments_mcp_server PID 3580 running on port 4041
# Claude Desktop closed — PID 3580 survived
# Claude Desktop reopened:
Process started (PID: 11612)                        ← new process can't bind port 4041
POST http://localhost:4041/mcp → 200 OK             ← connects to stale PID 3580, gets session
POST http://localhost:4041/mcp → 404 Not Found      ← stale process rejects new requests
GET  http://localhost:4041/mcp → 404 Not Found
GET stream disconnected, reconnecting in 1000ms...
Streamable HTTP server conda failed during tool registration: unhandled errors in a TaskGroup
Total tools: 0                                       ← no tools registered
```
Claude Desktop showed anaconda-mcp as non-active with a warning.

**Process tree**:
```
Claude Desktop (Electron)
  └── Node.js [anaconda-mcp] wrapper          ← killed on Claude Desktop exit ✓
        └── python -m anaconda_mcp serve      ← killed when STDIO pipe closes ✓
              └── environments_mcp_server     ← NOT killed — orphaned on Windows ✗
```

**Root cause — two layers**:

1. **mcp-compose** (primary): Does not register an `atexit` handler or Windows Job Object to terminate child processes on shutdown. On Unix, process group signals propagate; on Windows they do not. This is a mcp-compose bug.

2. **Our code** (defensive gap): `mcp-compose` startup does not check whether port 4041 is already bound before connecting. It connects to whatever is on the port, gets a session from the stale process, and only fails later during tool registration. A pre-startup port check (detect stale process → kill it → retry) would prevent the cascade.

**Not a Claude Desktop issue**: Claude Desktop correctly closes the STDIO pipe on exit. It has no visibility into grandchild processes.

**macOS not affected**: Verified 2026-03-11 — port 4041 is empty after closing Claude Desktop on macOS. Unix process group signaling propagates termination to child processes correctly. KI-017 is Windows-only.

> **Note on macOS process check**: `pgrep -fa "anaconda_mcp"` and `pgrep -fa "environments_mcp"` produce false positives on macOS when the project directories are open in Cursor IDE (directory paths contain those strings). Use `lsof -ti:4041` as the reliable indicator, or filter specifically with `pgrep -fa "python.*-m anaconda_mcp"` / `pgrep -fa "python.*-m environments_mcp"`.

**Workaround**: Kill the stale process(es) manually before restarting Claude Desktop.

> **Note**: `taskkill /FI "WINDOWTITLE eq ..."` does **not** work for background Python processes — they have no window title and the filter matches nothing. Use command-line or port-based lookup instead.

> **Note**: Multiple stale processes can accumulate across sessions. `netstat` may show **two** listeners on port 4041 — one bound to `0.0.0.0:4041` and one to `127.0.0.1:4041`. Windows allows this when bindings differ by interface. `mcp-compose` connects to `127.0.0.1:4041` and hits whichever process responds first, making failures unpredictable. Kill **all** PIDs shown by `findstr :4041`.
>
> Observed (2026-03-11):
> ```
> TCP    0.0.0.0:4041    0.0.0.0:0    LISTENING    9664   ← stale from earlier session
> TCP    127.0.0.1:4041  0.0.0.0:0    LISTENING    11612  ← stale from previous session
> ```

**Option 1 — by port** (most precise — kills exactly what holds port 4041):
```cmd
netstat -ano | findstr :4041
taskkill /F /PID <first PID>
taskkill /F /PID <second PID if present>
```

**Option 2 — by command line (PowerShell, Windows 11)**:
> `wmic` is removed in Windows 11 22H2+; use `Get-CimInstance` instead.
```powershell
Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like "*environments_mcp*"} | Select-Object ProcessId, CommandLine
taskkill /F /PID <PID from above>
```

**Option 3 — PowerShell one-liner** (find and kill in one step):
```powershell
Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like "*environments_mcp*"} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

**Relation to KI-011**: Fixing KI-017 (killing stale processes) prevents the "0 tools registered" failure but does **not** prevent the first-call hang (KI-011 pattern). The rapid init/shutdown cycles that trigger KI-011 are inherent to Claude Desktop's startup protocol negotiation and occur regardless of process state.

**To file**:
- Against `mcp-compose`: add Windows-safe child process cleanup on STDIO EOF / process exit
- Against `anaconda_mcp`: add port 4041 availability check at startup; kill stale process if found

---

### SQ-001: Claude Desktop Capability Setting
**Description**: Users must enable "Code execution and file creation" in Claude Desktop settings.
**Location**: Settings > Capabilities > Code execution and file creation > Cloud code execution
**Impact**: MCP tools don't appear without this setting.
**Documentation**: Add to setup instructions.

### SQ-002: Permission Prompts
**Description**: Every conda operation run for the first time requires granting permission in Claude Desktop.
**Impact**: First-time user experience has multiple prompts.
**Expected**: This is standard Claude Desktop behavior for MCP tools.

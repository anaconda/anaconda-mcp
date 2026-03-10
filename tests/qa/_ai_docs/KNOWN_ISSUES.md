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
**Status**: Open (Bug) — [DESK-1342](https://anaconda.atlassian.net/browse/DESK-1342)
**Severity**: High
**Version**: 1.0.0rc1
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

### KI-005: Channel Credentials Not Picked Up
**Status**: Open
**Severity**: Medium
**Bug**: [DESK-1358](https://anaconda.atlassian.net/browse/DESK-1358)
**Description**: When a private Anaconda channel is specified (e.g. `repo.anaconda.cloud` or an org-scoped channel like `anaconda-internal/msys2`), conda resolves the channel name using its default base URL (`https://conda.anaconda.org/<channel>`). This address does not exist for private channels, resulting in HTTP 404. The request never reaches `https://repo.anaconda.cloud`, so credentials are never checked. The failure is identical for authenticated and unauthenticated users.
**Impact**:
- Cannot install packages from private or org-scoped channels via MCP tools
- AUTH-001a test fully blocked — cannot verify anonymous users are denied private channel access
- AUTH-002 step 3a unconfirmed — unknown whether authenticated default installs resolve from `repo.anaconda.cloud`
- Misleading error: users see "channel not accessible" (404) instead of an auth error
**Root cause (hypothesis)**: conda requires either a full URL override (e.g. `https://repo.anaconda.cloud/pkgs/main`) or a token/credential config that maps the channel name to the correct endpoint. The MCP server is not injecting the necessary channel URL mapping or token when calling conda with a private channel override.
**Workaround**: None — private channel access via MCP tools is not functional until resolved.
**Blocks**: AUTH-001a (config-independent)

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

### KI-011: mcp-compose Proxy Hangs and Corrupts Session on Tool Error
**Status**: Partially Fixed — [mcp-compose #27](https://github.com/datalayer/mcp-compose/issues/27), [PR #28](https://github.com/datalayer/mcp-compose/pull/28) merged in 0.1.11
**Internal Ticket**: [DESK-1355](https://anaconda.atlassian.net/browse/DESK-1355)
**Component**: `mcp-compose`
**Severity**: High (process-wide corruption; server restart required to recover)
**Version**: mcp-compose 0.1.10 (original), 0.1.11 (partial fix)
**Regression tests**: `tests/qa/http_tools/test_guard_proxy_error_hang.py`, `tests/qa/stdio_tools/test_guard_proxy_error_hang_stdio.py`

**Description**: When a tool returns quickly (validation errors, etc.), `mcp-compose`'s proxy hangs and corrupts the httpx connection pool. All subsequent calls block indefinitely. Only restarting `mcp-compose` recovers.

**Root cause**: `mcp-compose` uses deprecated `streamablehttp_client` which has a hidden 5-minute SSE read timeout. When FastMCP serves results inline (200 OK) instead of via SSE, the SSE cleanup hangs waiting for the timeout, leaking the connection pool slot.

**Fix status** (as of 2026-03-10):
- PR #28 merged into mcp-compose 0.1.11 on 2026-03-07
- Fix replaces deprecated `streamablehttp_client` with `streamable_http_client` + explicit `httpx.AsyncClient`
- **Partial improvement**: Hang threshold improved from ~4 iterations to ~16 iterations
- **Still failing**: After ~16 rapid sequential error-triggering calls, the hang still occurs

**Test results** (mcp-compose 0.1.11, MCP SDK 1.26.0, 2026-03-10):

| Test | Before Fix | After Fix (0.1.11) |
|------|------------|-------------------|
| HANG-001 (remove_environment × 20) | Hangs at iteration 4 | ✅ **Passed** (all 20) |
| HANG-002 (install_packages × 20) | Hangs at iteration 4 | ❌ Hangs at iteration ~9-16 |
| HANG-003 (mixed error + health × 40) | Hangs early | ❌ Hangs (pool corrupted by HANG-002) |

**Note**: When HANG-002 is run in isolation (fresh server, no prior tests), it reaches iteration 16 before hanging. When run after HANG-001, pool state accumulates and it hangs earlier (~iteration 9).

**Remaining issue**: The MCP SDK's connection pool still accumulates state under rapid sequential calls. The "GET stream disconnected, reconnecting..." log message appears before the hang, indicating an SSE reconnection issue.

**Workaround**: Restart `mcp-compose` when hangs occur:
```bash
pkill -9 -f "anaconda-mcp"
pkill -9 -f "environments_mcp"
lsof -ti:8888 | xargs kill -9 2>/dev/null
lsof -ti:4041 | xargs kill -9 2>/dev/null
sleep 2
./tests/qa/_ai_docs/scripts/start-http-server.sh 8888
```

**Investigation**: [hang_issue/](./hang_issue/)

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

### PI-002: Claude Desktop on Windows 365 (Managed Corporate Device) Likely Blocked by Org Policy

**Status**: Under Investigation
**Severity**: High (**may** block all Windows STDIO testing with Claude Desktop)
**Platform**: Windows 365 / managed corporate Windows devices

**Description**: On organizational Windows 365 (cloud PC) instances, Claude Desktop (Windows Store version) may be unable to spawn local subprocess MCP servers. This does not appear to be an `anaconda-mcp` packaging issue — the likely cause is a platform-level constraint from corporate management policies, but this needs further confirmation.

**Why this blocks STDIO MCP servers**:
- The Windows Store Claude Desktop runs inside an **AppContainer sandbox**. On org-managed devices, additional **AppLocker / WDAC policies** may further restrict subprocess spawning from user directories (e.g. `C:\Users\...\miniconda3\...`).
- **Group Policy** on managed Windows 365 instances typically restricts app installation to the Store or an approved software list — installing the direct-download `.exe` Claude Desktop may be blocked outright.
- A **`vmcompute.dll` load failure** was observed in CoworkVMService logs — this may indicate Hyper-V/container features are restricted, which would be consistent with a locked-down Windows 365 instance, but the exact cause needs to be confirmed with IT support or reproduced on another instance.

**Observed symptoms**:
```
# CoworkVMService log
failed to load vmcompute.dll   ← possible indicator of org policy; needs IT confirmation
```
MCP servers failed to start when configured in Claude Desktop; subprocess spawn appeared to be silently blocked. **Root cause not yet definitively confirmed** — needs verification with IT support or testing on a second Windows 365 instance.

**Impact**:
- Windows STDIO testing with Claude Desktop is likely infeasible on org-managed Windows 365 without IT involvement.
- All QA 3 Windows + Claude Desktop test configurations are blocked.

**Practical alternatives**:

| Option | Feasibility |
|--------|-------------|
| Install direct-download Claude Desktop `.exe` | Likely blocked by IT Group Policy |
| Use **Cursor** or **VS Code** with HTTP transport | Possible — IDE installs are more commonly allowed |
| Request IT to allowlist direct-download Claude Desktop | Depends on org policy |
| Use a local (non-managed) Windows machine | Outside tester's control |

**Current plan**: Attempt Windows testing using **Cursor** or **VS Code** (with AI chat) + HTTP transport. STDIO-only configs remain blocked until further notice.

**Note**: This is a tester environment constraint, not an `anaconda-mcp` bug.

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

## Setup Quirks

### SQ-001: Claude Desktop Capability Setting
**Description**: Users must enable "Code execution and file creation" in Claude Desktop settings.
**Location**: Settings > Capabilities > Code execution and file creation > Cloud code execution
**Impact**: MCP tools don't appear without this setting.
**Documentation**: Add to setup instructions.

### SQ-002: Permission Prompts
**Description**: Every conda operation run for the first time requires granting permission in Claude Desktop.
**Impact**: First-time user experience has multiple prompts.
**Expected**: This is standard Claude Desktop behavior for MCP tools.

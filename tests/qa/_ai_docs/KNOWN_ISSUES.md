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

### KI-010: False "Environment Not Found" When Installing Nonexistent Package
**Status**: Open (Bug)
**Severity**: Medium
**Version**: 1.0.0rc1
**Regression test**: `tests/qa/api_tools/test_guard_install_nonexistent_pkg.py`

**Description**: `conda_install_packages(environment="<name>", packages=["nonexistent-package-xyz123"])` returns `is_error=true` with `"The environment was not found. Make sure you are providing the correct name or prefix"` even though the environment exists. The misleading error causes the LLM to list environments and retry by prefix, producing extra tool calls.

**Root cause**: `anaconda_connector_conda` creates a `Context(search_path=())` for each call. With an empty search path conda does not populate `envs_dirs`, so `context.target_prefix` raises `EnvironmentLocationNotFound` before the solver is invoked. `install_packages.py:93` catches this and returns the wrong error message.

**Expected behavior**: Returns `is_error=true` with a package-resolution error (e.g. `"Could not resolve the packages"`). Single tool call, no retry.

**Observed on**:

| Client | Transport | Python | Result |
|--------|-----------|--------|--------|
| Cursor | Streamable HTTP | 3.13 | Incorrect error message |
| Cursor | STDIO | 3.10, 3.13 | Incorrect error message |
| Claude Desktop | STDIO | 3.10 | Incorrect error message |

**Note on hanging**: In one isolated run (Cursor / Streamable HTTP / Python 3.13) the session hung after the retry-by-prefix call. The same configuration was retested multiple times and the hang did not recur. Root cause not identified; treated as a transient issue for now.

---

## Open Issues / Quirks

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
**Status**: Open (Bug)
**Severity**: High
**Version**: 1.0.0rc1
**Regression test**: `tests/qa/api_tools/test_env_name_resolution.py::TestEnvironmentNameResolution::test_ki003_remove_environment_by_name`
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

### KI-004: Extra Fields in Settings Causes Crash
**Status**: Fixed (PR #20)
**Version Fixed**: Post-0.1.2
**Description**: `pydantic_core.ValidationError: Extra inputs are not permitted` when user has extra env vars like `openai_api_key`.
**Root Cause**: Pydantic settings was set to forbid extra fields.
**Test Case**:
- [ ] Set random environment variables and run anaconda-mcp
- [ ] Verify no crash on extra env vars

---

### KI-005: Channel Credentials Not Picked Up
**Status**: Open
**Severity**: High
**Description**: `repo.anaconda.cloud` channel requires credentials that MCP tool isn't picking up.
**Impact**: Cannot create environments or install packages from licensed channels.
**Test Case**:
- [ ] Test with authenticated user (anaconda login)
- [ ] Test with licensed channel access
- [ ] Verify error messages are clear

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
**Status**: Open (Bug)
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

### KI-011: Cursor Chat Hangs When an MCP Tool Returns an Error

**Status**: Open (Cursor-side bug — not an Anaconda MCP issue)
**Severity**: Medium (workaround: start a new chat session)
**Observed**: Twice during internal testing (Feb–Mar 2026), two different tools (one-time occasional cases, non-reproducible with same configuration by next attempts)

**Description**: After an MCP tool call returns an error response, the Cursor chat panel stops responding — no further output, no error displayed, the session simply hangs. The same prompt in a fresh session works normally.

**Root cause**: This is a **Cursor UI state machine bug**. Cursor's frontend gets stuck in a *"waiting for tool response"* state and does not properly process or surface error responses returned by the MCP server. The MCP server itself has already returned a valid (error) response; Cursor never acknowledges it.

This is a well-documented, recurring issue across multiple unrelated MCP servers and Cursor versions.

**Observed pattern**:
1. Tool is called → MCP server returns an error
2. Cursor chat shows "Generating…" or "Running…" indefinitely
3. No error is surfaced in the chat
4. Starting a new chat session with the same prompt and config works fine

**Workaround**: Start a new chat session. If the hang persists, reload the Cursor window (`Cmd+Shift+P` → *Reload Window*) or temporarily disable and re-enable the MCP server in *Cursor Settings → Tools & MCP*.

**How to check MCP logs during a hang**: Bottom Pane → Output → select **MCP** from the dropdown.

**Cursor forum references**:
- [Cursor not handling long-running MCP tool responses](https://forum.cursor.com/t/cursor-not-handling-long-running-mcp-tool-responses/124718) — Cursor engineer confirmed the bug; a 30 s timeout was removed as a partial fix
- [Chat frequently stuck / not responding](https://forum.cursor.com/t/chat-frequently-stuck-not-responding/148975)
- [Cursor freezes/crashes when attempting to use an MCP server](https://forum.cursor.com/t/cursor-freezes-crashes-when-attempting-to-use-an-mcp-server/152332)
- [Cursor doesn't cancel long-running MCP tool](https://forum.cursor.com/t/cursor-doesn-t-cancel-long-running-mcp-tool/134079) — Cancel button does not send MCP cancellation; tool keeps running on the server
- [IDE hangs after automatic MCP browser test](https://forum.cursor.com/t/ide-hangs-after-automatic-mcp-browser-test/148923)

**Note on KI-010**: The isolated hang observed under KI-010 (*Note on hanging*) is consistent with this Cursor-side bug.

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


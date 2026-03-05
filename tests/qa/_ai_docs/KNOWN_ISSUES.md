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

### KI-003: Package Install Requires Path Instead of Name
**Status**: Open
**Severity**: Medium
**Description**: MCP could not find specific environment by name. Had to search by path.
**Reproduction**: Try to install package specifying environment by name only.
**Test Case**:
- [ ] Install package using environment name
- [ ] Install package using environment path
- [ ] Compare behavior

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

---

## Testing Recommendations

### High Priority Tests (Based on Known Issues)

1. **Environment Deletion Verification**
   - Delete environment
   - Verify with `conda env list` that it's actually gone
   - Test when environment is activated

2. **Environment Name Resolution**
   - Create environment with specific name
   - List environments and verify name matches
   - Install packages by environment name (not path)

3. **Authentication Flow**
   - Test with `anaconda login` completed
   - Test without authentication
   - Test with licensed channel access

4. **Extra Environment Variables**
   - Set various env vars (OPENAI_API_KEY, etc.)
   - Verify anaconda-mcp starts without error

### Regression Test Checklist

After each release, verify these fixed issues don't regress:

- [ ] KI-001: Environment deletion actually removes environment
- [ ] KI-004: Extra env vars don't cause crash

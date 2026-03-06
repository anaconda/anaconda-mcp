# Feature to Test Coverage Mapping


## Test Files

| File | Platform | Flows |
|------|----------|-------|
| [TESTS_E2E.md](./TESTS_E2E.md) | macOS, Windows | CORE-001, GUARD-001, AUTH-001, AUTH-002, REGRESS-001, REGRESS-002 |
| [TESTS_CLI.md](./TESTS_CLI.md) | All platforms | CLI-001 to CLI-004 |
| [TESTS_CONFIG.md](./TESTS_CONFIG.md) | All platforms | ENV-001 to ENV-004, CFG-001 to CFG-003, PATH-001 to PATH-002 |
| [TESTS_API_TOOLS.md](./TESTS_API_TOOLS.md) | Win365 first, then CI | TOOL-001 to TOOL-006, ERR-001 to ERR-005 |

---

## Feature Coverage Table

| Feature Group | Feature | User Actions | Covered By |
|---------------|---------|--------------|------------|
| **Environment Management** | List Environments | AI: "List my conda environments" | CORE-001, TOOL-001 |
| | List Environment Packages | AI: "What packages are in env X?" | CORE-001, TOOL-005 |
| | Create Environment | AI: "Create env with Python 3.11" | CORE-001, TOOL-002, ERR-001 |
| | Remove Environment | AI: "Delete environment X" | CORE-001, GUARD-001, TOOL-006, ERR-002, REGRESS-002 |
| | Install Packages | AI: "Install numpy in env X" | CORE-001, GUARD-001, TOOL-003, ERR-003 |
| | Remove Packages | AI: "Remove pandas from env X" | CORE-001, TOOL-004 |
| **Server Management** | Start Server | `anaconda-mcp serve --port 8888` | CLI-002 |
| | Discover Servers | `anaconda-mcp discover` | CLI-001 |
| | Compose Servers | `anaconda-mcp compose` | CLI-001 |
| | Verbose Logging | `anaconda-mcp -v serve` | CLI-001 |
| **Client Setup (Claude Desktop / Cursor / Claude Code)** | Setup STDIO | `claude-desktop setup-config` | CLI-003 |
| | Setup HTTP | `setup-config --transport streamable-http` | CLI-003 |
| | Force Overwrite | `setup-config --force` | CLI-003 |
| | Skip Backup | `setup-config --no-backup` | CLI-002 |
| | Remove Config | `claude-desktop remove-config` | CLI-003 |
| | Show Config | `claude-desktop show` | CLI-003 |
| | Show Server Config | `claude-desktop show --name` | CLI-002 |
| | JSON Output | `claude-desktop show --json` | CLI-003 |
| | Get Config Path | `claude-desktop path` | PATH-001 |
| **Authentication** | Auto Login | Browser opens on serve | AUTH-002 |
| | Manual Login | `anaconda login` | AUTH-002 |
| | Anonymous Mode | No login, public channels | AUTH-001 |
| | Token Management | System keyring | AUTH-002 |
| **Configuration** | Log Level | `ANACONDA_MCP_LOG_LEVEL` | ENV-001 |
| | Disable Telemetry | `ANACONDA_MCP_SEND_METRICS` | ENV-002 |
| | Set Environment | `ANACONDA_MCP_ENVIRONMENT` | ENV-004 |
| | Python Executable | `ANACONDA_MCP_PYTHON_EXECUTABLE` | ENV-003 |
| | Custom Config | `--config custom.toml` | CFG-001, CLI-002 |
| | CLI Precedence | CLI flags override config | CFG-002 |
| | Startup Delay | `--delay 5` | CFG-003, CLI-002 |
| | Port Override | `--port 8888` | CFG-002, CLI-002 |
| **Transport** | STDIO | Default for Claude Desktop | CORE-001 |
| | HTTP | `--transport streamable-http` | CORE-001, CLI-002 |
| **Guardrails** | Channel Ordering | Respects `.condarc`, no pip fallback | GUARD-001 |
| | Missing Package | Hard fail, no pip fallback | GUARD-001, ERR-003 |
| | Delete Confirmation | Requires confirmation | GUARD-001 |

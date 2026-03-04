# Feature to Test Coverage Mapping

## Coverage Summary

| Feature Group | Features | Coverage |
|---------------|----------|----------|
| Environment Management | 6 | 100% |
| Server Management | 4 | 100% |
| Claude Desktop | 9 | 100% |
| Authentication | 4 | 100% |
| Configuration | 8 | 100% |
| Transport | 2 | 100% |
| Guardrails | 3 | 100% |
| **TOTAL** | **35** | **100%** |

---

## Test Files

| File | Platform | Flows |
|------|----------|-------|
| [TESTS_E2E_CLAUDE.md](./TESTS_E2E_CLAUDE.md) | macOS only | CORE-001, CORE-002, GUARD-001, AUTH-002, REGRESS-001 |
| [TESTS_CLI.md](./TESTS_CLI.md) | All platforms | CLI-001 to CLI-005 |
| [TESTS_CONFIG.md](./TESTS_CONFIG.md) | All platforms | ENV-001 to ENV-004, CFG-001 to CFG-003, PATH-001 to PATH-002 |
| [TESTS_API_TOOLS.md](./TESTS_API_TOOLS.md) | Win365 first, then CI | TOOL-001 to TOOL-005, ERR-001 to ERR-003 |

---

## Feature Coverage Table

| Feature Group | Feature | User Actions | Covered By |
|---------------|---------|--------------|------------|
| **Environment Management** | List Environments | AI: "List my conda environments" | CORE-001 |
| | List Environment Packages | AI: "What packages are in env X?" | CORE-001 |
| | Create Environment | AI: "Create env with Python 3.11" | CORE-001 |
| | Remove Environment | AI: "Delete environment X" | CORE-001, GUARD-001 |
| | Install Packages | AI: "Install numpy in env X" | CORE-001, GUARD-001 |
| | Remove Packages | AI: "Remove pandas from env X" | CORE-001 |
| **Server Management** | Start Server | `anaconda-mcp serve --port 8888` | CORE-002, CLI-002 |
| | Discover Servers | `anaconda-mcp discover` | CLI-001 |
| | Compose Servers | `anaconda-mcp compose` | CLI-001 |
| | Verbose Logging | `anaconda-mcp -v serve` | CLI-001 |
| **Claude Desktop** | Setup STDIO | `claude-desktop setup-config` | CORE-001, CLI-003 |
| | Setup HTTP | `setup-config --transport streamable-http` | CORE-002, CLI-003 |
| | Force Overwrite | `setup-config --force` | CLI-003 |
| | Skip Backup | `setup-config --no-backup` | CLI-002 |
| | Remove Config | `claude-desktop remove-config` | CLI-003 |
| | Show Config | `claude-desktop show` | CLI-003 |
| | Show Server Config | `claude-desktop show --name` | CLI-002 |
| | JSON Output | `claude-desktop show --json` | CLI-003 |
| | Get Config Path | `claude-desktop path` | PATH-001 |
| **Authentication** | Auto Login | Browser opens on serve | AUTH-001 |
| | Manual Login | `anaconda login` | AUTH-001 |
| | Anonymous Mode | No login, public channels | AUTH-002 |
| | Token Management | System keyring | AUTH-001 |
| **Configuration** | Log Level | `ANACONDA_MCP_LOG_LEVEL` | ENV-001 |
| | Disable Telemetry | `ANACONDA_MCP_SEND_METRICS` | ENV-002 |
| | Set Environment | `ANACONDA_MCP_ENVIRONMENT` | ENV-004 |
| | Python Executable | `ANACONDA_MCP_PYTHON_EXECUTABLE` | ENV-003 |
| | Custom Config | `--config custom.toml` | CFG-001, CLI-002 |
| | CLI Precedence | CLI flags override config | CFG-002 |
| | Startup Delay | `--delay 5` | CFG-003, CLI-002 |
| | Port Override | `--port 8888` | CFG-002, CORE-002 |
| **Transport** | STDIO | Default for Claude Desktop | CORE-001 |
| | HTTP | `--transport streamable-http` | CORE-002 |
| **Guardrails** | Channel Ordering | Respects `.condarc` | GUARD-001 |
| | Missing Package | Hard fail, no pip fallback | GUARD-001 |
| | Delete Confirmation | Requires confirmation | GUARD-001 |

---

## Flow Summary by File

### TESTS_E2E_CLAUDE.md (macOS only)

| Flow ID | Name | Features |
|---------|------|----------|
| CORE-001 | Full Setup & Tools | 7 features |
| CORE-002 | HTTP Transport | 3 features |
| GUARD-001 | Guardrails | 3 features |
| AUTH-002 | Anonymous Mode | 1 feature |
| REGRESS-001 | Known Issues | 4 features |

### TESTS_CLI.md (All platforms)

| Flow ID | Name | Features |
|---------|------|----------|
| CLI-001 | Server Discovery | 3 features |
| CLI-002 | Advanced Options | 4 features |
| CLI-003 | Config Management | 5 features |
| CLI-004 | Regression CLI | 1 feature |
| CLI-005 | Negative Scenarios | Error handling |

### TESTS_CONFIG.md (All platforms)

| Test ID | Name | Features |
|---------|------|----------|
| ENV-001 to 004 | Environment Variables | 4 features |
| CFG-001 to 003 | Config File Tests | 3 features |
| PATH-001 to 002 | OS Path Tests | 2 features |

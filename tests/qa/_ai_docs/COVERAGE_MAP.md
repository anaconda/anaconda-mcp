# Feature to Test Coverage Mapping

## Test Files

| File | Platform | RC1 | RC2 |
|------|----------|:---:|:---:|
| [tests/](./tests/) | macOS, Windows | + | + |
| [TESTS_CLI.md](./TESTS_CLI.md) | All platforms | + | + |
| [TESTS_CONFIG.md](./TESTS_CONFIG.md) | All platforms | + | + |
| [TESTS_API_TOOLS.md](./TESTS_API_TOOLS.md) | Win365 first, then CI | + | + |

---

## Feature Coverage Table

| Feature Group | Feature | Covered By | RC1 | RC2 |
|---------------|---------|------------|:---:|:---:|
| **Environment Management** | List Environments | CORE-001, TOOL-001 | + | + |
| | List Environment Packages | CORE-001, TOOL-005 | + | + |
| | Create Environment | CORE-001, TOOL-002, ERR-001 | + | + |
| | Remove Environment | CORE-001, GUARD-001, TOOL-006, REGRESS-002 | + | + |
| | Install Packages | CORE-001, GUARD-001, TOOL-003, ERR-003 | + | + |
| | Remove Packages | CORE-001, TOOL-004 | + | + |
| | Override Channels | CHAN-001 | | + |
| **Server Management** | Start Server | CLI-002 | + | + |
| | Discover Servers | CLI-001 | + | + |
| | Compose Servers | CLI-001 | + | + |
| | Verbose Logging | CLI-001 | + | + |
| **Client Setup** | Setup STDIO | CLI-003 | + | + |
| | Setup HTTP | CLI-003 | + | + |
| | Force Overwrite | CLI-003 | + | + |
| | Skip Backup | CLI-002 | + | + |
| | Remove Config | CLI-003 | + | + |
| | Show Config | CLI-003 | + | + |
| | Get Config Path | PATH-001 | + | + |
| | Installation Disclaimer | SETUP-001 | | + |
| **Authentication** | Auto Login | AUTH-002 | + | + |
| | Manual Login | AUTH-002 | + | + |
| | Anonymous Mode | AUTH-001 | + | + |
| | Private Channel Denial | AUTH-001a | | + |
| | Token Management | AUTH-002 | + | + |
| **Configuration** | Log Level | ENV-001 | + | + |
| | Disable Telemetry | ENV-002 | + | + |
| | Set Environment | ENV-004 | + | + |
| | Python Executable | ENV-003 | + | + |
| | Custom Config | CFG-001, CLI-002 | + | + |
| | CLI Precedence | CFG-002 | + | + |
| | Startup Delay | CFG-003, CLI-002 | + | + |
| | Port Override | CFG-002, CLI-002 | + | + |
| | Allow Override Channels | CHAN-001 | | + |
| **Transport** | STDIO | CORE-001 | + | + |
| | HTTP | CORE-001, CLI-002 | + | + |
| **Guardrails** | Channel Ordering | GUARD-001 | + | + |
| | Missing Package | GUARD-001, ERR-003 | + | + |
| | Delete Confirmation | GUARD-001 | + | + |

**Legend**: `+` = covered in release

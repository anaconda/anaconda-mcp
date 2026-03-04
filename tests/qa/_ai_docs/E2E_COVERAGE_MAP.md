# E2E Flow to Feature Coverage Mapping

## Coverage Summary

| Feature Group | Features | Coverage |
|---------------|----------|----------|
| Environment Management | 5 | 100% |
| Server Management | 4 | 100% |
| Claude Desktop | 9 | 100% |
| Authentication | 4 | 100% |
| Configuration | 8 | 100% |
| Transport | 2 | 100% |
| Guardrails | 3 | 100% |
| **TOTAL** | **35** | **100%** |

---

## Feature Coverage Table

| Feature Group | Feature | User Actions | Covered By |
|---------------|---------|--------------|------------|
| **Environment Management** | List Environments | AI: "List my conda environments"<br>API: `tools/call conda_list_environments` | CORE-001 |
| | Create Environment | AI: "Create env with Python 3.11"<br>API: `tools/call conda_create_environment` | CORE-001 |
| | Delete Environment | AI: "Delete environment X"<br>API: `tools/call conda_delete_environment` | CORE-001, GUARD-001 |
| | Install Packages | AI: "Install numpy in env X"<br>API: `tools/call conda_install_packages` | CORE-001, GUARD-001 |
| | Remove Packages | AI: "Remove pandas from env X"<br>API: `tools/call conda_remove_packages` | CORE-001 |
| **Server Management** | Start Server | `anaconda-mcp serve`<br>`anaconda-mcp serve --port 8888` | CORE-002 |
| | Discover Servers | `anaconda-mcp discover`<br>`anaconda-mcp discover --output-format json` | CLI-001 |
| | Compose Servers | `anaconda-mcp compose`<br>`anaconda-mcp compose --include server1` | CLI-001 |
| | Verbose Logging | `anaconda-mcp -v serve` | CLI-001 |
| **Claude Desktop Integration** | Setup STDIO | `anaconda-mcp claude-desktop setup-config` | CORE-001 |
| | Setup HTTP | `setup-config --transport streamable-http` | CORE-002 |
| | Force Overwrite | `setup-config --force` | CORE-003 |
| | Skip Backup | `setup-config --no-backup` | CLI-002 |
| | Remove Config | `anaconda-mcp claude-desktop remove-config` | CORE-003 |
| | Show Config | `anaconda-mcp claude-desktop show` | CORE-003 |
| | Show Server Config | `claude-desktop show --name anaconda-mcp` | CLI-002 |
| | JSON Output | `claude-desktop show --json` | CORE-003 |
| | Get Config Path | `anaconda-mcp claude-desktop path` | CORE-001 |
| **Authentication** | Auto Login | Browser opens on serve | AUTH-001 |
| | Manual Login | `anaconda login` before serve | AUTH-001 |
| | Anonymous Mode | No login, public channels only | AUTH-002 |
| | Token Management | Stored in system keyring | AUTH-001 |
| **Configuration** | Log Level | `ANACONDA_MCP_LOG_LEVEL=DEBUG` | CONFIG_TESTING_GUIDE |
| | Disable Telemetry | `ANACONDA_MCP_SEND_METRICS=false` | CONFIG_TESTING_GUIDE |
| | Set Environment | `ANACONDA_MCP_ENVIRONMENT=staging` | CONFIG_TESTING_GUIDE |
| | Python Executable | `ANACONDA_MCP_PYTHON_EXECUTABLE` | CONFIG_TESTING_GUIDE |
| | Config File | Edit `mcp_compose.toml.template` | CLI-002 |
| | Custom Config | `--config custom.toml` | CLI-002 |
| | Startup Delay | `anaconda-mcp serve --delay 5` | CLI-002 |
| | Port Override | `anaconda-mcp serve --port 8888` | CORE-002 |
| **Transport Modes** | STDIO Transport | Default for Claude Desktop | CORE-001 |
| | HTTP Transport | `--transport streamable-http` | CORE-002 |
| **Guardrails** | Channel Ordering | Respects `.condarc` channel priority | GUARD-001 |
| | Missing Package | Hard fail if package not found | GUARD-001 |
| | Delete Confirmation | Requires confirmation for delete | GUARD-001 |

---

## E2E Flow Summary

| Flow ID | Flow Name | Features Covered | Priority |
|---------|-----------|------------------|----------|
| CORE-001 | Full Setup & Tools | STDIO setup, path, list, create, install, remove, delete | P0 |
| CORE-002 | HTTP Transport | Server start, HTTP setup, port override, HTTP transport | P0 |
| CORE-003 | Config Management | Show, force, JSON output, remove config | P0 |
| GUARD-001 | Guardrails | Channel ordering, missing package, delete confirmation | P0 |
| REGRESS-001 | Known Issues | KI-001 through KI-006 verification | P0 |
| CLI-001 | Server Discovery | Discover, compose, verbose logging | P1 |
| CLI-002 | Advanced Options | Custom config, delay, no-backup, show server | P1 |
| AUTH-001 | Authentication | Manual login, auto login, token management | P1 |
| AUTH-002 | Anonymous Mode | Anonymous/public channel access | P1 |

**Note**: Configuration testing (env vars, config files) covered in [CONFIG_TESTING_GUIDE.md](./CONFIG_TESTING_GUIDE.md).

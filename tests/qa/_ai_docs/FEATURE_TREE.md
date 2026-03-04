# Anaconda MCP - Feature Tree

## 3-Level Structure
- **Level 1**: Feature Group (category)
- **Level 2**: Feature (specific functionality)
- **Level 3**: User Action (how to use it)

---

## Feature Tree Diagram

```mermaid
mindmap
  root((Anaconda MCP))
    Environment Management
      List Environments
        Ask AI: "List my conda environments"
        API: tools/call conda_list_environments
      List Environment Packages
        Ask AI: "What packages are in env X?"
        API: tools/call conda_list_environment_packages
      Create Environment
        Ask AI: "Create env with Python 3.11"
        API: tools/call conda_create_environment
      Remove Environment
        Ask AI: "Delete environment X"
        API: tools/call conda_remove_environment
      Install Packages
        Ask AI: "Install numpy in env X"
        API: tools/call conda_install_packages
      Remove Packages
        Ask AI: "Remove pandas from env X"
        API: tools/call conda_remove_packages
    Server Management
      Start Server
        CLI: anaconda-mcp serve
        CLI: anaconda-mcp serve --port 8888
      Discover Servers
        CLI: anaconda-mcp discover
        CLI: anaconda-mcp discover --output-format json
      Compose Servers
        CLI: anaconda-mcp compose
        CLI: anaconda-mcp compose --include server1
    Claude Desktop Integration
      Setup Config
        CLI: anaconda-mcp claude-desktop setup-config
        CLI: setup-config --transport streamable-http
      Remove Config
        CLI: anaconda-mcp claude-desktop remove-config
      Show Config
        CLI: anaconda-mcp claude-desktop show
        CLI: claude-desktop show --json
      Get Config Path
        CLI: anaconda-mcp claude-desktop path
    Authentication
      Anaconda Login
        Auto: Browser opens on serve
        Manual: anaconda login before serve
      Token Management
        Auto: Stored in system keyring
        Check: Token used for telemetry
    Configuration
      Environment Variables
        Set: ANACONDA_MCP_LOG_LEVEL=DEBUG
        Set: ANACONDA_MCP_SEND_METRICS=false
      Config File
        Edit: mcp_compose.toml.template
        Override: --config custom.toml
      Python Executable
        Env: ANACONDA_MCP_PYTHON_EXECUTABLE
        Template: {{PYTHON_EXECUTABLE}}
    Transport Modes
      STDIO Transport
        Default for Claude Desktop
        Auto-spawns as subprocess
      HTTP Transport
        Start: anaconda-mcp serve --port 8888
        Connect: --transport streamable-http
```

---

## Feature Tree Table

| Feature Group | Feature | User Actions | Priority |
|---------------|---------|--------------|----------|
| **Environment Management** | List Environments | AI: "List my conda environments"<br>API: `tools/call conda_list_environments` | P0 |
| | List Environment Packages | AI: "What packages are in env X?"<br>API: `tools/call conda_list_environment_packages` | P0 |
| | Create Environment | AI: "Create env with Python 3.11"<br>API: `tools/call conda_create_environment` | P0 |
| | Remove Environment | AI: "Delete environment X"<br>API: `tools/call conda_remove_environment` | P0 |
| | Install Packages | AI: "Install numpy in env X"<br>API: `tools/call conda_install_packages` | P0 |
| | Remove Packages | AI: "Remove pandas from env X"<br>API: `tools/call conda_remove_packages` | P0 |
| **Server Management** | Start Server | `anaconda-mcp serve`<br>`anaconda-mcp serve --port 8888` | P0 |
| | Discover Servers | `anaconda-mcp discover`<br>`anaconda-mcp discover --output-format json` | P1 |
| | Compose Servers | `anaconda-mcp compose`<br>`anaconda-mcp compose --include server1` | P1 |
| **Claude Desktop Integration** | Setup Config | `anaconda-mcp claude-desktop setup-config`<br>`setup-config --transport streamable-http` | P0 |
| | Remove Config | `anaconda-mcp claude-desktop remove-config` | P0 |
| | Show Config | `anaconda-mcp claude-desktop show`<br>`claude-desktop show --json` | P1 |
| | Get Config Path | `anaconda-mcp claude-desktop path` | P1 |
| **Authentication** | Anaconda Login | Auto: Browser opens on serve<br>Manual: `anaconda login` before serve | P0 |
| | Token Management | Auto: Stored in system keyring<br>Used for telemetry | P1 |
| **Configuration** | Environment Variables | `ANACONDA_MCP_LOG_LEVEL=DEBUG`<br>`ANACONDA_MCP_SEND_METRICS=false` | P0 |
| | Config File | Edit: `mcp_compose.toml.template`<br>Override: `--config custom.toml` | P0 |
| | Python Executable | Env: `ANACONDA_MCP_PYTHON_EXECUTABLE`<br>Template: `{{PYTHON_EXECUTABLE}}` | P1 |
| **Transport Modes** | STDIO Transport | Default for Claude Desktop<br>Auto-spawns as subprocess | P0 |
| | HTTP Transport | Start: `anaconda-mcp serve --port 8888`<br>Connect: `--transport streamable-http` | P0 |

---

## User Journey Map

```mermaid
journey
    title First-Time User Journey
    section Installation
      Install package: 5: User
      Verify install: 5: User
    section Setup
      Run setup-config: 5: User
      Restart Claude Desktop: 3: User
    section First Use
      Ask to list environments: 5: User
      Grant permission: 3: User
      See environment list: 5: User
    section Daily Use
      Create environments: 5: User
      Install packages: 5: User
      Delete environments: 4: User
```

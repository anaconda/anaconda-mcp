# Anaconda MCP Architecture

Anaconda MCP is a unified gateway for Anaconda-related AI tools, built on top of [MCP Compose](https://mcp-compose.datalayer.tech). It aggregates multiple downstream MCP servers—such as the Environments MCP server for conda environment management—into a single authenticated endpoint that MCP clients can connect to.

For the complete MCP Compose architecture reference, see the [MCP Compose Architecture Documentation](https://mcp-compose.datalayer.tech/architecture/).

## High-Level Overview

Anaconda MCP sits between MCP clients (Claude Desktop, VS Code, custom agents) and specialized Anaconda MCP servers, providing a single entry point with optional Anaconda authentication.

```mermaid
graph LR
    subgraph Clients
        C1[Claude Desktop]
        C2[VS Code]
        C3[Custom Agent]
    end

    subgraph Anaconda MCP
        Auth[Anaconda Auth]
        Compose[MCP Compose Core]
    end

    subgraph Downstream MCP Servers
        ENV[Environments MCP<br/>conda env management]
        JUP[Jupyter MCP<br/>notebook operations]
        FUTURE[Future Servers<br/>packages, channels...]
    end

    C1 --> Auth
    C2 --> Auth
    C3 --> Auth
    Auth --> Compose
    Compose --> ENV
    Compose --> JUP
    Compose --> FUTURE
```

This architecture enables:
- **Single endpoint**: Clients connect once to access all Anaconda-related tools
- **Unified authentication**: Anaconda tokens validated at the gateway level
- **Extensibility**: New MCP servers can be added without client changes
- **Tool aggregation**: All tools from downstream servers appear in a single unified list

---

## Responsibilities

Anaconda MCP has clearly defined responsibilities that complement the underlying MCP Compose framework:

### Anaconda MCP Layer

| Responsibility | Description |
|----------------|-------------|
| **Anaconda Authentication** | Validates Anaconda bearer tokens against the Anaconda API |
| **Login Flow** | Provides non-blocking browser-based login via `anaconda-auth` |
| **Default Configuration** | Ships with pre-configured downstream servers for Anaconda tools |
| **CLI Wrapper** | Exposes `anaconda-mcp serve` command with sensible defaults |
| **Telemetry Integration** | Initializes Anaconda telemetry when authenticated |

### MCP Compose Layer (inherited)

| Responsibility | Description |
|----------------|-------------|
| **Server Composition** | Aggregates tools from multiple MCP servers |
| **Conflict Resolution** | Handles tool name collisions with prefixing |
| **Transport Management** | STDIO and Streamable HTTP client connections |
| **Process Management** | Lifecycle control for downstream STDIO servers |
| **REST API & Web UI** | Management interfaces for operations |

---

## Component Architecture

```mermaid
graph TD
    subgraph External
        Client[MCP Client]
        Browser[Web Browser]
    end

    subgraph "Anaconda MCP"
        subgraph "Anaconda Layer"
            CLI[anaconda-mcp CLI]
            AnacondaAuth[Anaconda Auth<br/>Token Validation]
            Login[Login Flow<br/>Browser OAuth]
            Telemetry[Telemetry Init]
        end
        
        subgraph "MCP Compose Layer"
            Transport[Transport Layer<br/>STDIO / HTTP]
            ToolMgr[Tool Manager]
            ProcMgr[Process Manager]
            API[REST API]
        end
    end
    
    subgraph "Downstream Servers"
        ENV[Environments MCP<br/>:4041]
        JUP[Jupyter MCP<br/>:8889]
    end
    
    Client --> Transport
    Browser --> API
    CLI --> Login
    Login --> AnacondaAuth
    Transport --> AnacondaAuth
    AnacondaAuth --> ToolMgr
    ToolMgr --> ENV
    ToolMgr --> JUP
    ProcMgr --> ENV
```

The **Anaconda Layer** handles authentication and provides CLI commands, while the **MCP Compose Layer** handles the core composition logic. Authentication is performed at the gateway—downstream servers don't need their own auth.

---

## Downstream MCP Servers

### Environments MCP Server

The primary downstream server, providing tools for conda environment management:

```mermaid
graph LR
    subgraph "Environments MCP Server"
        direction TB
        T1[create_environment]
        T2[list_environments]
        T3[delete_environment]
        T4[install_packages]
        T5[export_environment]
    end
    
    subgraph "Composed Tools (prefix strategy)"
        CT1[conda_environments_create_environment]
        CT2[conda_environments_list_environments]
        CT3[conda_environments_delete_environment]
        CT4[conda_environments_install_packages]
    end
    
    T1 --> CT1
    T2 --> CT2
    T3 --> CT3
    T4 --> CT4
    T5 --> CT5
```

The Environments MCP server runs as a standalone HTTP service on port 4041. Anaconda MCP connects to it via STDIO or Streamable HTTP transport (see details in the [CONFIGURATION_GUIDE](./CONFIGURATION_GUIDE.md) and auto-starts it if configured.

### Future Servers

The architecture supports adding additional MCP servers:

| Server | Purpose | Status |
|--------|---------|--------|
| **Environments MCP** | Conda environment management | ✅ Available |
| **Jupyter MCP** | Notebook operations | 🔄 Planned |
| **Packages MCP** | Package search and info | 🔄 Planned |
| **Channels MCP** | Channel management | 🔄 Planned |

---

## Authentication Flow

Anaconda MCP handles authentication at startup, not per-request. The server initiates the authentication flow and stores credentials securely in the system keyring using the `anaconda-auth` library.

### Browser-Based Login Flow

When Anaconda MCP starts, it checks for an existing API token in the system keyring (managed by `anaconda-auth`). If no token is found, it initiates a browser-based OAuth login flow. The user authenticates via the Anaconda website, and the token is securely stored in the keyring for subsequent requests.

```mermaid
sequenceDiagram
    participant User
    participant Anaconda as Anaconda MCP Server
    participant Composer as MCP Composer Server
    participant ENV as Environments MCP Server
    participant Keyring as System Keyring
    participant Browser
    participant API as Anaconda API

    User->>Anaconda: anaconda-mcp serve
    Anaconda->>Keyring: Check for API token
    
    alt Token exists in keyring
        Keyring-->>Anaconda: Token found
        Anaconda->>Anaconda: Use token from keyring (no pre-validation)
        Note over Anaconda,API: Future enhancement: validate token via Anaconda API before use
        Anaconda->>Anaconda: Initialize telemetry
    else No token in keyring
        Anaconda->>Browser: Open login page (background)
        User->>Browser: Authenticate
        Browser->>API: OAuth flow
        API-->>Browser: Token issued
        Browser->>Keyring: Store token (via anaconda-auth)
        Anaconda->>Keyring: Poll for token
        Keyring-->>Anaconda: Token available
        Anaconda->>Anaconda: Initialize telemetry
    end
    
    Anaconda->>Composer: Initialize MCP Compose
    Composer->>ENV: Start/Connect to server
    ENV-->>Composer: Ready
    Composer-->>Anaconda: Composition ready
    Anaconda-->>User: Server ready
```

Once authenticated, the token is persisted in the system keyring. Subsequent server starts will retrieve the stored token without requiring re-authentication. Users can also manually authenticate using `anaconda auth login` before starting the server.

### Token Retrieval for Requests

After startup, Anaconda MCP retrieves the token from the system keyring as needed for external API calls.

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Anaconda as Anaconda MCP Server
    participant Composer as MCP Composer Server
    participant ENV as Environments MCP Server
    participant Keyring as System Keyring

    Client->>Anaconda: tools/call
    Anaconda->>Keyring: Get stored token
    Keyring-->>Anaconda: Token
    Anaconda->>Composer: Route tool call
    Composer->>ENV: tools/call (no auth required)
    ENV-->>Composer: Result
    Composer-->>Anaconda: Result
    Anaconda-->>Client: Result
```

Note: Downstream MCP servers (like Environments MCP) don't require authentication—they're accessed only through the Anaconda MCP gateway which has already authenticated the user at startup.

---

## Startup Sequence

When `anaconda-mcp serve` is executed:

```mermaid
sequenceDiagram
    participant User
    participant Anaconda as Anaconda MCP Server
    participant Composer as MCP Composer Server
    participant ENV as Environments MCP Server

    User->>Anaconda: anaconda-mcp serve
    Anaconda->>Anaconda: start_login()
    
    alt Token exists
        Anaconda->>Anaconda: Initialize telemetry
    else No token
        Anaconda->>Anaconda: Start browser login (background)
        Anaconda->>Anaconda: Watch for token (background)
    end
    
    Anaconda->>Composer: serve(config)
    Composer->>Composer: Load mcp_compose.toml
    
    loop For each server with auto_start=true
        Composer->>ENV: Start subprocess
        ENV-->>Composer: HTTP server ready on :4041
    end
    
    Composer->>ENV: Connect via Streamable HTTP
    Composer->>ENV: Discover tools
    ENV-->>Composer: Tool list
    Composer->>Composer: Apply prefix strategy
    Composer-->>Anaconda: Composition ready
    Anaconda-->>User: Server ready (N tools)
```

Key points:
1. Login is **non-blocking**—the server starts regardless of auth state
2. Downstream servers with `auto_start=true` are spawned automatically
3. Tool discovery happens after subprocess initialization
4. The prefix strategy is applied to avoid tool name collisions

---

## Configuration

Anaconda MCP uses the standard MCP Compose configuration format. The default configuration lives at `src/anaconda_mcp/mcp_compose.toml`:

```toml
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
port = 8888

[authentication]
enabled = false
providers = ["anaconda"]
default_provider = "anaconda"

[authentication.anaconda]
domain = "anaconda.com"

[[servers.proxied.streamable-http]]
name = "conda_environments"
url = "http://localhost:4041/mcp"
auto_start = true
command = ["environments-mcp-server", "start", "--transport", "streamable-http"]
startup_delay = 3
```

For full configuration options, see the [Configuration Guide](./CONFIGURATION_GUIDE.md) and [MCP Compose Configuration](https://mcp-compose.datalayer.tech/configuration/).

---

## Extensibility

The `anaconda-mcp serve` command supports additional STDIO and Streamable HTTP transports (see details in the [CONFIGURATION_GUIDE](./CONFIGURATION_GUIDE.md)) and can auto-start them if configured.


### Adding a New Downstream Server

To add a new MCP server (e.g., Jupyter MCP):

1. Add the server configuration to `mcp_compose.toml`:

```toml
[[servers.proxied.streamable-http]]
name = "jupyter"
url = "http://localhost:8888/mcp"
auto_start = false  # Started separately
timeout = 30
```

2. The server's tools will automatically appear with the configured prefix (e.g., `jupyter_create_notebook`)

3. No changes to client code required—tools are discovered dynamically

### Creating Custom Downstream Servers

Custom MCP servers can be integrated if they support:
- **STDIO transport**: Run as subprocess, communicate via stdin/stdout
- **Streamable HTTP transport**: Run as HTTP server, expose `/mcp` endpoint

---

## Further Reading

- [MCP Compose Architecture](https://mcp-compose.datalayer.tech/architecture/) — Full architecture reference
- [MCP Compose Configuration](https://mcp-compose.datalayer.tech/configuration/) — Configuration options
- [Anaconda MCP Configuration Guide](./CONFIGURATION_GUIDE.md) — Quick configuration reference

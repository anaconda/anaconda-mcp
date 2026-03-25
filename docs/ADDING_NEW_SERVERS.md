# Adding New MCP Servers (Downstreams)

Anaconda MCP is built on [MCP Compose](https://mcp-compose.datalayer.tech), a unified control plane that composes multiple MCP servers behind a single endpoint. Each downstream server exposes its own set of tools, and MCP Compose makes them all available to clients transparently — no client changes needed.

This guide explains how to register a new downstream server so its tools appear in Anaconda MCP.

---

## Prerequisites: Packaging Requirements

> ⚠️ **Downstream servers must be shipped as conda packages.**

All downstream MCP servers are declared as dependencies of the `anaconda-mcp` conda package. We currently only ship conda packages.

Before shipping the new downstream server it is necessary to publish it to our main channel.

---

## Before You Start

Understand which config file to touch:

| File | Role | Edit? |
|------|------|----|
| `src/anaconda_mcp/mcp_compose.toml.template` | **Primary config** — rendered at runtime | ✅ Yes |
| `src/anaconda_mcp/mcp_compose.toml` | Fallback — used only if template is missing | ✅ Yes |

**Always edit the `.template` file.** If the template exists (it does), edits to `mcp_compose.toml` are silently ignored.

> For more detail on how the template rendering works, see [SERVER_CONFIGURATION.md](./SERVER_CONFIGURATION.md).

---

## Two Ways to Connect a Server

MCP Compose supports two transport types for downstream servers.

### Option 1 — Streamable HTTP (recommended for Anaconda servers)

Use this when your server runs as an HTTP service. MCP Compose can also auto-start it as a subprocess.

Add a `[[servers.proxied.streamable-http]]` block to `mcp_compose.toml.template`:

```toml
[[servers.proxied.streamable-http]]
name = "my-server"                        # unique name; used as tool prefix
url = "http://localhost:<PORT>/mcp"       # where MCP Compose will connect
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"

# auto_start launches the server as a subprocess when anaconda-mcp starts.
# Remove this block if the server is managed externally.
auto_start = true
command = ["{{PYTHON_EXECUTABLE}}", "-m", "my_server_module", "start",
           "--transport", "streamable-http", "--port", "<PORT>"]
startup_delay = 3                         # seconds to wait after launch
```

**`{{PYTHON_EXECUTABLE}}`** is replaced at runtime with the Python interpreter running `anaconda-mcp` (or the value of `ANACONDA_MCP_PYTHON_EXECUTABLE` if set). Always use this placeholder instead of a hard-coded path.

### Option 2 — STDIO

Use this when your server communicates over stdin/stdout (e.g., a Node.js or Python script launched as a subprocess).

```toml
[[servers.proxied.stdio]]
name = "my-server"
command = ["{{PYTHON_EXECUTABLE}}", "-m", "my_server_module", "start", "--transport", "stdio"]
restart_policy = "on-failure"
```

---

## Tool Naming and Prefixes

MCP Compose uses `conflict_resolution = "prefix"` by default (configured in `[composer]` and `[tool_manager]`). This means every tool from your server is automatically namespaced:

```
{server_name}_{tool_name}
```

For example, a server named `jupyter` with a tool `run_cell` becomes `jupyter_run_cell`.

Choose `name` values that are short, lowercase, and descriptive — they become part of every tool name that clients see.

### Optional: Aliases

If you want to expose a tool under a friendlier name, add an alias in the `[tool_manager.aliases]` section:

```toml
[tool_manager.aliases]
run_cell = "jupyter_run_cell"
```

---

## Minimal Real-World Example

Adding a hypothetical `jupyter` server that auto-starts on port `4042`:

```toml
[[servers.proxied.streamable-http]]
name = "jupyter"
url = "http://localhost:4042/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["{{PYTHON_EXECUTABLE}}", "-m", "jupyter_mcp_server", "start",
           "--transport", "streamable-http", "--port", "4042"]
startup_delay = 3
```

After adding this block, restart `anaconda-mcp`. The server's tools will appear prefixed as `jupyter_*`.

---

## Checklist

- [ ] Server is packaged and available as a **conda package**
- [ ] Package is declared as a dependency of `anaconda-mcp` in the conda recipe
- [ ] Edited `mcp_compose.toml.template` and `mcp_compose.toml`
- [ ] Chose a unique `name` for the server
- [ ] Set `url` to match the port/path your server listens on (if using streamable-http)
- [ ] Used `{{PYTHON_EXECUTABLE}}` in `command` (not a hard-coded path)
- [ ] Set an appropriate `startup_delay` if the server takes time to initialize
- [ ] Restarted `anaconda-mcp` to pick up the changes

---

## Further Reading

- [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) — Full reference for all TOML options
- [SERVER_CONFIGURATION.md](./SERVER_CONFIGURATION.md) — Template vs. fallback file explained
- [MCP Compose Servers Documentation](https://mcp-compose.datalayer.tech/configuration/#servers-section) — Upstream reference

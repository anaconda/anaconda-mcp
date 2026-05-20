# Anaconda MCP

`anaconda mcp` is a CLI and server for exposing conda environment management tools to MCP-enabled AI coding assistants. It acts as a unified MCP endpoint, giving AI assistants like Claude, Cursor, and VS Code awareness of your conda environments, packages, and channel configurations.

📖 **Full documentation:** [anaconda.com/docs](https://www.anaconda.com/docs/cli-reference/anaconda-mcp/getting-started) · [Development Guide](docs/DEVELOPMENT.md)

---

## Prerequisites

- [Conda](https://docs.conda.io/en/latest/) (Miniconda or Anaconda Distribution)

---

## Installation

```bash
conda create -n anaconda-mcp -c anaconda-connector -c datalayer anaconda-mcp
conda activate anaconda-mcp
```

---

## Anaconda Login

Authentication is **required**. The server will not start and tool calls will not succeed without a valid Anaconda login.

```bash
anaconda login
```

This opens a browser for OAuth login and stores the token in your system keyring. Subsequent starts use the stored token automatically.

---

## Accept the Terms of Service

Anaconda MCP requires you to accept the [Beta Terms](https://www.anaconda.com/legal/terms/mcpbeta) before tool calls will succeed.

**Interactive (recommended):**

```bash
anaconda mcp terms accept
```

**Non-interactive (CI / headless):**

```bash
export ANACONDA_MCP_ACCEPTED_TERMS=true
export ANACONDA_MCP_ACCEPTED_TERMS_VERSION=2026-05-19
```

---

## Setup

Configure your AI client to use Anaconda MCP:

```bash
anaconda mcp setup
```

This launches an interactive wizard that detects supported clients and writes the appropriate config. Supported clients: Claude Desktop, Claude Code, Cursor, Windsurf, VS Code, and OpenCode.

To configure a specific client non-interactively:

```bash
anaconda mcp setup --client claude-code
anaconda mcp setup --client cursor --scope project
```

---

## Configuration

Anaconda MCP is configured via `mcp_compose.toml.template`, which is rendered at startup. Always edit the template — not `mcp_compose.toml` directly.

See the [full configuration reference](https://www.anaconda.com/docs/cli-reference/anaconda-mcp/getting-started#configuration) for transport, server composition, tool aliases, and Python executable settings.

---

## Experimental: `ana` CLI

The [`ana` CLI](https://github.com/anaconda/anaconda-cli#installation) handles installation and environment setup automatically.

Install `ana`:

```bash
curl -fsSL https://anaconda.sh/install.sh | sh
```

Then configure your AI client to launch the MCP server with:

```
ana mcp serve
```

You still need to authenticate and accept TOS by running `anaconda login` and `anaconda mcp terms accept` beforehand.

---

## Manual Client Configuration

If you prefer to configure your AI client manually, add an entry to your client's MCP config JSON.

Example for Claude Code (`.mcp.json`):

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "type": "stdio",
      "command": "/path/to/anaconda3/envs/anaconda-mcp/bin/python",
      "args": ["-m", "anaconda_mcp", "serve"],
      "env": {}
    }
  }
}
```

⚠️ **Each client has a different JSON schema.** Check your client's MCP documentation carefully when writing configuration manually — field names and structure vary between Claude Code, Cursor, VS Code, and others.

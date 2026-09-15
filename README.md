# Anaconda MCP

`anaconda mcp` is a CLI and server for exposing conda environment management tools to MCP-enabled AI coding assistants. It acts as a unified MCP endpoint, giving AI assistants like Claude, Cursor, and VS Code awareness of your conda environments, packages, and channel configurations.

📖 **Full documentation:** [anaconda.com/docs](https://www.anaconda.com/docs/cli-reference/anaconda-mcp/getting-started) · [Development Guide](docs/DEVELOPMENT.md)

---

## Prerequisites

- [Conda](https://docs.conda.io/en/latest/) (Miniconda or Anaconda Distribution)

---

## Installation

```bash
conda create -n anaconda-mcp anaconda-mcp
conda activate anaconda-mcp
```

---

## Installation via pip or uvx

**Requires Python 3.10–3.14.**

```bash
pip install anaconda-mcp
```

```bash
uvx anaconda-mcp@latest
```

**Prerequisite:** `conda` must be installed separately and discoverable on your `PATH`. pip and uvx do not provide conda. Without a working conda installation, the conda tools this server exposes will fail. Install [Miniconda or Anaconda Distribution](https://docs.conda.io/en/latest/) first, then follow the `anaconda login` and `anaconda mcp terms accept` steps below.

> **Important:** The Anaconda MCP Server connects your conda environments to MCP-compatible AI assistants, enabling them to create, modify, and delete environments and packages on your machine. Install only if you trust the AI assistant you intend to connect and understand it can take real actions on your machine. By installing you acknowledge: (1) The AI assistant you connect to this MCP server is an independent third-party model, not a product or service of Anaconda. (2) Anaconda is NOT responsible for the actions the AI assistant directs within your environment, including unintended changes or deletions.

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
export ANACONDA_MCP_ACCEPTED_TERMS_VERSION=2026-05-27
```

---

## Setup

Configure your AI client to use Anaconda MCP:

```bash
anaconda mcp setup
```

This launches an interactive wizard that detects supported clients and adds the remote Anaconda MCP service (`https://anaconda.com/api/mcp`) to each selected client's MCP config. Supported clients: Claude Desktop, Claude Code, Cursor, Windsurf, VS Code, OpenCode, Kilo Code, and Codex.

To configure a specific client non-interactively:

```bash
anaconda mcp setup --client claude-code
anaconda mcp setup --client cursor
anaconda mcp setup --client kilo
anaconda mcp setup --client codex
```

Re-running `setup` overwrites an existing `anaconda-mcp` entry (a backup is created by default), so it also migrates legacy stdio entries to the remote service.

> **Note:** Claude Desktop does not support remote MCP servers in its config file, so `setup` keeps configuring the local stdio server for it.

### Kilo Code Configuration

Anaconda MCP writes a plain `kilo.json` file (`~/.config/kilo/kilo.json`) which Kilo Code deep-merges with any existing `kilo.jsonc`. This means hand-written comments in `kilo.jsonc` are preserved across `anaconda mcp setup` runs. **Important:** if you hand-edit `kilo.json` itself with comments, `anaconda mcp setup` cannot parse it — it treats the file as empty and silently overwrites it, discarding your changes. Keep comments in `kilo.jsonc` instead.

---

## Manual Client Configuration

If you prefer to configure your AI client manually, point it at the remote Anaconda MCP service with your API key as a bearer token. Example for Claude Code (`~/.claude.json`):

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "type": "http",
      "url": "https://anaconda.com/api/mcp",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}
```

Example for Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.anaconda-mcp]
url = "https://anaconda.com/api/mcp"
http_headers = { Authorization = "Bearer <your-api-key>" }
```

API keys can be obtained from your [Anaconda account settings](https://anaconda.com/app).

Claude Desktop is the exception: its config file only supports stdio servers, so keep the local server entry there:

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

Optionally, you can pass authentication and TOS acceptance via the stdio `env` dict instead of running `anaconda login` and `anaconda mcp terms accept`:

```json
"env": {
  "ANACONDA_AUTH_API_KEY": "<your-api-key>",
  "ANACONDA_MCP_ACCEPTED_TERMS": "true",
  "ANACONDA_MCP_ACCEPTED_TERMS_VERSION": "2026-05-27"
}
```

⚠️ **Each client has a different JSON schema.** Check your client's MCP documentation carefully when writing configuration manually — field names and structure vary between Claude Code, Cursor, VS Code, and others.

---

## Experimental: `ana` CLI

The [`ana` CLI](https://github.com/anaconda/anaconda-cli#installation) handles
Anaconda MCP runtime installation and environment setup automatically, so you
don't need to manage a dedicated `anaconda-mcp` conda environment path.

`ana mcp serve` installs and runs the managed Anaconda MCP runtime. It does not
install Miniconda, Anaconda Distribution, or a user-facing `conda` command. If
you want to activate or inspect environments from a terminal, notebook, or other
local tooling, install and configure conda separately for that workflow.

Install `ana`:

```bash
curl -fsSL https://anaconda.sh/install.sh | sh
```

You still need to authenticate and accept TOS by running `anaconda login` and `anaconda mcp terms accept` beforehand.

When configuring your client manually with `ana`, use:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "type": "stdio",
      "command": "ana",
      "args": ["mcp", "serve"],
      "env": {}
    }
  }
}
```

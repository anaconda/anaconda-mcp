<!--
  ~ Copyright (c) Anaconda, Inc.
  ~
  ~ Apache-2.0 License
-->

# Anaconda MCP - MCPB Bundle

One-click installer for [Anaconda MCP](https://github.com/anaconda/anaconda-mcp) in Claude Desktop.

## What is this?

This directory contains the source files for building an MCPB (MCP Bundle) / DXT (Desktop Extension) package. The resulting `.mcpb` file allows users to install Anaconda MCP in Claude Desktop with a single click — no terminal or manual configuration needed.

## Prerequisites

- [Node.js](https://nodejs.org/) (for the `mcpb` CLI tool)
- A working conda installation (Anaconda or Miniconda)
- A conda environment named `anaconda-mcp` with the `anaconda-mcp` package installed:

  ```bash
  conda create -n anaconda-mcp python>=3.10
  conda activate anaconda-mcp
  pip install anaconda-mcp
  ```

  The bundle includes a wrapper shell script that sources the user's shell profile to initialize conda automatically. No environment variables need to be set manually.

## Building the Bundle

1. Install the MCPB CLI tool:

   ```bash
   npm install -g @anthropic-ai/mcpb
   ```

2. Build the `.mcpb` file from this directory:

   ```bash
   cd mcpb
   mcpb pack
   ```

   This creates `anaconda-mcp-0.1.0.mcpb` in the current directory.

## Installing in Claude Desktop

1. Double-click the `.mcpb` file, or drag it into Claude Desktop Settings
2. The extension is ready to use — the wrapper script automatically finds your conda installation

## How It Works

This bundle uses the **binary** server type with a shell wrapper script:

- The user must have a pre-existing conda environment named `anaconda-mcp` with the `anaconda-mcp` Python package installed
- A wrapper script (`src/run.sh`) sources the user's shell profile (`~/.zshrc`, `~/.bashrc`, etc.) to initialize conda, since Claude Desktop as a GUI app does not inherit terminal environment variables
- The script resolves `${CONDA_PREFIX}/envs/anaconda-mcp/bin/python` after conda initialization, making it robust across different installations and platforms
- The server runs in **stdio** transport mode for direct communication with Claude Desktop

The server uses `mcp-compose` under the hood to compose and proxy the conda environments MCP server, giving Claude access to conda environment and package management tools.

## Bundle Structure

```
mcpb/
├── manifest.json      # Extension metadata, tools, and configuration
├── pyproject.toml     # Python dependencies
├── .mcpbignore        # Files to exclude from the bundle
├── README.md          # This file
└── src/
    ├── run.sh         # Shell wrapper that initializes conda and launches Python
    └── server.py      # MCP server entry point
```

## Available Tools

| Tool | Description |
|------|-------------|
| `list_environments` | List all installed conda environments |
| `create_environment` | Create a new conda environment with optional packages |
| `delete_environment` | Delete a conda environment by name or path |
| `remove_environment` | Remove a conda environment (alias for delete) |
| `install_packages` | Install packages into a conda environment |
| `delete_packages` | Delete packages from a conda environment |
| `remove_packages` | Remove packages from a conda environment (alias for delete) |

## Future Improvements

The server launch command currently requires the correct conda environment to be active. Areas for improvement include:

- Add `conda` as a supported server type in MCPB (currently limited to `python`, `node`, `binary`, and `uv`).
- Allow users to select or configure the conda environment via the Claude Desktop UI.
- Support auto-discovery of existing conda installations and environments.
- Automatically create and configure a dedicated conda environment during MCPB installation.
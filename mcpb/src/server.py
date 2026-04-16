#!/usr/bin/env python3
# Copyright (c) Anaconda, Inc.
#
# Apache-2.0 License

"""Anaconda MCP - MCPB entry point for Claude Desktop.

This is a thin wrapper that launches the Anaconda MCP server
in stdio transport mode for use with Claude Desktop and other
MCP-compatible applications.

The server composes and proxies the conda environments MCP tools,
providing environment and package management capabilities.
"""

import sys

if __name__ == "__main__":
    # Ensure the CLI receives "serve" as the subcommand.
    # Click reads sys.argv, so we inject "serve" for stdio transport.
    sys.argv = [sys.argv[0], "serve"]

    from anaconda_mcp.cli import main

    main()

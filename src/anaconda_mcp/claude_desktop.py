"""
Claude Desktop configuration utilities for Anaconda MCP.

This module provides functionality to configure Claude Desktop to work with
Anaconda MCP, supporting both STDIO and Streamable HTTP transports across
Linux, macOS, and Windows.
"""

import json
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def get_claude_desktop_config_path() -> Path:
    """
    Get the default Claude Desktop configuration file path based on the OS.

    Returns:
        Path to claude_desktop_config.json

    Raises:
        RuntimeError: If the OS is not supported
    """
    system = platform.system()

    if system == "Linux":
        # Linux: ~/.config/Claude/claude_desktop_config.json
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    elif system == "Darwin":
        # macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    elif system == "Windows":
        # Windows: %APPDATA%\Claude\claude_desktop_config.json
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        else:
            return (
                Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
            )
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")


def get_anaconda_mcp_config_dir() -> Path:
    """
    Get the directory containing the default Anaconda MCP configuration.

    This returns the path to the directory containing mcp_compose.toml,
    which is used as MCP_COMPOSE_CONFIG_DIR for STDIO transport.

    The path is computed from the Python executable location:
    - If Python is at /path/to/env/bin/python, returns /path/to/env/etc
    - Uses sys.prefix to get the environment root
    - Returns {prefix}/etc regardless of whether the file exists

    Returns:
        Path to the etc directory
    """
    # Get the Python prefix (environment root) from the executable
    # sys.prefix is the directory containing the Python installation
    prefix = Path(sys.prefix)
    
    # Return the etc directory based on the Python environment
    return prefix / "etc"


def backup_config_file(config_path: Path) -> Path | None:
    """
    Create a timestamped backup of the configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Path to the backup file, or None if no backup was created (file doesn't exist)
    """
    if not config_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.with_suffix(f".{timestamp}.backup.json")
    shutil.copy2(config_path, backup_path)
    return backup_path


def load_config(config_path: Path) -> dict[str, Any]:
    """
    Load the Claude Desktop configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Configuration dictionary (empty if file doesn't exist)
    """
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Return empty config if file is corrupted or cannot be read
        return {}


def save_config(config_path: Path, config: dict[str, Any]) -> None:
    """
    Save the Claude Desktop configuration file.

    Args:
        config_path: Path to the configuration file
        config: Configuration dictionary to save
    """
    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")  # Add trailing newline


def get_python_executable() -> str:
    """
    Get the Python executable path.

    Returns:
        Path to the Python executable
    """
    return sys.executable


def build_stdio_config(server_name: str = "anaconda-mcp") -> dict[str, Any]:
    """
    Build the STDIO MCP server configuration for Claude Desktop.

    Uses MCP_COMPOSE_CONFIG_DIR special variable for portable configuration.

    Args:
        server_name: Name for the MCP server in Claude Desktop

    Returns:
        Server configuration dictionary
    """
    python_exe = get_python_executable()
    config_dir = get_anaconda_mcp_config_dir()
    config_file = config_dir / "mcp_compose.toml"

    return {
        "command": python_exe,
        "args": ["-m", "anaconda_mcp", "serve", "--config", str(config_file)],
        "env": {
            "MCP_COMPOSE_CONFIG_DIR": str(config_dir),
        },
    }


def build_streamable_http_config(
    server_name: str = "anaconda-mcp",
    host: str = "localhost",
    port: int = 8888,
) -> dict[str, Any]:
    """
    Build the Streamable HTTP MCP server configuration for Claude Desktop.

    Note: Claude Desktop connects to an already-running HTTP server.
    The server must be started separately with `anaconda-mcp serve`.

    Args:
        server_name: Name for the MCP server in Claude Desktop
        host: Host where the server is running
        port: Port where the server is listening

    Returns:
        Server configuration dictionary
    """
    return {
        "url": f"http://{host}:{port}/mcp",
        "transport": "streamable-http",
    }


def configure_claude_desktop(
    config_path: Path | None = None,
    server_name: str = "anaconda-mcp",
    transport: str = "stdio",
    host: str = "localhost",
    port: int = 8888,
    backup: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """
    Configure Claude Desktop to use Anaconda MCP.

    Args:
        config_path: Path to Claude Desktop config (uses default if None)
        server_name: Name for the MCP server entry
        transport: Transport type ('stdio' or 'streamable-http')
        host: Host for streamable-http transport
        port: Port for streamable-http transport
        backup: Whether to backup existing config
        force: Whether to overwrite existing server configuration

    Returns:
        Dictionary with operation results:
        - config_path: Path to the configuration file
        - backup_path: Path to backup file (if created)
        - server_name: Name of the configured server
        - transport: Transport type used
        - created: Whether the config file was created
        - updated: Whether an existing entry was updated

    Raises:
        ValueError: If transport is invalid
        FileExistsError: If server already exists and force=False
    """
    if transport not in ("stdio", "streamable-http"):
        raise ValueError(f"Invalid transport: {transport}. Must be 'stdio' or 'streamable-http'")

    if config_path is None:
        config_path = get_claude_desktop_config_path()

    result = {
        "config_path": config_path,
        "backup_path": None,
        "server_name": server_name,
        "transport": transport,
        "created": not config_path.exists(),
        "updated": False,
    }

    # Backup existing config
    if backup:
        result["backup_path"] = backup_config_file(config_path)

    # Load existing config
    config = load_config(config_path)
    old_config = json.loads(json.dumps(config))  # Deep copy for comparison

    # Ensure mcpServers section exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Check if server already exists
    if server_name in config["mcpServers"] and not force:
        raise FileExistsError(
            f"Server '{server_name}' already exists in Claude Desktop config. "
            "Use --force to overwrite."
        )

    if server_name in config["mcpServers"]:
        result["updated"] = True

    # Build server configuration
    if transport == "stdio":
        server_config = build_stdio_config(server_name)
    else:
        server_config = build_streamable_http_config(server_name, host, port)

    # Add/update server configuration
    config["mcpServers"][server_name] = server_config

    # Save configuration
    save_config(config_path, config)

    # Add configs for diff display
    result["old_config"] = old_config
    result["new_config"] = config

    return result


def remove_claude_desktop_config(
    config_path: Path | None = None,
    server_name: str = "anaconda-mcp",
    backup: bool = True,
) -> dict[str, Any]:
    """
    Remove Anaconda MCP configuration from Claude Desktop.

    Args:
        config_path: Path to Claude Desktop config (uses default if None)
        server_name: Name of the MCP server entry to remove
        backup: Whether to backup existing config

    Returns:
        Dictionary with operation results:
        - config_path: Path to the configuration file
        - backup_path: Path to backup file (if created)
        - server_name: Name of the removed server
        - removed: Whether the entry was removed

    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If server entry doesn't exist
    """
    if config_path is None:
        config_path = get_claude_desktop_config_path()

    if not config_path.exists():
        raise FileNotFoundError(f"Claude Desktop config not found: {config_path}")

    result = {
        "config_path": config_path,
        "backup_path": None,
        "server_name": server_name,
        "removed": False,
    }

    # Backup existing config
    if backup:
        result["backup_path"] = backup_config_file(config_path)

    # Load config
    config = load_config(config_path)

    # Check if server exists
    if "mcpServers" not in config or server_name not in config["mcpServers"]:
        raise KeyError(f"Server '{server_name}' not found in Claude Desktop config")

    # Remove server
    del config["mcpServers"][server_name]
    result["removed"] = True

    # Save configuration
    save_config(config_path, config)

    return result


def show_claude_desktop_config(
    config_path: Path | None = None,
    server_name: str | None = None,
) -> dict[str, Any]:
    """
    Show the current Claude Desktop configuration.

    Args:
        config_path: Path to Claude Desktop config (uses default if None)
        server_name: If provided, show only this server's configuration

    Returns:
        Dictionary with configuration information:
        - config_path: Path to the configuration file
        - exists: Whether the config file exists
        - config: The full or server-specific configuration
    """
    if config_path is None:
        config_path = get_claude_desktop_config_path()

    result = {
        "config_path": config_path,
        "exists": config_path.exists(),
        "config": None,
    }

    if not result["exists"]:
        return result

    config = load_config(config_path)

    if server_name:
        servers = config.get("mcpServers", {})
        result["config"] = servers.get(server_name)
    else:
        result["config"] = config

    return result

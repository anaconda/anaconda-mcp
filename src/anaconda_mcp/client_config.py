import json
import sys
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir

from anaconda_mcp.claude_desktop import (
    backup_config_file,
    configure_claude_desktop,
    get_claude_desktop_config_path,
    load_config,
    save_config,
)
from anaconda_mcp.claude_desktop import (
    build_stdio_config as _claude_build_stdio_config,
)
from anaconda_mcp.claude_desktop import (
    build_streamable_http_config as _claude_build_http_config,
)
from anaconda_mcp.consts import TransportTypes

SUPPORTED_CLIENTS: dict[str, dict[str, Any]] = {
    "claude-desktop": {"config_key": "mcpServers"},
    "cursor": {"config_key": "mcpServers"},
    "windsurf": {"config_key": "mcpServers"},
    "vscode": {"config_key": "servers"},
    "opencode": {"config_key": "mcp"},
}


def get_client_config_path(client: str) -> Path:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'. Must be one of {sorted(SUPPORTED_CLIENTS)}")

    if client == "claude-desktop":
        return get_claude_desktop_config_path()

    if client == "cursor":
        return Path.home() / ".cursor" / "mcp.json"

    if client == "windsurf":
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    if client == "vscode":
        return Path(user_data_dir("Code", appauthor=False)) / "User" / "mcp.json"

    if client == "opencode":
        return Path(user_config_dir("opencode", appauthor=False)) / "opencode.json"

    raise ValueError(f"Unsupported client: '{client}'")


def build_client_stdio_config(client: str) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'")

    if client == "claude-desktop":
        return _claude_build_stdio_config()

    executable = sys.executable

    if client == "opencode":
        return {
            "type": "local",
            "command": [executable, "-m", "anaconda_mcp", "serve"],
            "enabled": True,
            "environment": {},
        }

    if client == "cursor":
        return {
            "type": "stdio",
            "command": executable,
            "args": ["-m", "anaconda_mcp", "serve"],
        }

    return {
        "command": executable,
        "args": ["-m", "anaconda_mcp", "serve"],
    }


def build_client_http_config(client: str, host: str = "localhost", port: int = 8888) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'")

    url = f"http://{host}:{port}/mcp"

    if client == "windsurf":
        return {"serverUrl": url}

    if client == "vscode":
        return {"type": "http", "url": url}

    if client == "opencode":
        return {"type": "remote", "url": url, "enabled": True}

    return _claude_build_http_config(host, port)


def configure_client(
    client: str,
    config_path: Path | None = None,
    server_name: str = "anaconda-mcp",
    transport: str = "stdio",
    host: str = "localhost",
    port: int = 8888,
    backup: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'")

    valid_transports = {t.value for t in TransportTypes}
    if transport not in valid_transports:
        raise ValueError(f"Invalid transport: {transport}. Must be one of {valid_transports}")

    if client == "claude-desktop":
        result = configure_claude_desktop(
            config_path=config_path,
            server_name=server_name,
            transport=transport,
            host=host,
            port=port,
            backup=backup,
            force=force,
        )
        result["client"] = client
        return result

    if config_path is None:
        config_path = get_client_config_path(client)

    config_key = SUPPORTED_CLIENTS[client]["config_key"]

    result: dict[str, Any] = {
        "client": client,
        "config_path": config_path,
        "backup_path": None,
        "server_name": server_name,
        "transport": transport,
        "created": not config_path.exists(),
        "updated": False,
    }

    if backup:
        result["backup_path"] = backup_config_file(config_path)

    config = load_config(config_path)
    old_config = json.loads(json.dumps(config))

    if config_key not in config:
        config[config_key] = {}

    if server_name in config[config_key] and not force:
        raise FileExistsError(f"Server '{server_name}' already exists in {client} config. Use --force to overwrite.")

    if server_name in config[config_key]:
        result["updated"] = True

    if transport == TransportTypes.STDIO.value:
        server_config = build_client_stdio_config(client)
    else:
        server_config = build_client_http_config(client, host, port)

    config[config_key][server_name] = server_config

    save_config(config_path, config)

    result["old_config"] = old_config
    result["new_config"] = config

    return result

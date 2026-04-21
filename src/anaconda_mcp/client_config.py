import json
import sys
from pathlib import Path
from typing import Any, cast

from platformdirs import user_config_dir, user_data_dir

from anaconda_mcp.claude_desktop import (
    backup_config_file,
    configure_claude_desktop,
    get_claude_desktop_config_path,
    load_config,
    remove_claude_desktop_config,
    save_config,
)
from anaconda_mcp.claude_desktop import (
    build_stdio_config as _claude_build_stdio_config,
)
from anaconda_mcp.claude_desktop import (
    build_streamable_http_config as _claude_build_http_config,
)
from anaconda_mcp.consts import TransportTypes

SCOPE_GLOBAL = "global"
SCOPE_PROJECT = "project"

SUPPORTED_CLIENTS: dict[str, dict[str, Any]] = {
    "claude-desktop": {"config_key": "mcpServers", "supports_project_scope": False},
    "claude-code": {"config_key": "mcpServers", "supports_project_scope": True},
    "cursor": {"config_key": "mcpServers", "supports_project_scope": True},
    "windsurf": {"config_key": "mcpServers", "supports_project_scope": False},
    "vscode": {"config_key": "servers", "supports_project_scope": True},
    "opencode": {"config_key": "mcp", "supports_project_scope": True},
}


def get_client_project_config_path(client: str, project_dir: Path) -> Path:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'. Must be one of {sorted(SUPPORTED_CLIENTS)}")

    if not SUPPORTED_CLIENTS[client]["supports_project_scope"]:
        raise ValueError(f"'{client}' does not support project scope.")

    if client == "cursor":
        return project_dir / ".cursor" / "mcp.json"

    if client == "vscode":
        return project_dir / ".vscode" / "mcp.json"

    if client == "opencode":
        return project_dir / "opencode.json"

    if client == "claude-code":
        return project_dir / ".mcp.json"

    raise ValueError(f"Unsupported client: '{client}'")


def get_client_config_path(
    client: str,
    scope: str = SCOPE_GLOBAL,
    project_dir: Path | None = None,
) -> Path:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'. Must be one of {sorted(SUPPORTED_CLIENTS)}")

    if scope == SCOPE_PROJECT:
        resolved_dir = project_dir if project_dir is not None else Path.cwd()
        return get_client_project_config_path(client, resolved_dir)

    if client == "claude-desktop":
        return Path(get_claude_desktop_config_path())

    if client == "claude-code":
        return Path.home() / ".claude.json"

    if client == "cursor":
        return Path.home() / ".cursor" / "mcp.json"

    if client == "windsurf":
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    if client == "vscode":
        return Path(str(user_data_dir("Code", appauthor=False))) / "User" / "mcp.json"

    if client == "opencode":
        return Path(str(user_config_dir("opencode", appauthor=False))) / "opencode.json"

    raise ValueError(f"Unsupported client: '{client}'")


def build_client_stdio_config(client: str) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'")

    if client == "claude-desktop":
        return dict(_claude_build_stdio_config())

    executable = sys.executable

    if client == "claude-code":
        return {
            "type": "stdio",
            "command": executable,
            "args": ["-m", "anaconda_mcp", "serve"],
            "env": {},
        }

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

    return dict(_claude_build_http_config(host, port))


def configure_client(
    client: str,
    scope: str = SCOPE_GLOBAL,
    project_dir: Path | None = None,
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

    if scope == SCOPE_PROJECT and not SUPPORTED_CLIENTS[client]["supports_project_scope"]:
        raise ValueError(f"'{client}' does not support project scope.")

    if client == "claude-desktop":
        claude_result: dict[str, Any] = configure_claude_desktop(
            config_path=config_path,
            server_name=server_name,
            transport=transport,
            host=host,
            port=port,
            backup=backup,
            force=force,
        )
        claude_result["client"] = client
        claude_result["scope"] = scope
        return claude_result

    if config_path is None:
        config_path = get_client_config_path(client, scope=scope, project_dir=project_dir)

    config_key = SUPPORTED_CLIENTS[client]["config_key"]

    result: dict[str, Any] = {
        "client": client,
        "scope": scope,
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

    return cast(dict[str, Any], result)


def remove_client(
    client: str,
    scope: str = SCOPE_GLOBAL,
    project_dir: Path | None = None,
    config_path: Path | None = None,
    server_name: str = "anaconda-mcp",
    backup: bool = True,
) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'. Must be one of {sorted(SUPPORTED_CLIENTS)}")

    if scope == SCOPE_PROJECT and not SUPPORTED_CLIENTS[client]["supports_project_scope"]:
        raise ValueError(f"'{client}' does not support project scope.")

    if client == "claude-desktop":
        claude_result: dict[str, Any] = remove_claude_desktop_config(
            config_path=config_path,
            server_name=server_name,
            backup=backup,
        )
        claude_result["client"] = client
        claude_result["scope"] = scope
        return claude_result

    if config_path is None:
        config_path = get_client_config_path(client, scope=scope, project_dir=project_dir)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config_key = SUPPORTED_CLIENTS[client]["config_key"]

    result: dict[str, Any] = {
        "client": client,
        "scope": scope,
        "config_path": config_path,
        "backup_path": None,
        "server_name": server_name,
        "removed": False,
    }

    if backup:
        result["backup_path"] = backup_config_file(config_path)

    config = load_config(config_path)

    if config_key not in config or server_name not in config[config_key]:
        raise KeyError(f"Server '{server_name}' not found in {client} config.")

    del config[config_key][server_name]
    result["removed"] = True

    save_config(config_path, config)

    return cast(dict[str, Any], result)

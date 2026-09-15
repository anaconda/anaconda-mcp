import os
from pathlib import Path
from typing import Any, cast

import tomlkit
from platformdirs import user_data_dir

from anaconda_mcp.claude_desktop import (
    backup_config_file,
    configure_claude_desktop,
    get_claude_desktop_config_path,
    load_config,
    remove_claude_desktop_config,
    save_config,
)
from anaconda_mcp.config import settings

REMOTE_MCP_URL = f"https://{settings.anaconda_domain or 'anaconda.com'}/api/mcp"

TRANSPORT_STDIO = "stdio"
TRANSPORT_HTTP = "http"

SUPPORTED_CLIENTS: dict[str, dict[str, Any]] = {
    "claude-desktop": {"config_key": "mcpServers", "transport": TRANSPORT_STDIO},
    "claude-code": {"config_key": "mcpServers", "transport": TRANSPORT_HTTP},
    "cursor": {"config_key": "mcpServers", "transport": TRANSPORT_HTTP},
    "windsurf": {"config_key": "mcpServers", "transport": TRANSPORT_HTTP},
    "vscode": {"config_key": "servers", "transport": TRANSPORT_HTTP},
    "opencode": {"config_key": "mcp", "transport": TRANSPORT_HTTP},
    "kilo": {"config_key": "mcp", "transport": TRANSPORT_HTTP},
    "codex": {"config_key": "mcp_servers", "transport": TRANSPORT_HTTP, "config_format": "toml"},
}


def get_client_config_path(client: str) -> Path:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'. Must be one of {sorted(SUPPORTED_CLIENTS)}")

    if client == "claude-desktop":
        return Path(get_claude_desktop_config_path())

    if client == "claude-code":
        return Path.home() / ".claude.json"

    if client == "cursor":
        return Path.home() / ".cursor" / "mcp.json"

    if client == "windsurf":
        return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"

    if client == "vscode":
        return Path(str(user_data_dir("Code", appauthor=False, roaming=True))) / "User" / "mcp.json"

    if client == "opencode":
        return Path.home() / ".config" / "opencode" / "opencode.json"

    if client == "kilo":
        # Kilo deep-merges kilo.json over kilo.jsonc; always write the plain
        # JSON file so hand-written comments in kilo.jsonc are preserved.
        return Path.home() / ".config" / "kilo" / "kilo.json"

    if client == "codex":
        codex_home = os.environ.get("CODEX_HOME")
        return (Path(codex_home) if codex_home else Path.home() / ".codex") / "config.toml"

    raise ValueError(f"Unsupported client: '{client}'")


def _auth_headers(token: str) -> dict[str, str]:
    # TODO: drop the embedded token once anaconda.com/api/mcp advertises OAuth
    # protected-resource metadata and agents can run the OAuth flow themselves.
    return {"Authorization": f"Bearer {token}"}


def build_client_remote_config(client: str, url: str, token: str) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'")

    if SUPPORTED_CLIENTS[client]["transport"] != TRANSPORT_HTTP:
        raise ValueError(f"'{client}' does not support remote MCP servers in its config file.")

    if client == "codex":
        raise ValueError("'codex' uses TOML configuration; build its entry with tomlkit in configure_client.")

    headers = _auth_headers(token)

    if client == "claude-code":
        return {"type": "http", "url": url, "headers": headers}

    if client == "cursor":
        return {"url": url, "headers": headers}

    if client == "windsurf":
        return {"serverUrl": url, "headers": headers}

    if client == "vscode":
        return {"type": "http", "url": url, "headers": headers}

    return {
        "type": "remote",
        "url": url,
        "enabled": True,
        "headers": headers,
    }


def _load_toml_config(config_path: Path) -> Any:
    if not config_path.exists():
        return tomlkit.document()
    try:
        return tomlkit.parse(config_path.read_text(encoding="utf-8"))
    except Exception:
        return tomlkit.document()


def _save_toml_config(config_path: Path, doc: Any) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def _build_codex_remote_entry(url: str, token: str) -> Any:
    entry = tomlkit.table()
    entry["url"] = url
    headers = tomlkit.table()
    for key, value in _auth_headers(token).items():
        headers[key] = value
    entry["http_headers"] = headers
    return entry


def get_client_entry(
    client: str,
    server_name: str = "anaconda-mcp",
    config_path: Path | None = None,
) -> dict[str, Any] | None:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'. Must be one of {sorted(SUPPORTED_CLIENTS)}")

    if config_path is None:
        config_path = get_client_config_path(client)

    if not config_path.exists():
        return None

    config_key = SUPPORTED_CLIENTS[client]["config_key"]

    if client == "codex":
        servers = _load_toml_config(config_path).get(config_key, {})
        entry = servers.get(server_name)
        return dict(entry) if entry is not None else None

    config = load_config(config_path)
    entry = config.get(config_key, {}).get(server_name)
    return dict(entry) if isinstance(entry, dict) else None


def is_client_installed(
    client: str,
    server_name: str = "anaconda-mcp",
    config_path: Path | None = None,
) -> bool:
    return get_client_entry(client, server_name=server_name, config_path=config_path) is not None


def client_needs_update(
    client: str,
    server_name: str = "anaconda-mcp",
    config_path: Path | None = None,
) -> bool:
    """True when an entry exists but is not the desired configuration (e.g. legacy stdio)."""
    entry = get_client_entry(client, server_name=server_name, config_path=config_path)
    if entry is None:
        return False
    if SUPPORTED_CLIENTS[client]["transport"] == TRANSPORT_STDIO:
        return False
    return "url" not in entry and "serverUrl" not in entry


def configure_client(
    client: str,
    config_path: Path | None = None,
    server_name: str = "anaconda-mcp",
    backup: bool = True,
    token: str | None = None,
) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'")

    if client == "claude-desktop":
        claude_result: dict[str, Any] = configure_claude_desktop(
            config_path=config_path,
            server_name=server_name,
            backup=backup,
            force=True,
        )
        claude_result["client"] = client
        return claude_result

    if not token:
        raise ValueError(f"An authentication token is required to configure '{client}'.")

    if config_path is None:
        config_path = get_client_config_path(client)

    config_key = SUPPORTED_CLIENTS[client]["config_key"]

    result: dict[str, Any] = {
        "client": client,
        "config_path": config_path,
        "backup_path": None,
        "server_name": server_name,
        "transport": TRANSPORT_HTTP,
        "created": not config_path.exists(),
        "updated": False,
    }

    if backup:
        result["backup_path"] = backup_config_file(config_path)

    if client == "codex":
        doc = _load_toml_config(config_path)
        if config_key not in doc:
            doc[config_key] = tomlkit.table()
        servers = doc[config_key]
        if server_name in servers:
            result["updated"] = True
        servers[server_name] = _build_codex_remote_entry(REMOTE_MCP_URL, token)
        _save_toml_config(config_path, doc)
        return result

    config = load_config(config_path)

    if config_key not in config:
        config[config_key] = {}

    if server_name in config[config_key]:
        result["updated"] = True

    config[config_key][server_name] = build_client_remote_config(client, REMOTE_MCP_URL, token)

    save_config(config_path, config)

    return cast(dict[str, Any], result)


def remove_client(
    client: str,
    config_path: Path | None = None,
    server_name: str = "anaconda-mcp",
    backup: bool = True,
) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: '{client}'")

    if client == "claude-desktop":
        claude_result: dict[str, Any] = remove_claude_desktop_config(
            config_path=config_path,
            server_name=server_name,
            backup=backup,
        )
        claude_result["client"] = client
        return claude_result

    if config_path is None:
        config_path = get_client_config_path(client)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config_key = SUPPORTED_CLIENTS[client]["config_key"]

    result: dict[str, Any] = {
        "client": client,
        "config_path": config_path,
        "backup_path": None,
        "server_name": server_name,
        "removed": False,
    }

    if backup:
        result["backup_path"] = backup_config_file(config_path)

    if client == "codex":
        doc = _load_toml_config(config_path)
        servers = doc.get(config_key, {})
        if server_name not in servers:
            raise KeyError(f"Server '{server_name}' not found in {client} config.")
        del servers[server_name]
        _save_toml_config(config_path, doc)
        result["removed"] = True
        return result

    config = load_config(config_path)

    if config_key not in config or server_name not in config[config_key]:
        raise KeyError(f"Server '{server_name}' not found in {client} config.")

    del config[config_key][server_name]
    result["removed"] = True

    save_config(config_path, config)

    return cast(dict[str, Any], result)

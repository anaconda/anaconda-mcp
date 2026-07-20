import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATE_PATH = Path("~/.anaconda/mcp_state.json").expanduser()


class StateKeys:
    FIRST_INSTALL_AT = "first_install_at"
    INSTALL_ID = "install_id"


class MCPState:
    def __init__(self, path: Path | None = None):
        self._path = path if path is not None else _STATE_PATH

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self._path.read_text())
            if isinstance(data, dict):
                return data
            return {}
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Error reading MCP state: {e}")
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data))
        except OSError as e:
            logger.warning(f"Failed to write MCP state: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._read().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)


def is_new_install() -> bool:
    return MCPState().get(StateKeys.FIRST_INSTALL_AT) is None


def mark_installed() -> None:
    state = MCPState()
    if state.get(StateKeys.FIRST_INSTALL_AT) is None:
        state.set(StateKeys.FIRST_INSTALL_AT, datetime.now(timezone.utc).isoformat())


_install_id: str | None = None


def _reset_install_id_cache() -> None:
    """Test hook: clear the memoized install id."""
    global _install_id
    _install_id = None


def get_or_create_install_id() -> str:
    """Return a stable per-install UUID, read once per process then cached.

    Best-effort telemetry join key: no locking, so racing cold starts may pick
    different ids (last write wins). Never raises. No re-entrancy guard needed —
    _UserContextLogFilter carries only user.id, so nothing re-enters this.
    """
    global _install_id
    if _install_id is not None:
        return _install_id
    new_id = str(uuid.uuid4())
    try:
        state = MCPState()
        existing = state.get(StateKeys.INSTALL_ID)
        if isinstance(existing, str) and existing:
            new_id = existing
        else:
            state.set(StateKeys.INSTALL_ID, new_id)
    except Exception as e:
        logger.debug(f"Failed to resolve/persist install id, using ephemeral value: {e}")
    _install_id = new_id
    return _install_id

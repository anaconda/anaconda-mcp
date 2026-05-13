import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATE_PATH = Path("~/.anaconda/mcp_state.json").expanduser()


class StateKeys:
    FIRST_INSTALL_AT = "first_install_at"


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

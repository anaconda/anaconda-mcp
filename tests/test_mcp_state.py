import json
import uuid
from unittest import mock

import pytest

from anaconda_mcp.mcp_state import MCPState, StateKeys, _reset_install_id_cache, get_or_create_install_id


@pytest.fixture(autouse=True)
def _clean_install_id_memo():
    """Every test starts and ends with a cleared in-process memo."""
    _reset_install_id_cache()
    yield
    _reset_install_id_cache()


@pytest.fixture
def temp_state_path(tmp_path, monkeypatch):
    """Redirect the module-level state path so tests never touch the real state file."""
    path = tmp_path / "mcp_state.json"
    monkeypatch.setattr("anaconda_mcp.mcp_state._STATE_PATH", path)
    return path


def test_get_or_create_install_id_memo_avoids_extra_reads(temp_state_path):
    # Given - the id has already been resolved once
    get_or_create_install_id()

    # When - calling it several more times with _read spied on
    with mock.patch.object(MCPState, "_read", autospec=True, wraps=MCPState._read) as read_spy:
        for _ in range(5):
            get_or_create_install_id()

        # Then - the memo short-circuits; no additional reads occur
        assert read_spy.call_count == 0


def test_get_or_create_install_id_warm_path_reads_once_no_write(temp_state_path):
    # Given - a state file that already has an install_id persisted directly
    pre_existing = str(uuid.uuid4())
    MCPState(path=temp_state_path).set(StateKeys.INSTALL_ID, pre_existing)
    _reset_install_id_cache()

    # When - resolving with read/write spied on
    with (
        mock.patch.object(MCPState, "_read", autospec=True, wraps=MCPState._read) as read_spy,
        mock.patch.object(MCPState, "_write", autospec=True, wraps=MCPState._write) as write_spy,
    ):
        result = get_or_create_install_id()

        # Then - exactly one read, zero writes, and the pre-existing value wins
        assert read_spy.call_count == 1
        assert write_spy.call_count == 0
    assert result == pre_existing


def test_get_or_create_install_id_persists_and_is_idempotent_across_resets(temp_state_path):
    # Given - no pre-existing install_id (cold path generates + persists one)
    first = get_or_create_install_id()
    _reset_install_id_cache()

    # When - resolving again against the same state file after a memo reset
    second = get_or_create_install_id()

    # Then - the second call adopts the exact value the first call persisted
    assert second == first
    on_disk = json.loads(temp_state_path.read_text())
    assert on_disk[StateKeys.INSTALL_ID] == first


@pytest.mark.parametrize("broken_method", ["_read", "_write"])
def test_get_or_create_install_id_returns_valid_uuid_when_state_io_fails(temp_state_path, broken_method):
    # Given - the state layer raises on read or on write
    with mock.patch.object(MCPState, broken_method, autospec=True, side_effect=OSError("io failure")):
        # When - resolving on a fresh memo
        result = get_or_create_install_id()

    # Then - a valid UUID is still returned; nothing propagates
    assert uuid.UUID(result)

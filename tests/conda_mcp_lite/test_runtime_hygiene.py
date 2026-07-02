from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

import pytest

from anaconda_mcp.conda_mcp_lite import server


def _envelope(result):
    sc = result.structured_content
    assert sc is not None, "tool returned no structured_content"
    return sc


@pytest.mark.asyncio
async def test_list_environments_offloads_conda_info_from_main_thread(monkeypatch):
    ran_on_main_thread: list[bool] = []

    def _fake_info():
        ran_on_main_thread.append(threading.current_thread() is threading.main_thread())
        return {"root_prefix": "/opt/conda", "envs": ["/opt/conda"]}

    monkeypatch.setattr(server, "get_conda_info", _fake_info)

    result = _envelope(await server.mcp.call_tool("list_environments", {}))

    assert result["is_error"] is False
    assert ran_on_main_thread == [False]


@pytest.mark.asyncio
async def test_run_conda_offloads_lazy_conda_discovery_from_main_thread(monkeypatch):
    ran_on_main_thread: list[bool] = []

    def _fake_ensure_conda_exe():
        ran_on_main_thread.append(threading.current_thread() is threading.main_thread())
        server._conda_exe = Path("/fake/conda")

    class _FakeProc:
        async def communicate(self):
            return (b"{}", b"")

    async def _fake_exec(*cmd, stdout=None, stderr=None):
        return _FakeProc()

    monkeypatch.setattr(server, "_ensure_conda_exe", _fake_ensure_conda_exe)
    monkeypatch.setattr(server.asyncio, "create_subprocess_exec", _fake_exec)

    assert await server.run_conda("info") == {}
    assert ran_on_main_thread == [False]


def test_module_logger_uses_stderr_without_root_propagation():
    assert server.logger.propagate is False
    assert any(
        isinstance(handler, logging.StreamHandler) and handler.stream is sys.stderr
        for handler in server.logger.handlers
    )

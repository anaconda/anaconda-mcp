from __future__ import annotations

import threading
from pathlib import Path

import pytest

from anaconda_mcp.conda_mcp_lite import server


def _envelope(result):
    sc = result.structured_content
    assert sc is not None, "tool returned no structured_content"
    return sc


async def _scenario_list_environments(monkeypatch, record):
    def _fake_info():
        record()
        return {"root_prefix": "/opt/conda", "envs": ["/opt/conda"]}

    monkeypatch.setattr(server, "get_conda_info", _fake_info)
    result = _envelope(await server.mcp.call_tool("list_environments", {}))
    assert result["is_error"] is False


async def _scenario_run_conda(monkeypatch, record):
    def _fake_ensure_conda_exe():
        record()
        server._conda_exe = Path("/fake/conda")

    class _FakeProc:
        returncode = 0

        async def communicate(self):
            return (b"{}", b"")

    async def _fake_exec(*cmd, stdout=None, stderr=None):
        return _FakeProc()

    monkeypatch.setattr(server, "_ensure_conda_exe", _fake_ensure_conda_exe)
    monkeypatch.setattr(server.asyncio, "create_subprocess_exec", _fake_exec)
    assert await server.run_conda("info") == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(_scenario_list_environments, id="list_environments->get_conda_info"),
        pytest.param(_scenario_run_conda, id="run_conda->lazy_discovery"),
    ],
)
async def test_blocking_work_runs_off_main_thread(scenario, monkeypatch):
    ran_on_main_thread: list[bool] = []

    def _record():
        ran_on_main_thread.append(threading.current_thread() is threading.main_thread())

    await scenario(monkeypatch, _record)
    assert ran_on_main_thread == [False]

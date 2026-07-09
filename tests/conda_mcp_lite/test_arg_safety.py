"""Hermetic argument-injection safety tests for the vendored conda server.

Locks in the fix for the argument-injection vulnerability (review blocking #3).
These do NOT require a real conda install: ``run_conda`` /
``create_subprocess_exec`` are monkeypatched, so they run everywhere (unlike
``test_mutating_tools.py`` which is conda-gated).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anaconda_mcp.conda_mcp_lite import server


def _envelope(result):
    sc = result.structured_content
    assert sc is not None, "tool returned no structured_content"
    return sc


@pytest.fixture
def recorded_run_conda(monkeypatch):
    """Replace run_conda with a recorder so no real conda is invoked."""
    calls: list[dict] = []

    async def _recorder(*args, positionals=None):
        calls.append({"args": list(args), "positionals": positionals})
        return {"message": "ok", "prefix": "/tmp/fake-env"}

    monkeypatch.setattr(server, "run_conda", _recorder)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["-c", "--channel=https://evil/t/TOK/ch", "-y"])
async def test_install_packages_rejects_option_like_package(recorded_run_conda, bad):
    """An option-like package spec is rejected and conda is never invoked."""
    result = _envelope(
        await server.mcp.call_tool("install_packages", {"environment": "e", "packages": [bad, "realpkg"]})
    )
    assert result["is_error"] is True
    assert bad in result["error_description"]
    assert recorded_run_conda == [], "run_conda must NOT run when a package spec is option-like"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool,args",
    [
        ("create_environment", {"environment_name": "-n"}),
        ("install_packages", {"prefix": "-p", "packages": ["numpy"]}),
        ("remove_packages", {"environment": "-x", "packages": ["numpy"]}),
        ("remove_environment", {"environment_name": "-x"}),
        ("list_environment_packages", {"environment": "--bad"}),
    ],
)
async def test_tools_reject_option_like_env_or_prefix(recorded_run_conda, tool, args):
    """Option-like environment names / prefixes are rejected before exec."""
    result = _envelope(await server.mcp.call_tool(tool, args))
    assert result["is_error"] is True
    assert recorded_run_conda == [], f"{tool}: run_conda must NOT run on option-like input"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool,args",
    [
        ("create_environment", {"environment_name": "e"}),
        ("install_packages", {"environment": "e", "packages": ["numpy"]}),
    ],
)
async def test_tools_reject_option_like_channel(recorded_run_conda, tool, args):
    """An option-like channel value is rejected before conda runs."""
    result = _envelope(await server.mcp.call_tool(tool, {**args, "channels": ["--use-local"]}))
    assert result["is_error"] is True
    assert "--use-local" in result["error_description"]
    assert recorded_run_conda == [], f"{tool}: run_conda must NOT run on option-like channel"


@pytest.mark.asyncio
async def test_run_conda_places_json_before_separator(monkeypatch):
    """``--json`` must precede the ``--`` separator, else conda treats it as a package spec."""
    captured: dict = {}

    class _FakeProc:
        returncode = 0

        async def communicate(self):
            return (b'{"ok": true}', b"")

    async def _fake_exec(*cmd, stdin=None, stdout=None, stderr=None):
        captured["cmd"] = list(cmd)
        return _FakeProc()

    monkeypatch.setattr(server, "_conda_exe", Path("/x/conda"))
    monkeypatch.setattr(server.asyncio, "create_subprocess_exec", _fake_exec)

    out = await server.run_conda("install", "-y", "-n", "e", positionals=["numpy", "pandas"])
    assert out == {"ok": True}
    # cmd[0] is the platform-rendered conda path; the point of this test is the
    # argument ordering — `--json` before the `--` separator, positionals after.
    assert captured["cmd"][0] == str(server._conda_exe)
    assert captured["cmd"][1:] == ["install", "-y", "-n", "e", "--json", "--", "numpy", "pandas"]


@pytest.mark.asyncio
async def test_run_conda_empty_stdout_with_success_returncode_returns_empty(monkeypatch):
    """rc=0 + empty stdout (e.g. ``remove --all`` on a package-less env) is success, not an error."""

    class _FakeProc:
        returncode = 0

        async def communicate(self):
            return (b"", b"")

    async def _fake_exec(*cmd, stdin=None, stdout=None, stderr=None):
        return _FakeProc()

    monkeypatch.setattr(server, "_conda_exe", Path("/x/conda"))
    monkeypatch.setattr(server.asyncio, "create_subprocess_exec", _fake_exec)

    assert await server.run_conda("remove", "--all", "-y", "-n", "e") == {}


@pytest.mark.asyncio
async def test_run_conda_empty_stdout_with_failure_returncode_raises(monkeypatch):
    """rc!=0 + empty stdout is a real failure -> RuntimeError carrying stderr."""

    class _FakeProc:
        returncode = 1

        async def communicate(self):
            return (b"", b"boom")

    async def _fake_exec(*cmd, stdin=None, stdout=None, stderr=None):
        return _FakeProc()

    monkeypatch.setattr(server, "_conda_exe", Path("/x/conda"))
    monkeypatch.setattr(server.asyncio, "create_subprocess_exec", _fake_exec)

    with pytest.raises(RuntimeError, match="conda failed"):
        await server.run_conda("remove", "--all", "-y", "-n", "e")


@pytest.mark.asyncio
async def test_install_packages_happy_path_uses_positionals(recorded_run_conda):
    """A normal install passes packages as positionals (after --), not spliced into args."""
    result = _envelope(await server.mcp.call_tool("install_packages", {"environment": "e", "packages": ["numpy"]}))
    assert result["is_error"] is False
    assert len(recorded_run_conda) == 1
    assert recorded_run_conda[0]["positionals"] == ["numpy"]
    assert "numpy" not in recorded_run_conda[0]["args"], "packages must not be spliced into conda args"


@pytest.mark.asyncio
async def test_channel_params_always_exposed():
    """create_environment / install_packages always advertise channels and
    override_channels (parity with environments-mcp; no governance gating)."""
    tools_by_name = {t.name: t for t in await server.mcp.list_tools()}
    for tool_name in ("create_environment", "install_packages"):
        properties = tools_by_name[tool_name].parameters["properties"]
        assert "channels" in properties, f"{tool_name}: 'channels' not exposed"
        assert "override_channels" in properties, f"{tool_name}: 'override_channels' not exposed"

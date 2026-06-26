"""Hermetic option-injection safety tests for the vendored conda server.

Locks in the fix for the channel-governance bypass / argument-injection
vulnerability (review blocking #3). These do NOT require a real conda install:
``run_conda`` / ``create_subprocess_exec`` are monkeypatched, so they run
everywhere (unlike ``test_mutating_tools.py`` which is conda-gated).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
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
async def test_run_conda_places_json_before_separator(monkeypatch):
    """``--json`` must precede the ``--`` separator, else conda treats it as a package spec."""
    captured: dict = {}

    class _FakeProc:
        async def communicate(self):
            return (b'{"ok": true}', b"")

    async def _fake_exec(*cmd, stdout=None, stderr=None):
        captured["cmd"] = list(cmd)
        return _FakeProc()

    monkeypatch.setattr(server, "_conda_exe", Path("/x/conda"))
    monkeypatch.setattr(server.asyncio, "create_subprocess_exec", _fake_exec)

    out = await server.run_conda("install", "-y", "-n", "e", positionals=["numpy", "pandas"])
    assert out == {"ok": True}
    assert captured["cmd"] == ["/x/conda", "install", "-y", "-n", "e", "--json", "--", "numpy", "pandas"]


@pytest.mark.asyncio
async def test_install_packages_happy_path_uses_positionals(recorded_run_conda):
    """A normal install passes packages as positionals (after --), not spliced into args."""
    result = _envelope(await server.mcp.call_tool("install_packages", {"environment": "e", "packages": ["numpy"]}))
    assert result["is_error"] is False
    assert len(recorded_run_conda) == 1
    assert recorded_run_conda[0]["positionals"] == ["numpy"]
    assert "numpy" not in recorded_run_conda[0]["args"], "packages must not be spliced into conda args"


_FLAG_ON_CHANNEL_REJECT_PROBE = """
import asyncio
import json

from anaconda_mcp.conda_mcp_lite import server as s


async def main():
    result = await s.mcp.call_tool(
        "install_packages",
        {"environment": "e", "packages": ["numpy"], "channels": ["--use-local"], "override_channels": True},
    )
    print(json.dumps(result.structured_content))


asyncio.run(main())
"""


def test_flag_on_registered_tool_rejects_option_like_channel():
    """With ANACONDA_MCP_ALLOW_CHANNEL_OVERRIDE set, the *registered* install_packages tool
    exposes channels AND validates them — an option-like channel is rejected before conda runs.
    A subprocess is required because the flag is read at module import."""
    env = os.environ.copy()
    env["ANACONDA_MCP_ALLOW_CHANNEL_OVERRIDE"] = "true"
    proc = subprocess.run(
        [sys.executable, "-c", _FLAG_ON_CHANNEL_REJECT_PROBE],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        check=True,
    )
    parsed = json.loads(proc.stdout.strip().splitlines()[-1])
    assert parsed["is_error"] is True
    assert "--use-local" in parsed["error_description"]

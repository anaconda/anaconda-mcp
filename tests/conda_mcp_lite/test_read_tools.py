"""Read-tool coverage for the vendored ``anaconda_mcp.conda_mcp_lite`` server.

Exercises ``list_environments`` and ``list_environment_packages`` against
the real local conda via FastMCP's in-process ``call_tool``. Tools return
a ``ToolResult`` whose ``.structured_content`` is the
``{is_error, error_description, tool_result}`` envelope.

A session-scoped fixture initializes module-level discovery globals
(``_conda_exe``/``_conda_info``) that the tools rely on; without it
``run_conda``/``get_conda_info`` would see ``None`` and crash.

The tests intentionally do NOT spawn ``python -m anaconda_mcp.conda_mcp_lite``
as a subprocess — that entrypoint blocks on stdin forever (stdio JSON-RPC).
"""

from __future__ import annotations

import os
import shutil

import pytest

from anaconda_mcp.conda_mcp_lite import server

CONDA_EXE = os.environ.get("CONDA_EXE") or shutil.which("conda")

pytestmark = pytest.mark.skipif(CONDA_EXE is None, reason="No conda installation found on PATH or via CONDA_EXE")


@pytest.fixture(scope="module", autouse=True)
def _init_conda_discovery():
    """Populate module globals once per test module (read-only ops, fast)."""
    server._conda_exe = server.find_conda_exe()
    server._conda_info = server.get_conda_info()
    yield


def _envelope(result):
    """Extract the ``{is_error, error_description, tool_result}`` dict."""
    sc = result.structured_content
    assert sc is not None, "FastMCP tool returned no structured_content"
    return sc


@pytest.mark.asyncio
async def test_list_environments_includes_base_with_name_and_path():
    result = await server.mcp.call_tool("list_environments", {})
    env = _envelope(result)

    assert env["is_error"] is False, env["error_description"]
    environments = env["tool_result"]["environments"]
    assert isinstance(environments, list) and environments, "expected non-empty environments list"

    base_entries = [e for e in environments if e.get("name") == "base"]
    assert len(base_entries) == 1, f"expected exactly one 'base' entry, got: {[e.get('name') for e in environments]}"
    base = base_entries[0]
    assert "path" in base and base["path"], "base entry missing 'path'"
    assert os.path.isdir(base["path"]), f"base path does not exist: {base['path']}"


@pytest.mark.asyncio
async def test_list_environment_packages_by_environment_name():
    result = await server.mcp.call_tool("list_environment_packages", {"environment": "base"})
    env = _envelope(result)

    assert env["is_error"] is False, env["error_description"]
    packages = env["tool_result"]["packages"]
    assert isinstance(packages, list) and packages, "expected non-empty packages list for base"

    pkg = packages[0]
    assert set(pkg.keys()) == {"name", "version", "channel"}, (
        f"expected exactly name/version/channel keys, got: {sorted(pkg.keys())}"
    )
    assert pkg["name"] and pkg["version"], "package entries must have non-empty name and version"


@pytest.mark.asyncio
async def test_list_environment_packages_by_prefix():
    root_prefix = server.get_conda_info()["root_prefix"]
    result = await server.mcp.call_tool("list_environment_packages", {"prefix": root_prefix})
    env = _envelope(result)

    assert env["is_error"] is False, env["error_description"]
    packages = env["tool_result"]["packages"]
    assert isinstance(packages, list) and packages, "expected non-empty packages list for root prefix"
    assert all({"name", "version", "channel"} <= set(p.keys()) for p in packages)


@pytest.mark.asyncio
async def test_list_environment_packages_missing_selector_returns_error():
    """Neither ``prefix`` nor ``environment`` -> structured error, no exception leak."""
    result = await server.mcp.call_tool("list_environment_packages", {})
    env = _envelope(result)

    assert env["is_error"] is True, "expected is_error=True when no selector provided"
    assert env["tool_result"] is None
    msg = env["error_description"]
    assert msg, "expected non-empty error_description"
    # The tool's literal message; assert key terms so the user gets actionable guidance.
    assert "environment" in msg.lower() or "prefix" in msg.lower(), (
        f"error_description should reference 'environment' or 'prefix': {msg!r}"
    )

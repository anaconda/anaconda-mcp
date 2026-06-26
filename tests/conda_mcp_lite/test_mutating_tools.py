"""Mutating-tool coverage for the vendored ``anaconda_mcp.conda_mcp_lite`` server.

Lifecycle: ``create_environment`` -> ``install_packages`` -> ``list_environment_packages``
shows it -> ``remove_packages`` -> ``remove_environment``. Every step asserts
``is_error is False`` and the env is gone at the end. ``remove_packages`` is
explicitly covered (highest-risk previously-untested tool, Metis E9).

Each test runs in a uuid-suffixed env with guaranteed teardown so a failure
mid-test never leaves a conda env behind.

The tests intentionally do NOT spawn ``python -m anaconda_mcp.conda_mcp_lite``
as a subprocess — that entrypoint blocks on stdin forever (stdio JSON-RPC).
Tools are driven in-process via ``server.mcp.call_tool(...)`` after the
module-global discovery cache (``_conda_exe`` / ``_conda_info``) is populated.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import uuid
from collections.abc import Iterator

import pytest

from anaconda_mcp.conda_mcp_lite import server

CONDA_EXE = os.environ.get("CONDA_EXE") or shutil.which("conda")

pytestmark = pytest.mark.skipif(CONDA_EXE is None, reason="No conda installation found on PATH or via CONDA_EXE")

# Generous-but-bounded per-call timeout. Cached conda solves typically finish
# in seconds; 120s is well above any realistic latency while still failing
# fast on a hung subprocess.
_TOOL_CALL_TIMEOUT_S = 120.0
_TEARDOWN_TIMEOUT_S = 180.0


@pytest.fixture(scope="module", autouse=True)
def _init_conda_discovery() -> Iterator[None]:
    """Populate module-global discovery cache once per test module.

    Tools call ``run_conda(...)`` which uses ``_conda_exe`` / ``_conda_info``;
    without this the first call would crash on ``str(None)``.
    """
    server._conda_exe = server.find_conda_exe()
    server._conda_info = server.get_conda_info()
    yield


def _force_remove_env(env_name: str) -> None:
    """Best-effort env teardown; never raises so failed tests still clean up."""
    conda_exe = str(server._conda_exe or CONDA_EXE or "conda")
    subprocess.run(
        [conda_exe, "env", "remove", "-y", "-n", env_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=_TEARDOWN_TIMEOUT_S,
        check=False,
    )


@pytest.fixture
def ephemeral_env_name() -> Iterator[str]:
    """Yield a uuid-suffixed env name; guarantee teardown even on failure."""
    name = f"amcp-mut-{uuid.uuid4().hex[:8]}"
    try:
        yield name
    finally:
        _force_remove_env(name)


def _envelope(result):
    """Extract the ``{is_error, error_description, tool_result}`` dict."""
    sc = result.structured_content
    assert sc is not None, "FastMCP tool returned no structured_content"
    return sc


async def _call(tool_name: str, args: dict):
    """Per-call timeout so a hung conda solve fails the test instead of stalling CI."""
    return await asyncio.wait_for(
        server.mcp.call_tool(tool_name, args),
        timeout=_TOOL_CALL_TIMEOUT_S,
    )


@pytest.mark.asyncio
async def test_full_lifecycle_create_install_remove_packages_remove_environment(
    ephemeral_env_name: str,
) -> None:
    """End-to-end cycle hitting every mutating tool plus list verification.

    Uses tiny, likely-cached packages (``pip`` then ``six``) to keep solves fast.
    Asserts ``is_error is False`` at every step and the env is truly gone at the end.
    """
    # 1. create_environment — single tiny, likely-cached package.
    create = _envelope(
        await _call(
            "create_environment",
            {"environment_name": ephemeral_env_name, "packages": ["pip"]},
        )
    )
    assert create["is_error"] is False, create["error_description"]
    assert create["tool_result"] is not None
    assert "prefix" in create["tool_result"], "create_environment missing prefix"

    # 2. install_packages — small, pure-Python, not a transitive dep of pip.
    install = _envelope(
        await _call(
            "install_packages",
            {"environment": ephemeral_env_name, "packages": ["six"]},
        )
    )
    assert install["is_error"] is False, install["error_description"]

    # 3. list_environment_packages — confirm 'six' is now installed.
    listed = _envelope(await _call("list_environment_packages", {"environment": ephemeral_env_name}))
    assert listed["is_error"] is False, listed["error_description"]
    pkg_names = {p["name"] for p in listed["tool_result"]["packages"]}
    assert "six" in pkg_names, f"six missing after install; got {sorted(pkg_names)}"

    # 4. remove_packages — explicitly cover the highest-risk previously-untested tool.
    removed_pkg = _envelope(
        await _call(
            "remove_packages",
            {"environment": ephemeral_env_name, "packages": ["six"]},
        )
    )
    assert removed_pkg["is_error"] is False, removed_pkg["error_description"]

    # Confirm the package is actually gone — guards against a "success" envelope
    # that didn't actually remove anything.
    listed_after = _envelope(await _call("list_environment_packages", {"environment": ephemeral_env_name}))
    assert listed_after["is_error"] is False, listed_after["error_description"]
    pkg_names_after = {p["name"] for p in listed_after["tool_result"]["packages"]}
    assert "six" not in pkg_names_after, "remove_packages reported success but 'six' still listed"

    # 5. remove_environment — final cleanup. Verify the env is truly gone.
    removed_env = _envelope(await _call("remove_environment", {"environment_name": ephemeral_env_name}))
    assert removed_env["is_error"] is False, removed_env["error_description"]

    envs = _envelope(await _call("list_environments", {}))
    env_names = {e["name"] for e in envs["tool_result"]["environments"]}
    assert ephemeral_env_name not in env_names, f"env {ephemeral_env_name!r} still listed after remove_environment"

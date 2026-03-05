"""
Regression tests: GUARD-001-API

Covers two bugs triggered by GUARD-001 Step 1
("Install nonexistent-package-xyz123 in guard-test"):

  ERR-003a  conda_install_packages returns a false "environment not found"
            when the environment exists but is addressed by name.

  ERR-003b  conda_install_packages hangs indefinitely when addressed by
            prefix and the package does not exist (the call never returns).

Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.

See tests/qa/api_tools/README.md for setup and usage.
"""

from __future__ import annotations

import logging
import subprocess

import httpx
import pytest

from common.constants.config import TOOL_TIMEOUT
from common.utils.conda_utils import _conda_env_prefix
from common.utils.mcp_client import _call_tool, _tool_result

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

ENV_NAME = "guard-api-test"
NONEXISTENT_PKG = "nonexistent-package-xyz123"


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _validate_package_resolution_error(result: dict, env_name: str) -> None:
    """
    Assert that the tool result describes a package-resolution failure,
    not a false 'environment not found'.

    ERR-003a: EnvironmentLocationNotFound was raised before the solver was
    reached, causing the response to misreport the environment as missing
    instead of the package.
    """
    error_desc = result.get("error_description", "").lower()

    if "environment was not found" in error_desc:
        raise AssertionError(
            f"False 'environment not found' for existing env '{env_name}'. "
            f"Bug: EnvironmentLocationNotFound raised before package resolution. "
            f"Full error_description: {result.get('error_description')!r}"
        )

    if "could not resolve the packages" not in error_desc:
        raise AssertionError(
            f"Expected 'Could not resolve the packages' (install_packages.py → "
            f"ResolvePackageNotFound), "
            f"got: {result.get('error_description')!r}"
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def conda_env():
    """Create the guard-api-test environment once for the module; remove it after."""
    logger.info("Creating conda environment '%s'", ENV_NAME)
    subprocess.run(
        ["conda", "create", "-n", ENV_NAME, "python=3.11", "-y"],
        check=True,
    )
    prefix = _conda_env_prefix(ENV_NAME)
    logger.debug("Conda env '%s' prefix: %s", ENV_NAME, prefix)
    yield {"name": ENV_NAME, "prefix": prefix}
    logger.info("Removing conda environment '%s'", ENV_NAME)
    subprocess.run(
        ["conda", "remove", "-n", ENV_NAME, "--all", "-y"],
        check=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.slow
class TestInstallNonexistentPackage:
    """
    Regression: conda_install_packages with a nonexistent package must return
    a proper error quickly — not hang and not misreport the environment.
    """

    def test_err_003a_by_name_error_description(self, conda_env, session_id):
        """
        ERR-003a: calling by environment name must report a package-resolution
        failure — not 'environment not found' — when the environment exists.

        Source:  install_packages.py catches conda.exceptions.ResolvePackageNotFound
                 and returns error_description = "Could not resolve the packages".
                 The bug causes EnvironmentLocationNotFound to be raised instead,
                 returning "The environment was not found." before ever reaching
                 the solver.

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info("ERR-003a: installing nonexistent pkg by env name '%s'", ENV_NAME)
        response = _call_tool(
            "conda_install_packages",
            {"environment": conda_env["name"], "packages": [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)
        _validate_package_resolution_error(result, conda_env["name"])

    def test_err_003a_by_name_returns_error(self, conda_env, session_id):
        """
        ERR-003a: calling by environment name must return is_error=true
        (package does not exist; no silent pip fallback).

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info("ERR-003a: verifying is_error flag for nonexistent pkg by env name")
        response = _call_tool(
            "conda_install_packages",
            {"environment": conda_env["name"], "packages": [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)

        assert result.get("is_error") is True, (
            f"Expected is_error=true for nonexistent package '{NONEXISTENT_PKG}', "
            f"got: {result}"
        )

    def test_err_003b_by_prefix_does_not_hang(self, conda_env, session_id):
        """
        ERR-003b: calling by prefix must return within TOOL_TIMEOUT seconds.
        A ReadTimeout here means the server hung (regression of the reported bug).

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info(
            "ERR-003b: installing nonexistent pkg by prefix '%s'", conda_env["prefix"]
        )
        try:
            response = _call_tool(
                "conda_install_packages",
                {"prefix": conda_env["prefix"], "packages": [NONEXISTENT_PKG]},
                session_id,
            )
        except httpx.ReadTimeout:
            logger.error(
                "Tool call timed out after %ss — regression of hang bug", TOOL_TIMEOUT
            )
            pytest.fail(
                f"conda_install_packages hung for >{TOOL_TIMEOUT}s when called with "
                f"prefix='{conda_env['prefix']}' and a nonexistent package. "
                "Regression of the install-nonexistent-pkg hang bug."
            )

        result = _tool_result(response)
        assert result.get("is_error") is True, (
            f"Expected is_error=true for nonexistent package '{NONEXISTENT_PKG}', "
            f"got: {result}"
        )

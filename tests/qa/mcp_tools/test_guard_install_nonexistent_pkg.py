"""
Regression tests: GUARD-001-API (KI-010)

Covers the confirmed defect in the conda sub-server's install_packages tool
(`anaconda_mcp.conda_mcp_lite`) triggered by
GUARD-001 Step 1 ("Install nonexistent-package-xyz123 in guard-test").

conda_install_packages(environment="<name>", packages=["nonexistent-pkg"])
returns "The environment was not found" even though the environment exists.

Root cause: anaconda_connector_conda creates a Context(search_path=()) for each
call. With an empty search path conda does not populate envs_dirs, so
context.target_prefix raises EnvironmentLocationNotFound before the solver is
invoked. install_packages.py:93 catches this and returns the wrong error.

Side-effect: the misleading error causes the LLM to list environments and retry
by prefix, producing extra tool calls.

See tests/qa/_ai_docs/KNOWN_ISSUES.md (KI-010) and README.md for setup.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.config import TOOL_CALL_WALL_SECONDS
from common.constants.mcp_tools import InstallPackagesArgs, Tools
from common.constants.test_data import NONEXISTENT_PKG
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import (
    _validate_is_error,
    _validate_package_resolution_error,
)

logger = logging.getLogger(__name__)

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

    def test_err_003a_by_name_error_description(self, conda_env, call_tool):
        """
        ERR-003a: calling by environment name must report a package-resolution
        failure — not 'environment not found' — when the environment exists.

        Source:  install_packages.py may normalize ResolvePackageNotFound to
                 "Could not resolve the packages", or conda may return channel
                 text (e.g. "not available from current channels"). The KI-010 bug
                 causes EnvironmentLocationNotFound to be raised instead, returning
                 "The environment was not found." before the solver.

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info("ERR-003a: installing nonexistent pkg by env name '%s'", conda_env["name"])
        response = call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.ENVIRONMENT: conda_env["name"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
        )
        result = _tool_result(response)
        _validate_package_resolution_error(result, conda_env["name"])

    @pytest.mark.timeout(TOOL_CALL_WALL_SECONDS + 15)
    def test_err_003b_by_prefix_does_not_hang(self, conda_env, call_tool):
        """
        ERR-003b: calling by prefix must return within the tools/call wall clock.

        ``pytest-timeout`` must exceed ``TOOL_CALL_WALL_SECONDS`` because ``_call_tool``
        can block the main thread on ``ThreadPoolExecutor.result`` while the worker
        reads the SSE body (up to that wall budget).

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info("ERR-003b: installing nonexistent pkg by prefix '%s'", conda_env["prefix"])
        response = call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.PREFIX: conda_env["prefix"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
        )
        result = _tool_result(response)
        _validate_is_error(result, f"nonexistent package '{NONEXISTENT_PKG}'")

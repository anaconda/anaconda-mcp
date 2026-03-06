"""
Regression tests: GUARD-001-API (KI-010)

Covers the confirmed defect in
environments_mcp_server/tools/environments/install_packages.py triggered by
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

from common.constants.config import TOOL_TIMEOUT
from common.constants.mcp_tools import InstallPackagesArgs, Tools
from common.constants.test_data import NONEXISTENT_PKG
from common.utils.mcp_client import _call_tool, _tool_result
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
        logger.info("ERR-003a: installing nonexistent pkg by env name '%s'", conda_env["name"])
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.ENVIRONMENT: conda_env["name"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
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
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.ENVIRONMENT: conda_env["name"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)

        _validate_is_error(result, f"nonexistent package '{NONEXISTENT_PKG}'")

    @pytest.mark.timeout(TOOL_TIMEOUT)
    def test_err_003b_by_prefix_does_not_hang(self, conda_env, session_id):
        """
        ERR-003b: calling by prefix must return within TOOL_TIMEOUT seconds.

        The timeout marker is the regression guard — if the server hangs, pytest
        kills the test and reports TIMEOUT instead of waiting until the SSE
        session expires (~5 min).

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor client.
        """
        logger.info(
            "ERR-003b: installing nonexistent pkg by prefix '%s'", conda_env["prefix"]
        )
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {InstallPackagesArgs.PREFIX: conda_env["prefix"], InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG]},
            session_id,
        )
        result = _tool_result(response)
        _validate_is_error(result, f"nonexistent package '{NONEXISTENT_PKG}'")


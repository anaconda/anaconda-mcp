"""
Happy-path tests for conda_install_packages with a real, existing package.

Covers the success path of conda_install_packages — the counterpart to
test_guard_install_nonexistent_pkg.py which only exercises the error path.

Tests verify:
- is_error=false when a valid package is installed by environment name
- is_error=false when a valid package is installed by prefix
- tool_result contains a non-empty message on success

Package under test: pyyaml — small, available in conda defaults, not
a default dependency of a bare python=3.11 environment.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import InstallPackagesArgs, Tools
from common.constants.test_data import EXISTING_PKG
from common.utils.mcp_client import _call_tool, _tool_result
from common.utils.response_validators import (
    _validate_install_has_message,
    _validate_install_success,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestInstallExistingPackage:
    """
    Happy-path: conda_install_packages with a valid package must succeed
    and return a non-empty message — addressed both by name and by prefix.
    """

    def test_install_by_name_is_not_error(self, conda_env, session_id):
        """
        Installing an existing package by environment name must return is_error=false.

        Verifies the basic success path: a real package, a real environment,
        addressed by name.  Failure here indicates a regression in the install
        path itself (e.g. environment lookup, solver, or response serialisation).
        """
        logger.info("Installing '%s' into env '%s' by name", EXISTING_PKG, conda_env["name"])
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {
                InstallPackagesArgs.ENVIRONMENT: conda_env["name"],
                InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
            },
            session_id,
        )
        result = _tool_result(response)
        _validate_install_success(result, context=f"env_name={conda_env['name']!r} pkg={EXISTING_PKG!r}")

    def test_install_by_name_has_message(self, conda_env, session_id):
        """
        A successful install by name must carry a non-empty tool_result.message.

        install_packages.py sets tool_result={"message": ...} on success.
        An absent or empty message signals an unexpected response shape.
        """
        logger.info(
            "Checking tool_result.message after installing '%s' into env '%s'",
            EXISTING_PKG,
            conda_env["name"],
        )
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {
                InstallPackagesArgs.ENVIRONMENT: conda_env["name"],
                InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
            },
            session_id,
        )
        result = _tool_result(response)
        _validate_install_success(result, context=f"env_name={conda_env['name']!r} pkg={EXISTING_PKG!r}")
        _validate_install_has_message(result, context=f"env_name={conda_env['name']!r} pkg={EXISTING_PKG!r}")

    def test_install_by_prefix_is_not_error(self, conda_env, session_id):
        """
        Installing an existing package by prefix must return is_error=false.

        Validates the prefix-based lookup path separately from the name-based
        path — they exercise different resolution logic inside install_packages.py.
        """
        logger.info(
            "Installing '%s' into env '%s' by prefix '%s'",
            EXISTING_PKG,
            conda_env["name"],
            conda_env["prefix"],
        )
        response = _call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {
                InstallPackagesArgs.PREFIX: conda_env["prefix"],
                InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
            },
            session_id,
        )
        result = _tool_result(response)
        _validate_install_success(result, context=f"prefix={conda_env['prefix']!r} pkg={EXISTING_PKG!r}")

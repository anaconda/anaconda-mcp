"""
Happy-path tests for conda_remove_packages tool.

Tests verify:
- is_error=false when removing a package by environment name
- is_error=false when removing a package by prefix

Note: This test installs a package first, then removes it to verify the remove path.
"""

from __future__ import annotations

import logging

import pytest
from common.constants.mcp_tools import (
    InstallPackagesArgs,
    RemovePackagesArgs,
    Tools,
)
from common.constants.test_data import EXISTING_PKG
from common.utils.mcp_client import _tool_result
from common.utils.response_validators import (
    _validate_install_success,
    validate_remove_success,
)

logger = logging.getLogger(__name__)


@pytest.mark.slow
class TestRemovePackages:
    """
    Happy-path: conda_remove_packages must succeed — addressed both by name and by prefix.
    """

    def test_remove_package_by_name(self, conda_env, call_tool):
        """
        Removing a package by environment name must return is_error=false.

        First installs a package, then removes it to verify the remove path works.
        """
        logger.info("Installing '%s' into env '%s' before removal test", EXISTING_PKG, conda_env["name"])
        install_response = call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {
                InstallPackagesArgs.ENVIRONMENT: conda_env["name"],
                InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
            },
        )
        install_result = _tool_result(install_response)
        _validate_install_success(install_result, context=f"env={conda_env['name']!r} pkg={EXISTING_PKG!r}")

        logger.info("Removing '%s' from env '%s' by name", EXISTING_PKG, conda_env["name"])
        response = call_tool(
            Tools.CONDA_REMOVE_PACKAGES,
            {
                RemovePackagesArgs.ENVIRONMENT: conda_env["name"],
                RemovePackagesArgs.PACKAGES: [EXISTING_PKG],
            },
        )
        result = _tool_result(response)
        validate_remove_success(result, context=f"env_name={conda_env['name']!r} pkg={EXISTING_PKG!r}")

    def test_remove_package_by_prefix(self, conda_env, call_tool):
        """
        Removing a package by prefix must return is_error=false.

        Validates the prefix-based lookup path separately from the name-based path.
        """
        logger.info(
            "Installing '%s' into env '%s' by prefix before removal test",
            EXISTING_PKG,
            conda_env["name"],
        )
        install_response = call_tool(
            Tools.CONDA_INSTALL_PACKAGES,
            {
                InstallPackagesArgs.PREFIX: conda_env["prefix"],
                InstallPackagesArgs.PACKAGES: [EXISTING_PKG],
            },
        )
        install_result = _tool_result(install_response)
        _validate_install_success(install_result, context=f"prefix={conda_env['prefix']!r} pkg={EXISTING_PKG!r}")

        logger.info(
            "Removing '%s' from env '%s' by prefix '%s'",
            EXISTING_PKG,
            conda_env["name"],
            conda_env["prefix"],
        )
        response = call_tool(
            Tools.CONDA_REMOVE_PACKAGES,
            {
                RemovePackagesArgs.PREFIX: conda_env["prefix"],
                RemovePackagesArgs.PACKAGES: [EXISTING_PKG],
            },
        )
        result = _tool_result(response)
        validate_remove_success(result, context=f"prefix={conda_env['prefix']!r} pkg={EXISTING_PKG!r}")

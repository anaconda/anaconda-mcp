"""
MCP tool names and their argument/result field keys.

Using str-based enums so values work directly as dict keys and JSON strings
without an explicit .value call.
"""

from __future__ import annotations

from enum import Enum


class Tools(str, Enum):
    CONDA_INSTALL_PACKAGES = "conda_install_packages"


class InstallPackagesArgs(str, Enum):
    ENVIRONMENT = "environment"
    PREFIX = "prefix"
    PACKAGES = "packages"


class ToolResultFields(str, Enum):
    IS_ERROR = "is_error"
    ERROR_DESCRIPTION = "error_description"

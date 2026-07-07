"""
MCP tool names and their argument/result field keys.

Using str-based enums so values work directly as dict keys and JSON strings
without an explicit .value call.
"""

from __future__ import annotations

from enum import Enum


class Tools(str, Enum):
    CONDA_CREATE_ENVIRONMENT = "conda_create_environment"
    CONDA_INSTALL_PACKAGES = "conda_install_packages"
    CONDA_LIST_ENVIRONMENTS = "conda_list_environments"
    CONDA_REMOVE_ENVIRONMENT = "conda_remove_environment"


class CreateEnvironmentArgs(str, Enum):
    ENVIRONMENT_NAME = "environment_name"
    PACKAGES = "packages"


class InstallPackagesArgs(str, Enum):
    ENVIRONMENT = "environment"
    PREFIX = "prefix"
    PACKAGES = "packages"


class RemoveEnvironmentArgs(str, Enum):
    ENVIRONMENT_NAME = "environment_name"
    PREFIX = "prefix"


class ToolResultFields(str, Enum):
    IS_ERROR = "is_error"
    ERROR_DESCRIPTION = "error_description"
    TOOL_RESULT = "tool_result"

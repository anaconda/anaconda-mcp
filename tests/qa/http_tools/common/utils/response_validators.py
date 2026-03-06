"""
Response validators for the http_tools suite.

Each validator checks one specific property of a tool result dict.
Validators return nothing and raise AssertionError with context on failure.
"""

from __future__ import annotations

from common.constants.mcp_tools import ToolResultFields


def _validate_is_error(result: dict, context: str = "") -> None:
    """
    Assert that the tool result has is_error=true.

    Raises AssertionError with the context string and the actual result if not.
    """
    if result.get(ToolResultFields.IS_ERROR) is not True:
        parts = ["Expected is_error=true"]
        if context:
            parts.append(context)
        parts.append(f"got: {result!r}")
        raise AssertionError(" — ".join(parts))


def _validate_package_resolution_error(result: dict, env_name: str) -> None:
    """
    Assert that the tool result describes a package-resolution failure,
    not a false 'environment not found'.

    ERR-003a: EnvironmentLocationNotFound was raised before the solver was
    reached, causing the response to misreport the environment as missing
    instead of the package.
    """
    error_desc = result.get(ToolResultFields.ERROR_DESCRIPTION, "").lower()

    if "environment was not found" in error_desc:
        raise AssertionError(
            f"False 'environment not found' for existing env '{env_name}'. "
            f"Bug: EnvironmentLocationNotFound raised before package resolution. "
            f"Full error_description: {result.get(ToolResultFields.ERROR_DESCRIPTION)!r}"
        )

    if "could not resolve the packages" not in error_desc:
        raise AssertionError(
            f"Expected 'Could not resolve the packages' (install_packages.py → "
            f"ResolvePackageNotFound), "
            f"got: {result.get(ToolResultFields.ERROR_DESCRIPTION)!r}"
        )

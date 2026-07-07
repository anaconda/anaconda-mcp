"""
Response validators for the mcp_tools suite.

Each validator checks one specific property of a tool result dict.
Validators return nothing and assert on failure.
"""

from __future__ import annotations

from common.constants.mcp_tools import ToolResultFields


def _validate_is_error(result: dict, context: str = "") -> None:
    """Assert that the tool result has is_error=true."""
    parts = ["Expected is_error=true"]
    if context:
        parts.append(context)
    parts.append(f"got: {result!r}")
    assert result.get(ToolResultFields.IS_ERROR) is True, " — ".join(parts)


def _validate_install_success(result: dict, context: str = "") -> None:
    """
    Assert that the tool result represents a successful package installation.

    Checks is_error is falsy. A truthy is_error means conda refused or failed
    the install; the test should surface the error_description for diagnosis.
    """
    error_desc = result.get(ToolResultFields.ERROR_DESCRIPTION, "")
    parts = ["Expected is_error=false (successful install)"]
    if context:
        parts.append(context)
    if error_desc:
        parts.append(f"error_description: {error_desc!r}")
    parts.append(f"got: {result!r}")
    assert not result.get(ToolResultFields.IS_ERROR), " — ".join(parts)


def _validate_install_has_message(result: dict, context: str = "") -> None:
    """
    Assert that a successful install result carries a non-empty message.

    install_packages.py sets tool_result={"message": ...} on success.
    An empty or missing message suggests the response was parsed incorrectly
    or the server returned an unexpected shape.
    """
    tool_result = result.get(ToolResultFields.TOOL_RESULT, {})
    parts = ["Expected tool_result.message to be present and non-empty"]
    if context:
        parts.append(context)
    parts.append(f"tool_result={tool_result!r}")
    assert isinstance(tool_result, dict) and tool_result.get("message"), " — ".join(parts)


def _looks_like_conda_package_resolution_error(error_desc_lower: str) -> bool:
    """
    True if the text clearly indicates the solver could not satisfy the package
    spec (not only install_packages.py's ResolvePackageNotFound wrapper string).

    Conda may surface e.g. ``PackagesNotFoundError`` / channel text such as
    "The following packages are not available from current channels" instead of
    the normalized "Could not resolve the packages" message.
    """
    return any(
        [
            "could not resolve the packages" in error_desc_lower,
            "not available from current channels" in error_desc_lower,
            "packages are not available" in error_desc_lower,
            "no packages found" in error_desc_lower,
        ]
    )


def _validate_package_resolution_error(result: dict, env_name: str) -> None:
    """
    Assert that the tool result is an error describing a package-resolution
    failure, not a false 'environment not found'.

    Checks (in order):
    1. is_error=true — a package-resolution failure must be signalled as an error.
    2. error_description is not 'environment not found' (KI-010 regression guard).
    3. error_description matches a known conda package-resolution failure pattern.

    ERR-003a: EnvironmentLocationNotFound was raised before the solver was
    reached, causing the response to misreport the environment as missing
    instead of the package.

    Accepts either install_packages.py's ResolvePackageNotFound message or other
    conda solver/channel wording that still proves resolution failed (not env
    lookup).
    """
    assert result.get(ToolResultFields.IS_ERROR) is True, (
        f"Expected is_error=true for nonexistent package in env '{env_name}', got: {result!r}"
    )

    raw = result.get(ToolResultFields.ERROR_DESCRIPTION, "")
    error_desc = raw.lower()

    assert "environment was not found" not in error_desc, (
        f"False 'environment not found' for existing env '{env_name}'. "
        f"Bug: EnvironmentLocationNotFound raised before package resolution. "
        f"Full error_description: {raw!r}"
    )

    assert _looks_like_conda_package_resolution_error(error_desc), (
        "Expected a package-resolution failure "
        "(e.g. 'Could not resolve the packages' or conda 'not available from current channels'), "
        f"got: {raw!r}"
    )

"""
Response validators for the mcp_tools suite.

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


def _validate_no_pydantic_validation_error(
    result: dict,
    response: dict | None = None,
    context: str = "",
) -> None:
    """
    Assert that neither the parsed tool result nor the raw MCP response content
    contains a Pydantic frozen_instance validation error.

    KI-016: create_environment raised a frozen_instance ValidationError when
    environment_root_path was provided. The error propagates past the try/except
    block in create_environment.py (it is raised in get_conda_config() before the
    try block), so fastmcp catches it and returns the raw exception text as a
    plain-text content item — NOT as a JSON-wrapped tool result.

    This means _tool_result() returns {} (the text doesn't start with '{'), and
    checking only result["error_description"] misses the error entirely.
    This validator checks both:
      (a) result["error_description"] — for structured tool error results
      (b) all raw content text items in the MCP response — for unhandled exceptions
    """
    # (a) structured tool result error_description
    error_desc = result.get(ToolResultFields.ERROR_DESCRIPTION, "")

    # (b) raw content text items from the MCP response (catches unhandled exceptions)
    raw_texts: list[str] = []
    if response is not None:
        content = response.get("result", {}).get("content", [])
        raw_texts = [c.get("text", "") for c in content if c.get("type") == "text"]

    all_text = "\n".join([error_desc] + raw_texts)
    if "frozen_instance" in all_text or "Instance is frozen" in all_text:
        raise AssertionError(
            "Pydantic frozen_instance validation error in response (KI-016 regression). "
            + (f"Context: {context}. " if context else "")
            + f"error_description={error_desc!r}  raw_content_texts={raw_texts!r}"
        )


def _validate_install_success(result: dict, context: str = "") -> None:
    """
    Assert that the tool result represents a successful package installation.

    Checks is_error is falsy.  A truthy is_error means conda refused or failed
    the install; the test should surface the error_description for diagnosis.
    """
    if result.get(ToolResultFields.IS_ERROR):
        parts = ["Expected is_error=false (successful install)"]
        if context:
            parts.append(context)
        error_desc = result.get(ToolResultFields.ERROR_DESCRIPTION, "")
        if error_desc:
            parts.append(f"error_description: {error_desc!r}")
        parts.append(f"got: {result!r}")
        raise AssertionError(" — ".join(parts))


def _validate_install_has_message(result: dict, context: str = "") -> None:
    """
    Assert that a successful install result carries a non-empty message.

    install_packages.py sets tool_result={"message": ...} on success.
    An empty or missing message suggests the response was parsed incorrectly
    or the server returned an unexpected shape.
    """
    tool_result = result.get(ToolResultFields.TOOL_RESULT, {})
    if not isinstance(tool_result, dict) or not tool_result.get("message"):
        parts = ["Expected tool_result.message to be present and non-empty"]
        if context:
            parts.append(context)
        parts.append(f"tool_result={tool_result!r}")
        raise AssertionError(" — ".join(parts))


def _looks_like_conda_package_resolution_error(error_desc_lower: str) -> bool:
    """
    True if the text clearly indicates the solver could not satisfy the package
    spec (not only install_packages.py's ResolvePackageNotFound wrapper string).

    Conda may surface e.g. ``PackagesNotFoundError`` / channel text such as
    "The following packages are not available from current channels" instead of
    the normalized "Could not resolve the packages" message.
    """
    if "could not resolve the packages" in error_desc_lower:
        return True
    if "not available from current channels" in error_desc_lower:
        return True
    if "packages are not available" in error_desc_lower:
        return True
    if "no packages found" in error_desc_lower:
        return True
    return False


def _validate_package_resolution_error(result: dict, env_name: str) -> None:
    """
    Assert that the tool result describes a package-resolution failure,
    not a false 'environment not found'.

    ERR-003a: EnvironmentLocationNotFound was raised before the solver was
    reached, causing the response to misreport the environment as missing
    instead of the package.

    Accepts either install_packages.py's ResolvePackageNotFound message or other
    conda solver/channel wording that still proves resolution failed (not env
    lookup).
    """
    raw = result.get(ToolResultFields.ERROR_DESCRIPTION, "")
    error_desc = raw.lower()

    if "environment was not found" in error_desc:
        raise AssertionError(
            f"False 'environment not found' for existing env '{env_name}'. "
            f"Bug: EnvironmentLocationNotFound raised before package resolution. "
            f"Full error_description: {raw!r}"
        )

    if not _looks_like_conda_package_resolution_error(error_desc):
        raise AssertionError(
            "Expected a package-resolution failure "
            "(e.g. 'Could not resolve the packages' or conda 'not available from current channels'), "
            f"got: {raw!r}"
        )

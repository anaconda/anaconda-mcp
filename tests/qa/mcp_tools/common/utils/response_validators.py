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
    assert "frozen_instance" not in all_text and "Instance is frozen" not in all_text, (
        "Pydantic frozen_instance validation error in response (KI-016 regression). "
        + (f"Context: {context}. " if context else "")
        + f"error_description={error_desc!r}  raw_content_texts={raw_texts!r}"
    )


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


# =============================================================================
# environments-mcp validators (additional)
# =============================================================================


def validate_list_packages_success(result: dict, context: str = "") -> None:
    """Assert that conda_list_environment_packages returned success."""
    parts = ["Expected is_error=false (successful list packages)"]
    if context:
        parts.append(context)
    error_desc = result.get(ToolResultFields.ERROR_DESCRIPTION, "")
    if error_desc:
        parts.append(f"error_description: {error_desc!r}")
    parts.append(f"got: {result!r}")
    assert not result.get(ToolResultFields.IS_ERROR), " — ".join(parts)


def validate_remove_success(result: dict, context: str = "") -> None:
    """Assert that a remove operation (env or packages) returned success."""
    parts = ["Expected is_error=false (successful remove)"]
    if context:
        parts.append(context)
    error_desc = result.get(ToolResultFields.ERROR_DESCRIPTION, "")
    if error_desc:
        parts.append(f"error_description: {error_desc!r}")
    parts.append(f"got: {result!r}")
    assert not result.get(ToolResultFields.IS_ERROR), " — ".join(parts)


def validate_create_error(result: dict, context: str = "") -> None:
    """Assert that conda_create_environment returned an error (e.g., duplicate name)."""
    parts = ["Expected is_error=true (create should fail)"]
    if context:
        parts.append(context)
    parts.append(f"got: {result!r}")
    assert result.get(ToolResultFields.IS_ERROR) is True, " — ".join(parts)


# =============================================================================
# conda-meta-mcp validators
# =============================================================================


def validate_conda_meta_success(response: dict, context: str = "") -> None:
    """
    Assert that a conda-meta-mcp tool returned success.

    conda-meta-mcp uses MCP standard response format:
    {"content": [...], "isError": false}
    """
    parts = ["Expected isError=false (conda-meta success)"]
    if context:
        parts.append(context)

    # Check for isError field (MCP standard uses camelCase)
    is_error = response.get("isError", response.get("is_error", False))
    parts.append(f"got: isError={is_error}")
    assert not is_error, " — ".join(parts)


def validate_conda_meta_text_content(response: dict, context: str = "") -> None:
    """
    Assert that conda-meta-mcp response has non-empty text content.

    Checks that content array contains at least one text item.
    """
    parts = ["Expected non-empty text content"]
    if context:
        parts.append(context)

    content = response.get("content", [])
    text_items = [c for c in content if c.get("type") == "text" and c.get("text")]
    parts.append(f"got {len(text_items)} text items")
    assert len(text_items) > 0, " — ".join(parts)


def validate_conda_meta_error(response: dict, context: str = "") -> None:
    """Assert that a conda-meta-mcp tool returned an error."""
    parts = ["Expected isError=true (conda-meta error)"]
    if context:
        parts.append(context)

    is_error = response.get("isError", response.get("is_error", False))
    parts.append(f"got: isError={is_error}")
    assert is_error is True, " — ".join(parts)


# =============================================================================
# search-mcp validators
# =============================================================================


def validate_search_success(response: dict, context: str = "") -> None:
    """
    Assert that a search-mcp tool returned success.

    search-mcp uses MCP standard response format.
    """
    parts = ["Expected isError=false (search success)"]
    if context:
        parts.append(context)

    is_error = response.get("isError", response.get("is_error", False))
    parts.append(f"got: isError={is_error}")
    assert not is_error, " — ".join(parts)


def validate_search_has_content(response: dict, context: str = "") -> None:
    """Assert that search-mcp response has content."""
    parts = ["Expected non-empty content"]
    if context:
        parts.append(context)

    content = response.get("content", [])
    parts.append(f"got {len(content)} content items")
    assert len(content) > 0, " — ".join(parts)


def validate_search_error(response: dict, context: str = "") -> None:
    """Assert that a search-mcp tool returned an error."""
    parts = ["Expected isError=true (search error)"]
    if context:
        parts.append(context)

    is_error = response.get("isError", response.get("is_error", False))
    parts.append(f"got: isError={is_error}")
    assert is_error is True, " — ".join(parts)

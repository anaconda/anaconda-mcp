# Contract: Response Validators

**Date**: 2026-05-14

## Purpose

Define the interface for MCP tool response validation functions used in QA tests.

## Interface

### Base Validator Signature

```python
def validate_{server}_{check}(response: dict, *, context: str = "") -> None:
    """
    Validate {check} for {server} tool response.

    Args:
        response: Raw MCP tool response dict
        context: Optional string for error message context

    Raises:
        AssertionError: If validation fails
    """
```

### environments-mcp Validators

| Validator | Purpose | Assertion |
|-----------|---------|-----------|
| `_validate_install_success` | Verify install success | `is_error == False` |
| `_validate_install_has_message` | Verify message present | `tool_result.message` exists and non-empty |
| `validate_list_packages_success` | Verify list packages | `is_error == False`, `tool_result.packages` is list |
| `validate_remove_success` | Verify remove success | `is_error == False` |
| `validate_error_response` | Verify error shape | `is_error == True`, `error_description` present |

### conda-meta-mcp Validators

| Validator | Purpose | Assertion |
|-----------|---------|-----------|
| `validate_conda_meta_success` | Verify MCP success | `isError == False`, `content` is non-empty list |
| `validate_conda_meta_error` | Verify MCP error | `isError == True` |
| `validate_conda_meta_text_content` | Verify text content | `content[0].type == "text"`, `text` is non-empty |

### search-mcp Validators

| Validator | Purpose | Assertion |
|-----------|---------|-----------|
| `validate_search_success` | Verify search success | `isError == False`, `content` present |
| `validate_search_error` | Verify search error | `isError == True` |
| `validate_search_results` | Verify results shape | `content[0].text` parses as JSON with `results` key |

## Response Extraction Helpers

```python
def _tool_result(response: dict) -> dict:
    """Extract tool_result from environments-mcp response."""

def _content_text(response: dict) -> str:
    """Extract text content from MCP standard response."""

def _parse_search_results(response: dict) -> list:
    """Parse JSON results from search-mcp response."""
```

## Usage Pattern

```python
from common.utils.response_validators import (
    validate_conda_meta_success,
    validate_conda_meta_text_content,
)

def test_info_success(self, call_tool):
    response = call_tool(CondaMetaTools.INFO, {})
    validate_conda_meta_success(response, context="info tool")
    validate_conda_meta_text_content(response, context="info tool")
```

## Error Messages

All validators MUST include:
1. What was expected
2. What was received
3. Context string (if provided)

Example:
```
AssertionError: Expected is_error=False but got True [context: env_name='test-env' pkg='numpy']
```

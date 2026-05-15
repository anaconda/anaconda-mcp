# Data Model: QA Tool Test Coverage

**Date**: 2026-05-14 | **Branch**: `001-extend-qa-tool-coverage`

## Entities

### Test Tool Enums

Tool name constants organized by MCP server.

```python
# tests/qa/mcp_tools/common/constants/mcp_tools.py

class Tools(str, Enum):
    """environments-mcp tools"""
    CONDA_CREATE_ENVIRONMENT = "conda_create_environment"
    CONDA_INSTALL_PACKAGES = "conda_install_packages"
    CONDA_LIST_ENVIRONMENTS = "conda_list_environments"
    CONDA_LIST_ENVIRONMENT_PACKAGES = "conda_list_environment_packages"  # NEW
    CONDA_REMOVE_ENVIRONMENT = "conda_remove_environment"
    CONDA_REMOVE_PACKAGES = "conda_remove_packages"  # NEW


class CondaMetaTools(str, Enum):
    """conda-meta-mcp tools"""
    INFO = "info"
    CACHE_MAINTENANCE = "cache_maintenance"
    CLI_HELP = "cli_help"
    FILE_PATH_SEARCH = "file_path_search"
    IMPORT_MAPPING = "import_mapping"
    PACKAGE_INSIGHTS = "package_insights"
    PACKAGE_SEARCH = "package_search"
    PYPI_TO_CONDA = "pypi_to_conda"
    REPOQUERY = "repoquery"


class SearchTools(str, Enum):
    """search-mcp tools"""
    SEARCH_PACKAGES = "search_packages"
    SEARCH_DOCUMENTATION = "search_documentation"
    SEARCH_FORUM = "search_forum"
    SEARCH_COLLECTIONS_AND_FILES = "search_collections_and_files"
    SEARCH_ENVIRONMENTS = "search_environments"
```

### Tool Argument Enums

Argument keys for tools with required/optional parameters.

```python
# environments-mcp (extend existing)
class ListEnvironmentPackagesArgs(str, Enum):
    ENVIRONMENT = "environment"
    PREFIX = "prefix"
    ENVIRONMENT_ROOT_PATH = "environment_root_path"


class RemovePackagesArgs(str, Enum):
    ENVIRONMENT = "environment"
    PREFIX = "prefix"
    PACKAGES = "packages"
    ENVIRONMENT_ROOT_PATH = "environment_root_path"


# conda-meta-mcp
class CliHelpArgs(str, Enum):
    TOOL = "tool"
    LIMIT = "limit"
    OFFSET = "offset"
    GREP = "grep"


class FilePathSearchArgs(str, Enum):
    PATH = "path"
    LIMIT = "limit"
    OFFSET = "offset"


class ImportMappingArgs(str, Enum):
    IMPORT_NAME = "import_name"
    GET_KEYS = "get_keys"


class PackageInsightsArgs(str, Enum):
    URL = "url"
    FILE = "file"
    LIMIT = "limit"
    OFFSET = "offset"
    GET_KEYS = "get_keys"


class PackageSearchArgs(str, Enum):
    PACKAGE_REF_OR_MATCH_SPEC = "package_ref_or_match_spec"
    CHANNEL = "channel"
    PLATFORM = "platform"
    LIMIT = "limit"
    OFFSET = "offset"
    GET_KEYS = "get_keys"


class PypiToCondaArgs(str, Enum):
    PYPI_NAME = "pypi_name"


class RepoqueryArgs(str, Enum):
    SUBCMD = "subcmd"
    SPEC = "spec"
    CHANNEL = "channel"
    PLATFORM = "platform"
    TREE = "tree"
    OFFSET = "offset"
    LIMIT = "limit"
    GET_KEYS = "get_keys"


# search-mcp
class SearchPackagesArgs(str, Enum):
    QUERY = "query"
    PAGE = "page"
    PAGE_SIZE = "page_size"
    GROUP_TOP_N = "group_top_n"
    SORT_KEY = "sort_key"
    CHANNELS = "channels"
    LICENSES = "licenses"
    PLATFORMS = "platforms"


class SearchDocumentationArgs(str, Enum):
    QUERY = "query"
    PAGE = "page"
    PAGE_SIZE = "page_size"
    TYPES = "types"
    KEYWORDS = "keywords"


class SearchForumArgs(str, Enum):
    QUERY = "query"
    PAGE = "page"
    PAGE_SIZE = "page_size"
    REPLIES = "replies"
    LAST_UPDATED_AFTER = "last_updated_after"
    VIEWS = "views"
    TYPES = "types"


class SearchCollectionsFilesArgs(str, Enum):
    QUERY = "query"
    PAGE = "page"
    PAGE_SIZE = "page_size"
    COLLECTIONS_LIMIT = "collections_limit"
    INCLUDE_DELETED = "include_deleted"
    MIN_FILE_SIZE = "min_file_size"
    OWNERSHIP = "ownership"


class SearchEnvironmentsArgs(str, Enum):
    QUERY = "query"
    PAGE = "page"
    PAGE_SIZE = "page_size"
    INCLUDE_DELETED = "include_deleted"
    PLATFORMS = "platforms"
    STATUS = "status"
    USERNAME = "username"
    CREATED_DATE_RANGE = "created_date_range"
    UPDATED_DATE_RANGE = "updated_date_range"
```

### Test Data Constants

Stable test inputs for deterministic tests.

```python
# tests/qa/mcp_tools/common/constants/test_data.py

# Existing
EXISTING_PKG = "pyyaml"
NONEXISTENT_PKG = "nonexistent-pkg-12345"
NONEXISTENT_ENV = "nonexistent-env-12345"

# New - conda-meta-mcp
KNOWN_IMPORT = "yaml"
KNOWN_IMPORT_PACKAGE = "pyyaml"
PYPI_PACKAGE = "PyYAML"
CONDA_PACKAGE = "pyyaml"
SEARCH_PACKAGE = "numpy"
REPOQUERY_SPEC = "python"
REPOQUERY_CHANNEL = "defaults"
FILE_PATH_PATTERN = "yaml/__init__.py"

# New - search-mcp
SEARCH_QUERY_PACKAGES = "numpy"
SEARCH_QUERY_DOCS = "conda"
SEARCH_QUERY_FORUM = "install"
SEARCH_QUERY_COLLECTIONS = "data"
SEARCH_QUERY_ENVIRONMENTS = "python"
```

## Response Shapes

### environments-mcp

```python
# Success
{
    "is_error": False,
    "tool_result": {
        "message": "...",
        # tool-specific fields
    }
}

# Error
{
    "is_error": True,
    "error_description": "..."
}
```

### conda-meta-mcp

```python
# Success (MCP standard)
{
    "content": [
        {"type": "text", "text": "..."}
    ],
    "isError": False  # Note: camelCase per MCP spec
}

# Error
{
    "content": [
        {"type": "text", "text": "Error: ..."}
    ],
    "isError": True
}
```

### search-mcp

```python
# Success (MCP standard)
{
    "content": [
        {"type": "text", "text": "{\"results\": [...]}"}
    ],
    "isError": False
}

# Error
{
    "content": [
        {"type": "text", "text": "{\"error\": \"...\"}"}
    ],
    "isError": True
}
```

## Validation Rules

1. **Tool name validity**: Must match enum value (prevents typos)
2. **Required parameters**: Tool call fails if missing
3. **Response shape**: Must contain expected fields per server
4. **Error flag**: `is_error`/`isError` must be boolean
5. **Content presence**: Success response must have non-empty content/tool_result

---

## Session 2026-05-15: Authentication Entities

### AuthState

Represents the current authentication state detected at session start.

```python
# tests/qa/mcp_tools/common/utils/auth_service.py

from dataclasses import dataclass
from typing import Literal

AuthSource = Literal["env_credentials", "keyring", "no_auth", "env_credentials_failed"]

@dataclass
class AuthState:
    """Authentication state for the test session."""
    logged_in: bool
    token: str | None = None
    source: AuthSource = "no_auth"
```

### AuthService

OAuth 2-step login implementation for programmatic token acquisition.

```python
class AuthService:
    """Programmatic OAuth authentication service."""

    def __init__(self, base_url: str = "https://api.anaconda.com"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def _authorize(self) -> str:
        """Step 1: Get state token."""
        response = self.client.post(f"{self.base_url}/auth/authorize")
        response.raise_for_status()
        return response.json()["state"]

    def login(self, email: str, password: str) -> str:
        """Step 2: Complete OAuth flow, return session token."""
        state = self._authorize()
        response = self.client.post(
            f"{self.base_url}/auth/login",
            json={"state": state, "email": email, "password": password}
        )
        response.raise_for_status()
        return response.json()["token"]
```

### Tool Auth Category Enum

Classification of tools by their authentication dependency.

```python
from enum import Enum

class ToolAuthCategory(str, Enum):
    """Tool authentication dependency classification."""
    INDEPENDENT = "auth_independent"  # Works identically with/without auth
    REQUIRED = "auth_required"        # Needs auth to return results
    ENHANCED = "auth_enhanced"        # Works both ways, different results
```

### Tool-to-Category Mapping

```python
TOOL_AUTH_CATEGORIES: dict[str, ToolAuthCategory] = {
    # environments-mcp (6) - all auth-independent
    "conda_create_environment": ToolAuthCategory.INDEPENDENT,
    "conda_install_packages": ToolAuthCategory.INDEPENDENT,
    "conda_list_environments": ToolAuthCategory.INDEPENDENT,
    "conda_list_environment_packages": ToolAuthCategory.INDEPENDENT,
    "conda_remove_environment": ToolAuthCategory.INDEPENDENT,
    "conda_remove_packages": ToolAuthCategory.INDEPENDENT,

    # conda-meta-mcp (9) - all auth-independent
    "conda-meta_info": ToolAuthCategory.INDEPENDENT,
    "conda-meta_cache_maintenance": ToolAuthCategory.INDEPENDENT,
    "conda-meta_cli_help": ToolAuthCategory.INDEPENDENT,
    "conda-meta_file_path_search": ToolAuthCategory.INDEPENDENT,
    "conda-meta_import_mapping": ToolAuthCategory.INDEPENDENT,
    "conda-meta_package_insights": ToolAuthCategory.INDEPENDENT,
    "conda-meta_package_search": ToolAuthCategory.INDEPENDENT,
    "conda-meta_pypi_to_conda": ToolAuthCategory.INDEPENDENT,
    "conda-meta_repoquery": ToolAuthCategory.INDEPENDENT,

    # search-mcp (5) - mixed
    "search_search_packages": ToolAuthCategory.ENHANCED,
    "search_search_documentation": ToolAuthCategory.ENHANCED,
    "search_search_forum": ToolAuthCategory.ENHANCED,
    "search_search_collections_and_files": ToolAuthCategory.REQUIRED,
    "search_search_environments": ToolAuthCategory.REQUIRED,
}
```

### Pytest Markers

```python
# conftest.py pytest_configure()

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "auth_independent: Tool works without authentication"
    )
    config.addinivalue_line(
        "markers",
        "auth_required: Tool requires authentication to return results"
    )
    config.addinivalue_line(
        "markers",
        "auth_enhanced: Tool works with/without auth, different results"
    )
```

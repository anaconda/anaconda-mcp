"""
MCP tool names and their argument/result field keys.

Using str-based enums so values work directly as dict keys and JSON strings
without an explicit .value call.

Tool coverage: 20 tools across 3 MCP servers
- environments-mcp: 6 tools (conda_*)
- conda-meta-mcp: 9 tools (info, cache_maintenance, cli_help, etc.)
- search-mcp: 5 tools (search_*)
"""

from __future__ import annotations

from enum import Enum

# =============================================================================
# environments-mcp tools (6 tools)
# =============================================================================


class Tools(str, Enum):
    """environments-mcp tool names."""

    CONDA_CREATE_ENVIRONMENT = "conda_create_environment"
    CONDA_INSTALL_PACKAGES = "conda_install_packages"
    CONDA_LIST_ENVIRONMENTS = "conda_list_environments"
    CONDA_LIST_ENVIRONMENT_PACKAGES = "conda_list_environment_packages"
    CONDA_REMOVE_ENVIRONMENT = "conda_remove_environment"
    CONDA_REMOVE_PACKAGES = "conda_remove_packages"


class CreateEnvironmentArgs(str, Enum):
    ENVIRONMENT_NAME = "environment_name"
    PREFIX = "prefix"
    PACKAGES = "packages"
    OVERRIDE_CHANNELS = "override_channels"
    ENVIRONMENT_ROOT_PATH = "environment_root_path"


class InstallPackagesArgs(str, Enum):
    ENVIRONMENT = "environment"
    PREFIX = "prefix"
    PACKAGES = "packages"
    ENVIRONMENT_ROOT_PATH = "environment_root_path"


class ListEnvironmentPackagesArgs(str, Enum):
    ENVIRONMENT = "environment"
    PREFIX = "prefix"
    ENVIRONMENT_ROOT_PATH = "environment_root_path"


class RemoveEnvironmentArgs(str, Enum):
    ENVIRONMENT_NAME = "environment_name"
    PREFIX = "prefix"
    ENVIRONMENT_ROOT_PATH = "environment_root_path"


class RemovePackagesArgs(str, Enum):
    ENVIRONMENT = "environment"
    PREFIX = "prefix"
    PACKAGES = "packages"
    ENVIRONMENT_ROOT_PATH = "environment_root_path"


# =============================================================================
# conda-meta-mcp tools (9 tools)
# =============================================================================


class CondaMetaTools(str, Enum):
    """conda-meta-mcp tool names (prefixed by mcp-compose)."""

    INFO = "conda-meta_info"
    CACHE_MAINTENANCE = "conda-meta_cache_maintenance"
    CLI_HELP = "conda-meta_cli_help"
    FILE_PATH_SEARCH = "conda-meta_file_path_search"
    IMPORT_MAPPING = "conda-meta_import_mapping"
    PACKAGE_INSIGHTS = "conda-meta_package_insights"
    PACKAGE_SEARCH = "conda-meta_package_search"
    PYPI_TO_CONDA = "conda-meta_pypi_to_conda"
    REPOQUERY = "conda-meta_repoquery"


class CliHelpArgs(str, Enum):
    TOOL = "tool"
    LIMIT = "limit"
    OFFSET = "offset"
    GREP = "grep"


class FilePathSearchArgs(str, Enum):
    PATH = "path"
    CHANNEL = "channel"
    LIMIT = "limit"
    OFFSET = "offset"


class ImportMappingArgs(str, Enum):
    IMPORT_NAME = "import_name"
    CHANNEL = "channel"
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
    CHANNEL = "channel"


class RepoqueryArgs(str, Enum):
    SUBCMD = "subcmd"
    SPEC = "spec"
    CHANNEL = "channel"
    PLATFORM = "platform"
    TREE = "tree"
    OFFSET = "offset"
    LIMIT = "limit"
    GET_KEYS = "get_keys"


# =============================================================================
# search-mcp tools (5 tools)
# =============================================================================


class SearchTools(str, Enum):
    """search-mcp tool names (prefixed by mcp-compose)."""

    SEARCH_PACKAGES = "search_search_packages"
    SEARCH_DOCUMENTATION = "search_search_documentation"
    SEARCH_FORUM = "search_search_forum"
    SEARCH_COLLECTIONS_AND_FILES = "search_search_collections_and_files"
    SEARCH_ENVIRONMENTS = "search_search_environments"


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


# =============================================================================
# Common result fields
# =============================================================================


class ToolResultFields(str, Enum):
    IS_ERROR = "is_error"
    ERROR_DESCRIPTION = "error_description"
    TOOL_RESULT = "tool_result"


# =============================================================================
# Authentication categories
# =============================================================================


class ToolAuthCategory(str, Enum):
    """Tool authentication dependency classification."""

    INDEPENDENT = "auth_independent"  # Works identically with/without auth
    REQUIRED = "auth_required"  # Needs auth to return results
    ENHANCED = "auth_enhanced"  # Works both ways, different results


TOOL_AUTH_CATEGORIES: dict[str, ToolAuthCategory] = {
    # environments-mcp (6) - all auth-independent
    Tools.CONDA_CREATE_ENVIRONMENT: ToolAuthCategory.INDEPENDENT,
    Tools.CONDA_INSTALL_PACKAGES: ToolAuthCategory.INDEPENDENT,
    Tools.CONDA_LIST_ENVIRONMENTS: ToolAuthCategory.INDEPENDENT,
    Tools.CONDA_LIST_ENVIRONMENT_PACKAGES: ToolAuthCategory.INDEPENDENT,
    Tools.CONDA_REMOVE_ENVIRONMENT: ToolAuthCategory.INDEPENDENT,
    Tools.CONDA_REMOVE_PACKAGES: ToolAuthCategory.INDEPENDENT,
    # conda-meta-mcp (9) - all auth-independent
    CondaMetaTools.INFO: ToolAuthCategory.INDEPENDENT,
    CondaMetaTools.CACHE_MAINTENANCE: ToolAuthCategory.INDEPENDENT,
    CondaMetaTools.CLI_HELP: ToolAuthCategory.INDEPENDENT,
    CondaMetaTools.FILE_PATH_SEARCH: ToolAuthCategory.INDEPENDENT,
    CondaMetaTools.IMPORT_MAPPING: ToolAuthCategory.INDEPENDENT,
    CondaMetaTools.PACKAGE_INSIGHTS: ToolAuthCategory.INDEPENDENT,
    CondaMetaTools.PACKAGE_SEARCH: ToolAuthCategory.INDEPENDENT,
    CondaMetaTools.PYPI_TO_CONDA: ToolAuthCategory.INDEPENDENT,
    CondaMetaTools.REPOQUERY: ToolAuthCategory.INDEPENDENT,
    # search-mcp (5) - mixed
    SearchTools.SEARCH_PACKAGES: ToolAuthCategory.ENHANCED,
    SearchTools.SEARCH_DOCUMENTATION: ToolAuthCategory.ENHANCED,
    SearchTools.SEARCH_FORUM: ToolAuthCategory.ENHANCED,
    SearchTools.SEARCH_COLLECTIONS_AND_FILES: ToolAuthCategory.REQUIRED,
    SearchTools.SEARCH_ENVIRONMENTS: ToolAuthCategory.REQUIRED,
}

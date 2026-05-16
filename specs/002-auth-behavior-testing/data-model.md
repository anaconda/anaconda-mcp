# Data Model: Auth Behavior Testing

**Feature**: Auth Behavior Testing for MCP Tools
**Phase**: 1 - Design
**Date**: 2026-05-15

## Entities

### AuthState

**Purpose**: Immutable state object representing authentication status for test session.

**Location**: `tests/qa/mcp_tools/common/utils/auth_service.py` (existing)

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `logged_in` | `bool` | Whether user is authenticated |
| `token` | `str \| None` | API key/token if authenticated |
| `source` | `AuthSource` | How auth was detected |

**AuthSource (Literal type)**:
- `"env_credentials"`: Token from `ANACONDA_AUTH_API_KEY` env var
- `"no_auth"`: No authentication available

**Validation Rules**:
- If `logged_in=True`, `token` MUST be non-None
- If `logged_in=False`, `token` MUST be None

**State Transitions**: None (immutable, detected once at session start)

---

### AuthCategory

**Purpose**: Classification of a tool's authentication dependency.

**Location**: pytest markers in `conftest.py`

**Values**:

| Marker | Meaning | Test Behavior |
|--------|---------|---------------|
| `@pytest.mark.auth_independent` | Tool works identically with/without auth | Run normally |
| `@pytest.mark.auth_required` | Tool requires auth to return results | Skip if not logged in |
| `@pytest.mark.auth_enhanced` | Tool works both ways, different results | Run normally, same assertions |

---

### ToolAuthMapping

**Purpose**: Maps each MCP tool to its auth category.

**Location**: Documented in spec, enforced via markers on test classes.

| Server | Tool | Category |
|--------|------|----------|
| environments-mcp | `conda_create_environment` | auth_independent |
| environments-mcp | `conda_install_packages` | auth_independent |
| environments-mcp | `conda_list_environment_packages` | auth_independent |
| environments-mcp | `conda_list_environments` | auth_independent |
| environments-mcp | `conda_remove_environment` | auth_independent |
| environments-mcp | `conda_remove_packages` | auth_independent |
| conda-meta-mcp | `info` | auth_independent |
| conda-meta-mcp | `cache_maintenance` | auth_independent |
| conda-meta-mcp | `cli_help` | auth_independent |
| conda-meta-mcp | `file_path_search` | auth_independent |
| conda-meta-mcp | `import_mapping` | auth_independent |
| conda-meta-mcp | `package_insights` | auth_independent |
| conda-meta-mcp | `package_search` | auth_independent |
| conda-meta-mcp | `pypi_to_conda` | auth_independent |
| conda-meta-mcp | `repoquery` | auth_independent |
| search-mcp | `search_packages` | auth_enhanced |
| search-mcp | `search_documentation` | auth_enhanced |
| search-mcp | `search_forum` | auth_enhanced |
| search-mcp | `search_collections_and_files` | auth_required |
| search-mcp | `search_environments` | auth_required |

---

## Fixture Relationships

```
pytest session
    │
    └── auth_state (session-scoped)
            │
            ├── require_auth (function-scoped)
            │       └── skips test if not auth_state.logged_in
            │
            └── assertion helpers (functions)
                    └── receive auth_state, adjust behavior
```

## File Organization

```
tests/qa/mcp_tools/
├── conftest.py
│   ├── auth_state fixture (existing)
│   └── require_auth fixture (NEW)
│
├── common/utils/
│   ├── auth_service.py
│   │   ├── AuthState (existing)
│   │   ├── AuthSource (existing)
│   │   └── detect_auth_state() (existing)
│   │
│   ├── assertions.py (NEW)
│   │   └── assert_search_results()
│   │
│   └── response_validators.py (existing)
│       ├── validate_search_success()
│       └── validate_search_has_content()
│
└── test_search_*.py
    └── Use require_auth or assertions as needed
```

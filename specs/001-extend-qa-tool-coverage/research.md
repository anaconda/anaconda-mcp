# Research: Extend QA Tool Test Coverage

**Date**: 2026-05-14 | **Branch**: `001-extend-qa-tool-coverage`

## Research Questions

### 1. Tool Response Shapes by MCP Server

**Question**: What are the response shapes for each MCP server's tools?

**Decision**: Each server has consistent response patterns:

| Server | Success Response | Error Response |
|--------|------------------|----------------|
| environments-mcp | `{"is_error": false, "tool_result": {...}}` | `{"is_error": true, "error_description": "..."}` |
| conda-meta-mcp | `{"content": [...], "isError": false}` | `{"content": [...], "isError": true}` |
| search-mcp | Standard MCP response with `content` array | Error in `content` with `isError: true` |

**Rationale**: Response shapes verified from GitHub repos and mcp-compose proxy behavior. Tests must handle both `is_error` (environments-mcp) and `isError` (MCP standard) field names.

**Alternatives considered**: Normalizing response shapes in validators — chosen to handle both patterns.

### 2. Test Data for conda-meta-mcp

**Question**: What stable test data can be used for conda-meta-mcp tools?

**Decision**: Use well-known, stable packages and imports:

| Tool | Test Data |
|------|-----------|
| `package_search` | `numpy`, `pandas` — ubiquitous, always available |
| `import_mapping` | `yaml` → `pyyaml`, `np` → `numpy` |
| `pypi_to_conda` | `PyYAML` → `pyyaml`, `numpy` → `numpy` |
| `repoquery` | `python` depends, `numpy` whoneeds |
| `file_path_search` | `/lib/python3.*/site-packages/yaml/__init__.py` |
| `package_insights` | URL from conda-forge repodata |

**Rationale**: These packages exist in all major channels and have stable names. Tests remain deterministic.

### 3. Test Data for search-mcp

**Question**: What stable queries work for search-mcp tools?

**Decision**: Use broad, always-returning queries:

| Tool | Test Query | Rationale |
|------|------------|-----------|
| `search_packages` | `numpy` | Most popular package, always returns results |
| `search_documentation` | `conda` | Core docs always present |
| `search_forum` | `install` | High-frequency forum topic |
| `search_collections_and_files` | `data` | Broad term with results |
| `search_environments` | `python` | Common environment component |

**Rationale**: Broad queries ensure tests don't fail due to empty results. Specific assertions focus on response shape, not content.

### 4. Hang-Stress Tool Selection

**Question**: Which tools need hang-stress coverage?

**Decision**: Per spec clarification:
- **environments-mcp**: Already covered (3 tools)
- **conda-meta-mcp**: `repoquery` — uses libmamba solver, large result pagination
- **search-mcp**: `search_packages` — upstream HTTP calls, complex filtering

**Rationale**: These tools have the highest risk of proxy-state accumulation due to:
1. Long-running operations (solver, HTTP)
2. Complex response structures
3. Pagination/streaming potential

### 5. Tool Constants Organization

**Question**: How should `mcp_tools.py` be extended?

**Decision**: Organize by server with separate enum classes:

```python
# Existing
class Tools(str, Enum):  # environments-mcp
    ...

# New
class CondaMetaTools(str, Enum):  # conda-meta-mcp
    INFO = "info"
    CACHE_MAINTENANCE = "cache_maintenance"
    ...

class SearchTools(str, Enum):  # search-mcp
    SEARCH_PACKAGES = "search_packages"
    ...
```

**Rationale**: Separate enums per server maintain clear ownership and prevent namespace collisions.

### 6. Response Validators Pattern

**Question**: How should validators handle different response shapes?

**Decision**: Create server-specific validators:

```python
# environments-mcp (existing pattern)
def _validate_install_success(result, context): ...

# conda-meta-mcp (new)
def validate_conda_meta_success(response, context): ...

# search-mcp (new)
def validate_search_success(response, context): ...
```

**Rationale**: Each server may have different response envelope structure. Dedicated validators make assertions clear and maintainable.

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| pytest | existing | Test framework |
| httpx | existing | HTTP transport |
| mcp-compose | existing | Server orchestration |
| conda-meta-mcp | `pip install conda-meta-mcp` | `cmm` command for server |
| anaconda.com API | remote | search-mcp backend |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Network flakiness | search-mcp tests fail intermittently | Use broad queries, retry fixture, mark as `slow` |
| conda-meta-mcp cache state | Test pollution | `cache_maintenance` call in fixture setup |
| Auth token expiry | search-mcp tests fail | Document token requirement, CI secret rotation |
| Channel availability | conda-meta tests fail | Use defaults + conda-forge (high availability) |

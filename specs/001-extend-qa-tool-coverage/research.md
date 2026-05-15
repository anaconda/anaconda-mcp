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
| Auth token expiry | search-mcp tests fail | Programmatic OAuth flow obtains fresh tokens |
| Channel availability | conda-meta tests fail | Use defaults + conda-forge (high availability) |
| Missing credentials | Auth-required tests skip | Clear skip messages, fallback to keyring |

---

## Session 2026-05-15: Authentication Research

### 7. OAuth Programmatic Authentication

**Question**: How should tests obtain fresh authentication tokens in CI?

**Decision**: Implement a Python `AuthService` class that performs the 2-step OAuth login flow.

**Reference Implementation**: anaconda-desktop `api-auth-service.ts` demonstrates:
1. `authorize()` → POST to `/auth/authorize` → returns `state` token
2. `login(state, email, password)` → POST to `/auth/login` → returns session token

**Python Pattern**:
```python
class AuthService:
    def __init__(self, base_url: str = "https://api.anaconda.com"):
        self.base_url = base_url
        self.client = httpx.Client()

    def login(self, email: str, password: str) -> str:
        """Complete OAuth flow and return session token."""
        state = self._authorize()
        response = self.client.post(
            f"{self.base_url}/auth/login",
            json={"state": state, "email": email, "password": password}
        )
        return response.json()["token"]
```

**Rationale**: Tokens are session-scoped and expire, so static tokens in GitHub secrets won't work reliably.

**Alternatives Rejected**:
| Alternative | Why Rejected |
|-------------|--------------|
| Static tokens in secrets | Tokens expire; unreliable for CI |
| `anaconda login` CLI call | Requires interactive TTY; not headless-friendly |
| Mock auth responses | Violates constitution: "All tests use real integration" |

### 8. Authentication State Detection

**Question**: How should tests detect auth state to adapt their behavior?

**Decision**: Session-scoped pytest fixture with priority-based detection:

```python
@pytest.fixture(scope="session")
def auth_state() -> AuthState:
    # Priority 1: .env file or environment credentials (local dev / CI)
    # conftest loads .env automatically via python-dotenv
    email = os.environ.get("ANACONDA_USER_EMAIL")
    password = os.environ.get("ANACONDA_USER_PASSWORD")
    if email and password:
        try:
            token = AuthService().login(email, password)
            return AuthState(logged_in=True, token=token, source="env_credentials")
        except AuthError:
            return AuthState(logged_in=False, source="env_credentials_failed")

    # Priority 2: Keyring token (fallback from `anaconda login`)
    try:
        token = get_keyring_token()  # via anaconda-auth
        return AuthState(logged_in=True, token=token, source="keyring")
    except:
        return AuthState(logged_in=False, source="no_auth")
```

**Credential sources**:
- **Local development**: `.env` file in repo root (already in `.gitignore`)
- **CI workflow**: GitHub secrets loaded via `env:` block in workflow YAML

**Rationale**: Centralized detection at session start; no redundant per-test checks.

### 9. Tool Auth Categories

**Question**: How should tests declare their auth dependency?

**Decision**: Three pytest markers based on spec User Story 5:

| Category | Marker | Behavior When Logged Out |
|----------|--------|--------------------------|
| Auth-Independent (15 tools) | `@pytest.mark.auth_independent` | Run normally |
| Auth-Required (2 tools) | `@pytest.mark.auth_required` | Skip with message |
| Auth-Enhanced (3 tools) | `@pytest.mark.auth_enhanced` | Run, assert public-only |

**Tool Classification**:
- **Auth-Independent**: All environments-mcp (6), all conda-meta-mcp (9)
- **Auth-Required**: `search_collections_and_files`, `search_environments`
- **Auth-Enhanced**: `search_packages`, `search_documentation`, `search_forum`

### 10. Test Coverage Gap Analysis (Updated)

**Finding**: Test coverage is more complete than initially assessed in spec. From `test_design.md`:

| Server | Tools | Happy Path | Error Path | Hang Stress |
|--------|-------|:----------:|:----------:|:-----------:|
| environments-mcp | 6 | 6 ✓ | 5 ✓ | 3 ✓ |
| conda-meta-mcp | 9 | 9 ✓ | 3 ✓ | 1 ✓ |
| search-mcp | 5 | 5 ✓ | 3 ✓ | 1 ✓ |

**Remaining Work**:
1. Add auth-state handling to existing search-mcp tests
2. Implement AuthService class
3. Add auth fixtures and markers to conftest.py
4. Update test_design.md with auth documentation

### 11. CI Workflow Integration

**Decision**: Extend `qa-mcp-tools.yml` to pass credentials via environment variables.

```yaml
env:
  ANACONDA_USER_EMAIL: ${{ secrets.ANACONDA_USER_EMAIL }}
  ANACONDA_USER_PASSWORD: ${{ secrets.ANACONDA_USER_PASSWORD }}
```

**Secrets Required**:
- `ANACONDA_USER_EMAIL`: Test account email
- `ANACONDA_USER_PASSWORD`: Test account password

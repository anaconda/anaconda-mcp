# Feature Specification: Extend QA Tool Test Coverage

**Feature Branch**: `001-extend-qa-tool-coverage`

**Created**: 2026-05-14

**Status**: Draft

**Input**: User description: "extend qa-owned tests to cover all available tools. revisit all implemented features and AC: each tool has at least positive scenario. tool might require >1 scenario for complex set of parameters"

## Tool Inventory

### environments-mcp (6 tools)

Source: [anaconda/environments-mcp](https://github.com/anaconda/environments-mcp)

| Tool | Description | Current Coverage |
|------|-------------|------------------|
| `conda_create_environment` | Create a new conda environment | Happy path ✓, Error path ✗ |
| `conda_install_packages` | Install packages into environment | Happy path ✓, Error path ✓, Hang stress ✓ |
| `conda_list_environment_packages` | List packages in an environment | **No coverage** |
| `conda_list_environments` | List all conda environments | Happy path ✓, Error path ✗, Hang stress ✓ |
| `conda_remove_environment` | Remove a conda environment | Happy path ✗, Error path ✓, Hang stress ✓ |
| `conda_remove_packages` | Remove packages from environment | **No coverage** |

### conda-meta-mcp (9 tools)

Source: [conda-incubator/conda-meta-mcp](https://github.com/conda-incubator/conda-meta-mcp)

| Tool | Description | Current Coverage |
|------|-------------|------------------|
| `info` | Version metadata (MCP tool/library versions) | **No coverage** |
| `cache_maintenance` | Run cache maintenance for all caches | **No coverage** |
| `cli_help` | CLI help for conda | **No coverage** |
| `file_path_search` | File path to package mapping | **No coverage** |
| `import_mapping` | Import to package heuristic mapping | **No coverage** |
| `package_insights` | Package info tarball data | **No coverage** |
| `package_search` | Package search | **No coverage** |
| `pypi_to_conda` | PyPI name to conda package mapping | **No coverage** |
| `repoquery` | Repository metadata queries (depends/whoneeds) | **No coverage** |

### search-mcp (5 tools)

Source: [anaconda/anaconda-mcp-search](https://github.com/anaconda/anaconda-mcp-search)

| Tool | Description | Current Coverage |
|------|-------------|------------------|
| `search_packages` | Search for packages | **No coverage** |
| `search_documentation` | Search documentation | **No coverage** |
| `search_forum` | Search forum posts | **No coverage** |
| `search_collections_and_files` | Search collections and files | **No coverage** |
| `search_environments` | Search environments | **No coverage** |

### Coverage Summary

| Server | Total Tools | Happy Path | Error Path | Hang Stress | Gaps |
|--------|-------------|------------|------------|-------------|------|
| environments-mcp | 6 | 3 | 2 | 3 | 2 tools no coverage, 3 missing paths |
| conda-meta-mcp | 9 | 0 | 0 | 0 | 9 tools no coverage |
| search-mcp | 5 | 0 | 0 | 0 | 5 tools no coverage |
| **Total** | **20** | **3** | **2** | **3** | **16 tools + 3 paths** |

## Tool Parameters Reference

### environments-mcp Parameters

| Tool | Required Parameters | Optional Parameters | Test Scenarios Needed |
|------|---------------------|---------------------|----------------------|
| `conda_create_environment` | `environment_name` OR `prefix` | `packages`, `override_channels`, `environment_root_path` | By name, by prefix, with packages, with root_path |
| `conda_install_packages` | `environment` OR `prefix`, `packages` | `environment_root_path` | By name, by prefix (already covered) |
| `conda_list_environment_packages` | `environment` OR `prefix` | `environment_root_path` | By name, by prefix |
| `conda_list_environments` | (none) | (none) | Basic call (already covered) |
| `conda_remove_environment` | `environment_name` OR `prefix` | `environment_root_path` | By name, by prefix |
| `conda_remove_packages` | `environment` OR `prefix`, `packages` | `environment_root_path` | By name, by prefix |

### conda-meta-mcp Parameters

| Tool | Required Parameters | Optional Parameters | Test Scenarios Needed |
|------|---------------------|---------------------|----------------------|
| `info` | (none) | (none) | Basic call |
| `cache_maintenance` | (none) | (none) | Basic call |
| `cli_help` | (none) | `tool`, `limit`, `offset`, `grep` | Default, with grep filter |
| `file_path_search` | `path` | `limit`, `offset` | Known path, unknown path |
| `import_mapping` | `import_name` | `get_keys` | Known import (e.g., "yaml"), unknown import |
| `package_insights` | `url` | `file`, `limit`, `offset`, `get_keys` | Valid package URL |
| `package_search` | `package_ref_or_match_spec`, `channel`, `platform` | `limit`, `offset`, `get_keys` | Simple search, with version spec |
| `pypi_to_conda` | `pypi_name` | (none) | Known mapping (e.g., "PyYAML"), direct match |
| `repoquery` | `subcmd`, `spec`, `channel` | `platform`, `tree`, `offset`, `limit`, `get_keys` | depends mode, whoneeds mode |

### search-mcp Parameters

| Tool | Required Parameters | Optional Parameters | Test Scenarios Needed |
|------|---------------------|---------------------|----------------------|
| `search_packages` | `query` | `page`, `page_size`, `group_top_n`, `sort_key`, `channels`, `licenses`, `platforms` | Basic search, with filters |
| `search_documentation` | `query` | `page`, `page_size`, `types`, `keywords` | Basic search |
| `search_forum` | `query` | `page`, `page_size`, `replies`, `last_updated_after`, `views`, `types` | Basic search |
| `search_collections_and_files` | `query` | `page`, `page_size`, `collections_limit`, `include_deleted`, `min_file_size`, `ownership` | Basic search |
| `search_environments` | `query` | `page`, `page_size`, `include_deleted`, `platforms`, `status`, `username`, `created_date_range`, `updated_date_range` | Basic search, with filters |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Positive Scenario Coverage (Priority: P1)

QA engineer runs the MCP tool test suite and verifies that every available tool has at least one happy-path test that confirms the tool works correctly with valid inputs.

**Why this priority**: Without positive scenario coverage for all tools, we cannot validate basic functionality. This is the minimum bar for release readiness.

**Independent Test**: Run `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http` and verify all 20 tools have at least one passing happy-path test.

**Acceptance Scenarios**:

1. **Given** the MCP server is running with all servers registered (environments-mcp, conda-meta-mcp, search-mcp), **When** QA runs the test suite, **Then** each of the 20 tools has at least one test that exercises a successful operation.

2. **Given** a tool with complex parameters (e.g., `conda_create_environment` with optional `root_path`, `repoquery` with depends/whoneeds modes), **When** QA runs the test suite, **Then** there are tests covering the primary parameter combinations that represent distinct usage patterns.

---

### User Story 2 - Error Path Coverage for High-Risk Tools (Priority: P2)

QA engineer verifies that tools which can fail in user-facing ways have error-path tests that confirm proper error responses are returned (not hangs or crashes).

**Why this priority**: Error handling is critical for user experience and proxy stability. Tools that fail silently or hang degrade the AI assistant experience.

**Independent Test**: Run tests with `-m regression` and verify error scenarios return well-formed MCP error responses.

**Acceptance Scenarios**:

1. **Given** a tool that can fail due to invalid input (e.g., nonexistent environment name, invalid package name), **When** the tool is called with invalid input, **Then** the test verifies an error response is returned with `is_error=True` and a meaningful message.

2. **Given** a tool that interacts with external state (conda environments, remote APIs), **When** the external state is in an unexpected condition, **Then** the test verifies the tool handles the condition gracefully without hanging.

---

### User Story 3 - Hang Stress Coverage for Newly Tested Tools (Priority: P3)

QA engineer verifies that newly added tool tests include hang-stress variants where appropriate to catch proxy-state accumulation bugs (KI-011 pattern).

**Why this priority**: Hang regressions only manifest after accumulated proxy state. New tools need hang-stress coverage to prevent regression.

**Independent Test**: Run `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio -m hang_stress` and verify newly added tools are included.

**Hang-stress tool selection** (highest risk per MCP):
- **environments-mcp**: Already covered (`conda_install_packages`, `conda_list_environments`, `conda_remove_environment`)
- **conda-meta-mcp**: `repoquery` — uses libmamba solver, pagination, potentially large results
- **search-mcp**: `search_packages` — upstream HTTP to anaconda.com, complex filtering, grouped results

**Acceptance Scenarios**:

1. **Given** a tool that now has positive scenario coverage, **When** the tool is exercised 20 times in succession with valid inputs, **Then** no timeout occurs and all iterations complete within the configured `TOOL_TIMEOUT`.

---

### User Story 4 - Programmatic Authentication for CI (Priority: P1)

QA engineer configures the GitHub Actions workflow to run search-mcp tests without requiring pre-stored static API tokens. The test infrastructure obtains fresh session tokens at runtime using user credentials stored as GitHub secrets.

**Why this priority**: Without programmatic auth, search-mcp tests cannot run in CI because tokens expire between sessions. This blocks CI/CD coverage for 5 search-mcp tools.

**Independent Test**: Run the `qa-mcp-tools.yml` workflow in GitHub Actions with `ANACONDA_USER_EMAIL` and `ANACONDA_USER_PASSWORD` secrets configured, verify search-mcp tests pass.

**Acceptance Scenarios**:

1. **Given** the GitHub workflow has `ANACONDA_USER_EMAIL` and `ANACONDA_USER_PASSWORD` secrets configured, **When** the workflow runs search-mcp tests, **Then** the auth service obtains a fresh token via OAuth API and tests pass.

2. **Given** a developer runs tests locally without having run `anaconda login`, **When** they have `ANACONDA_USER_EMAIL` and `ANACONDA_USER_PASSWORD` in `.env`, **Then** the auth service obtains a token programmatically and tests pass.

3. **Given** a developer has previously run `anaconda login` locally, **When** they run tests without credentials in `.env`, **Then** the existing keyring token is used as fallback.

---

### User Story 5 - Authentication-State-Aware Test Behavior (Priority: P1)

QA engineer runs positive tool tests in both authenticated and unauthenticated modes, with tests automatically adjusting their behavior and assertions based on the current authentication state.

**Why this priority**: Some tools work identically regardless of auth state (environments-mcp, conda-meta-mcp), some tools require authentication (search-mcp private content), and some tools return different results based on auth state (search-mcp public vs private results). Tests must handle all cases to provide accurate coverage.

**Independent Test**: Run `pytest tests/qa/mcp_tools -o addopts=` twice: once with auth credentials configured, once without. Verify appropriate tests pass in each mode.

**Tool Authentication Classification**:

| Category | Tools | Logged Out Behavior | Logged In Behavior |
|----------|-------|--------------------|--------------------|
| **Auth-Independent** | All environments-mcp (6), all conda-meta-mcp (9) | Works normally | Works normally (no change) |
| **Auth-Required** | `search_collections_and_files`, `search_environments` | Should skip or return auth-required error | Returns private/user-scoped results |
| **Auth-Enhanced** | `search_packages`, `search_documentation`, `search_forum` | Returns public results only | Returns public + private/user results |

**Acceptance Scenarios**:

1. **Given** a test for an auth-independent tool (environments-mcp, conda-meta-mcp), **When** the test runs in either logged-out or logged-in mode, **Then** the test passes with identical behavior and assertions.

2. **Given** a test for an auth-required tool (`search_collections_and_files`, `search_environments`), **When** the user is logged out, **Then** the test is skipped with clear message OR validates the auth-required error response.

3. **Given** a test for an auth-required tool, **When** the user is logged in, **Then** the test validates the tool returns user-scoped results successfully.

4. **Given** a test for an auth-enhanced tool (`search_packages`, `search_documentation`, `search_forum`), **When** the user is logged out, **Then** the test validates the tool works with public data and makes no assertions about private content.

5. **Given** a test for an auth-enhanced tool, **When** the user is logged in, **Then** the test validates the tool works (same as logged-out) — private content assertions are optional/separate tests.

---

### Edge Cases

**Authentication & Auth State**:
- What happens when credentials are invalid? (Should fail fast with clear error before tests start)
- What happens when Anaconda auth API is temporarily unavailable? (Should retry with backoff, then fail with actionable error)
- What happens when token expires mid-test-run? (Out of scope for v1: assume token lifetime exceeds test duration)
- What happens when auth-required tool is called while logged out? (Test skips OR validates auth error response)
- What happens when auth-enhanced tool is called while logged out? (Tool works with public data; test validates public-only behavior)
- What happens when running tests without any auth config (no credentials, no keyring)? (Auth-independent tests pass; auth-required tests skip; auth-enhanced tests run public-only mode)

**environments-mcp**:
- What happens when `conda_list_environments` is called when no environments exist? (Should return empty list or just base) — *Covered by FR-005/T043 if meaningful*
- What happens when `conda_list_environment_packages` is called on an environment with no user-installed packages? (Should return base packages or empty) — *Happy path covers this implicitly*
- What happens when `conda_create_environment` is called with an already existing environment name? (Should return error) — *Covered by FR-004/T020*
- What happens when `conda_remove_environment` is called on base environment? (Should be rejected) — *Out of scope: base env protection is environments-mcp responsibility*
- What happens when `conda_remove_packages` is called with a package that isn't installed? (Should return appropriate error) — *Covered by T045*

**conda-meta-mcp**:
- What happens when `package_search` finds no results? (Should return empty list, not error) — *Covered by T046*
- What happens when `import_mapping` is given an unknown import? (Should return empty or not-found response) — *Covered by T047*
- What happens when `repoquery` is called with an invalid package name? (Should return appropriate error) — *Covered by T048*

**search-mcp**:
- What happens when search tools are called with empty query? (Should return error or empty results) — *Covered by T049-T051*
- What happens when search tools have network issues? (Should return appropriate timeout/error) — *Out of scope: network resilience is search-mcp responsibility; tests assume network available*

## Requirements *(mandatory)*

### Functional Requirements

**environments-mcp gaps**:
- **FR-001**: Test suite MUST include happy-path test for `conda_list_environment_packages` tool
- **FR-002**: Test suite MUST include happy-path test for `conda_remove_packages` tool
- **FR-003**: Test suite MUST include happy-path test for `conda_remove_environment` tool (currently only error path exists)
- **FR-004**: Test suite MUST include error-path test for `conda_create_environment` tool (currently only happy path exists)
- **FR-005**: Test suite MUST include error-path test for `conda_list_environments` tool if meaningful error scenarios exist

**conda-meta-mcp coverage**:
- **FR-006**: Test suite MUST include at least one happy-path test for each of the 9 conda-meta-mcp tools
- **FR-007**: Test suite MUST include error-path tests for tools with meaningful failure modes (`package_search`, `import_mapping`, `repoquery`)

**search-mcp coverage**:
- **FR-008**: Test suite MUST include at least one happy-path test for each of the 5 search-mcp tools
- **FR-009**: Test suite MUST include error-path tests for search tools (empty query, invalid parameters)

**Authentication for CI/CD**:
- **FR-014**: Test infrastructure MUST support programmatic authentication that obtains fresh tokens at runtime (tokens are session-scoped and expire)
- **FR-015**: Authentication service MUST implement OAuth 2-step login flow: (1) authorize request to get state token, (2) login with credentials to get session token
- **FR-016**: Credentials (email/password) MUST be sourced from environment variables locally (`.env`) and GitHub secrets in CI workflows
- **FR-017**: Authentication MUST work in both local development (interactive `anaconda login` fallback) and headless CI environments (API-based login)
- **FR-018**: Token obtained via API login MUST be passed to search-mcp via the `ANACONDA_AUTH_API_KEY` environment variable or mcp-compose config

**Authentication-State-Aware Testing**:
- **FR-019**: Test suite MUST detect current authentication state (logged-in vs logged-out) before running search-mcp tests
- **FR-020**: Tests for auth-independent tools (environments-mcp, conda-meta-mcp) MUST produce identical results regardless of auth state
- **FR-021**: Tests for auth-required tools (`search_collections_and_files`, `search_environments`) MUST skip with clear message when user is logged out
- **FR-022**: Tests for auth-enhanced tools (`search_packages`, `search_documentation`, `search_forum`) MUST validate public-data behavior when logged out and work identically when logged in
- **FR-023**: Test fixtures/markers MUST provide mechanism to declare tool's auth category (independent, required, enhanced)
- **FR-024**: Test output MUST clearly indicate which tests were skipped due to auth state and how to run them with auth

**Infrastructure**:
- **FR-010**: All new tests MUST follow existing test patterns in `tests/qa/mcp_tools/` (class-based, use fixtures, proper marks)
- **FR-011**: All new tests MUST be transport-agnostic (work across all `--mcp-profile` values)
- **FR-012**: Tool constants in `tests/qa/mcp_tools/common/constants/mcp_tools.py` MUST be extended with new tool names
- **FR-013**: Documentation in `tests/qa/mcp_tools/_docs/test_design.md` MUST be updated to reflect new tool coverage

### Implementation Phases

| Phase | Scope | Tools Affected |
|-------|-------|----------------|
| **Phase 1** | At least 1 positive test per tool | All 20 tools (16 new + 4 existing gaps) |
| **Phase 2** | Additional positive tests for complex params | Tools with OR params, multiple modes |
| **Phase 3** | Negative tests (1 per tool minimum) | All 20 tools |
| **Phase 4** | Hang-stress tests | `repoquery`, `search_packages` (new); existing already covered |

### Key Entities

- **MCP Tool**: A callable function exposed via MCP protocol with defined input schema and response shape
- **Test Scenario**: A single test case exercising one tool with specific inputs and expected outputs
- **Transport Profile**: Configuration determining how test communicates with MCP server (`http-http`, `stdio-http`, `stdio-stdio`)
- **MCP Server**: A proxied backend providing tools (environments-mcp, conda-meta-mcp, search-mcp)
- **Auth Service**: Component that programmatically obtains Anaconda session tokens via OAuth API flow using credentials
- **Auth State**: Current authentication status (logged-in or logged-out) that affects tool behavior and test expectations
- **Tool Auth Category**: Classification of a tool's authentication dependency: auth-independent (works same either way), auth-required (needs login), or auth-enhanced (works both ways, different results)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 20 tools have at least one happy-path test
- **SC-002**: Tool coverage table in `test_design.md` shows checkmarks for all tools in "Happy path" column
- **SC-003**: Test suite passes on declared supported profile without failures in new tests
- **SC-004**: No new tests introduce flaky behavior (pass rate >99% across 10 consecutive runs — i.e., at most 1 failure per 100 test invocations total)
- **SC-005**: Tool constants file includes all 20 tools organized by server
- **SC-006**: search-mcp tests pass in GitHub Actions workflow using programmatic authentication (no pre-stored static tokens)
- **SC-007**: Test suite passes when run without authentication (logged-out mode): auth-independent tests pass, auth-required tests skip, auth-enhanced tests run public-only
- **SC-008**: Test suite passes when run with authentication (logged-in mode): all tests pass including auth-required and auth-enhanced tests
- **SC-009**: Test output clearly reports auth state and lists any skipped tests with reason

## Assumptions

### Infrastructure Prerequisites

- PRs for search-mcp and conda-meta-mcp integration are merged to main branch before test implementation begins
- Server configurations in `mcp_compose.toml` and `mcp_compose.toml.template` include all three MCP servers (conda, conda-meta, search)
- QA test environment setup documentation (`tests/qa/mcp_tools/README.md`) is updated with conda-meta-mcp and search-mcp requirements

### Test Environment

- The 20 tools to cover are distributed across 3 MCP servers: environments-mcp (6), conda-meta-mcp (9), search-mcp (5)
- Existing test patterns and fixtures (`call_tool`, `conda_env`, etc.) are sufficient for environments-mcp tests
- All tests use real integration (no mocks): environments-mcp uses local conda, conda-meta-mcp queries public conda channels, search-mcp calls anaconda.com API
- Test environment has network access to public conda channels (defaults, conda-forge) and anaconda.com
- conda-meta-mcp server must be installed via `cmm` command (`pip install conda-meta-mcp`) in server environment
- search-mcp tests require valid Anaconda authentication; tokens are session-scoped and must be obtained programmatically at runtime via OAuth API flow

### Implementation

- Hang-stress tests for new tools are desirable but not blocking for this feature (can be added incrementally)

## Clarifications

### Session 2026-05-14

- Q: Should tests use live network calls or mocked responses for conda-meta-mcp and search-mcp? → A: Live integration tests - all servers run locally, conda-meta-mcp queries public channels, search-mcp calls real anaconda.com API
- Q: What is the implementation priority order? → A: Phased approach: (1) At least one positive test per tool across all MCPs, (2) Additional positive tests for complex parameter sets, (3) Negative tests (1 per tool), (4) Hang-stress tests (1-2 tools per MCP based on risk)
- Q: Which tools for hang-stress coverage per MCP? → A: conda-meta-mcp: `repoquery` (libmamba solver, large results); search-mcp: `search_packages` (upstream HTTP, complex filtering). environments-mcp already has coverage.

### Session 2026-05-15

- Q: How should search-mcp authentication work in CI/GH workflows? → A: Tokens are session-scoped and expire, so static tokens in secrets won't work reliably. Implement programmatic OAuth 2-step login (like anaconda-desktop's `api-auth-service.ts`): (1) POST authorize to get state, (2) POST login with credentials to get session token. Credentials (email/password) stored in `.env` locally or GitHub secrets for CI.
- Q: Reference implementation for API auth? → A: `/Users/iiliukhina/projects/anaconda-desktop/src/__tests__/e2e/rest-api/api-auth-service.ts` - REST API class with `authorize()` and `login()` methods implementing the OAuth flow.

## References

- environments-mcp: https://github.com/anaconda/environments-mcp
- conda-meta-mcp: https://github.com/conda-incubator/conda-meta-mcp
- search-mcp: https://github.com/anaconda/anaconda-mcp-search
- conda-meta-mcp blog: https://conda.org/blog/conda-meta-mcp/
- API auth reference implementation: `anaconda-desktop/src/__tests__/e2e/rest-api/api-auth-service.ts` (OAuth 2-step login pattern)

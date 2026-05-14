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
| `search_environments` | `query` | (TBD - check source) | Basic search |

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

### Edge Cases

**environments-mcp**:
- What happens when `conda_list_environments` is called when no environments exist? (Should return empty list or just base)
- What happens when `conda_list_environment_packages` is called on an environment with no user-installed packages? (Should return base packages or empty)
- What happens when `conda_create_environment` is called with an already existing environment name? (Should return error)
- What happens when `conda_remove_environment` is called on base environment? (Should be rejected)
- What happens when `conda_remove_packages` is called with a package that isn't installed? (Should return appropriate error)

**conda-meta-mcp**:
- What happens when `package_search` finds no results? (Should return empty list, not error)
- What happens when `import_mapping` is given an unknown import? (Should return empty or not-found response)
- What happens when `repoquery` is called with an invalid package name? (Should return appropriate error)

**search-mcp**:
- What happens when search tools are called with empty query? (Should return error or empty results)
- What happens when search tools have network issues? (Should return appropriate timeout/error)

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

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 20 tools have at least one happy-path test
- **SC-002**: Tool coverage table in `test_design.md` shows checkmarks for all tools in "Happy path" column
- **SC-003**: Test suite passes on declared supported profile without failures in new tests
- **SC-004**: No new tests introduce flaky behavior (pass rate >99% across 10 consecutive runs)
- **SC-005**: Tool constants file includes all 20 tools organized by server

## Assumptions

- The 20 tools to cover are distributed across 3 MCP servers: environments-mcp (6), conda-meta-mcp (9), search-mcp (5)
- Existing test patterns and fixtures (`call_tool`, `conda_env`, etc.) are sufficient for environments-mcp tests
- All tests use real integration (no mocks): environments-mcp uses local conda, conda-meta-mcp queries public conda channels, search-mcp calls anaconda.com API
- Test environment has network access to public conda channels (defaults, conda-forge) and anaconda.com
- conda-meta-mcp server must be installed via `cmm` command in server environment
- Hang-stress tests for new tools are desirable but not blocking for this feature (can be added incrementally)

## Clarifications

### Session 2026-05-14

- Q: Should tests use live network calls or mocked responses for conda-meta-mcp and search-mcp? → A: Live integration tests - all servers run locally, conda-meta-mcp queries public channels, search-mcp calls real anaconda.com API
- Q: What is the implementation priority order? → A: Phased approach: (1) At least one positive test per tool across all MCPs, (2) Additional positive tests for complex parameter sets, (3) Negative tests (1 per tool), (4) Hang-stress tests (1-2 tools per MCP based on risk)
- Q: Which tools for hang-stress coverage per MCP? → A: conda-meta-mcp: `repoquery` (libmamba solver, large results); search-mcp: `search_packages` (upstream HTTP, complex filtering). environments-mcp already has coverage.

## References

- environments-mcp: https://github.com/anaconda/environments-mcp
- conda-meta-mcp: https://github.com/conda-incubator/conda-meta-mcp
- search-mcp: https://github.com/anaconda/anaconda-mcp-search
- conda-meta-mcp blog: https://conda.org/blog/conda-meta-mcp/

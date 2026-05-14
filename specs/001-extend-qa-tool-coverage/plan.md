# Implementation Plan: Extend QA Tool Test Coverage

**Branch**: `001-extend-qa-tool-coverage` | **Date**: 2026-05-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-extend-qa-tool-coverage/spec.md`

## Summary

Extend QA-owned MCP tool tests to achieve complete coverage across all 20 tools from 3 MCP servers (environments-mcp: 6, conda-meta-mcp: 9, search-mcp: 5). Currently, only 4 tools have any test coverage, all in environments-mcp. Implementation follows a phased approach: positive tests first, then complex parameter scenarios, negative tests, and finally hang-stress tests for high-risk tools.

## Technical Context

**Language/Version**: Python 3.11+ (test suite runs in `anaconda-mcp-qa` conda env)

**Primary Dependencies**: pytest, httpx (HTTP transport), mcp-compose (server orchestration)

**Storage**: N/A (tests use live MCP servers, no persistent storage)

**Testing**: pytest with custom fixtures (`call_tool`, `conda_env`, `call_no_hang_unified`)

**Target Platform**: Linux/macOS CI runners with conda, network access to public channels and anaconda.com

**Project Type**: Test suite extension (QA)

**Performance Goals**: Each test completes within `TOOL_CALL_WALL_SECONDS` (single call) or 60s per iteration (hang-stress)

**Constraints**: Tests must be transport-agnostic, deterministic, and pass on declared supported profiles

**Scale/Scope**: 20 tools × (happy path + error path + hang-stress where applicable) = ~40-50 test methods

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. MCP Server Composition** | ✅ Pass | Tests exercise tools via mcp-compose; tool contracts verified |
| **II. Type Safety** | ✅ Pass | Tests use typed enums (`Tools`, `*Args`), validators have type hints |
| **III. QA-Owned Test Standards** | ✅ Pass | Tests in `tests/qa/mcp_tools/`, follow established patterns, transport-agnostic |
| **IV. Observability** | ✅ Pass | Tests validate well-formed MCP responses, use logging |

**Constitution Requirements Applied**:
- All new tests MUST pass on profiles declared as supported
- Tests MUST be deterministic: same input → same output
- Dual environment setup required: `anaconda-mcp-qa` + server env with all MCP servers
- Hang-stress tests use 20 iterations with timeout guards
- Tool constants organized in `mcp_tools.py` by server

## Project Structure

### Documentation (this feature)

```text
specs/001-extend-qa-tool-coverage/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (test entity model)
├── checklists/          # Quality validation
│   └── requirements.md
└── tasks.md             # Phase 2 output (from /speckit-tasks)
```

### Source Code (test files)

```text
tests/qa/mcp_tools/
├── _docs/
│   └── test_design.md           # Update with new tool coverage table
├── common/
│   ├── constants/
│   │   └── mcp_tools.py         # Extend with conda-meta and search-mcp tools
│   └── utils/
│       └── response_validators.py  # Add validators for new response shapes
├── conftest.py                  # Existing fixtures (no changes expected)
│
│ # Existing tests (environments-mcp)
├── test_create_environment_root_path.py
├── test_env_name_resolution.py
├── test_guard_happy_path_hang.py
├── test_guard_install_nonexistent_pkg.py
├── test_guard_proxy_error_hang.py
├── test_install_existing_package.py
│
│ # New tests - environments-mcp gaps
├── test_list_environment_packages.py      # FR-001: happy path
├── test_remove_packages.py                # FR-002: happy path
├── test_remove_environment_happy.py       # FR-003: happy path
├── test_create_environment_error.py       # FR-004: error path
│
│ # New tests - conda-meta-mcp (9 tools)
├── test_conda_meta_info.py                # info tool
├── test_conda_meta_cache.py               # cache_maintenance tool
├── test_conda_meta_cli_help.py            # cli_help tool
├── test_conda_meta_file_path.py           # file_path_search tool
├── test_conda_meta_import_mapping.py      # import_mapping tool
├── test_conda_meta_package_insights.py    # package_insights tool
├── test_conda_meta_package_search.py      # package_search tool
├── test_conda_meta_pypi_to_conda.py       # pypi_to_conda tool
├── test_conda_meta_repoquery.py           # repoquery tool (+ hang-stress)
│
│ # New tests - search-mcp (5 tools)
├── test_search_packages.py                # search_packages (+ hang-stress)
├── test_search_documentation.py           # search_documentation
├── test_search_forum.py                   # search_forum
├── test_search_collections_files.py       # search_collections_and_files
└── test_search_environments.py            # search_environments
```

**Structure Decision**: Flat file structure per test module (matching existing pattern). Each test file covers one tool with happy/error/stress scenarios as class methods.

## Complexity Tracking

No constitution violations. All tests follow established patterns:
- Class-based test structure
- Fixtures for tool invocation and environment setup
- Validators for response shape assertions
- Marks for categorization (`slow`, `regression`, `hang_stress`)

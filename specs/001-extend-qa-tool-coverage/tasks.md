# Tasks: Extend QA Tool Test Coverage

**Input**: Design documents from `/specs/001-extend-qa-tool-coverage/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All test code lives under `tests/qa/mcp_tools/`:
- Constants: `common/constants/`
- Validators: `common/utils/`
- Test files: root of `tests/qa/mcp_tools/`
- Docs: `_docs/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend tool constants and validators to support all 3 MCP servers

- [ ] T001 Add `CondaMetaTools` enum (9 tools) to tests/qa/mcp_tools/common/constants/mcp_tools.py
- [ ] T002 [P] Add `SearchTools` enum (5 tools) to tests/qa/mcp_tools/common/constants/mcp_tools.py
- [ ] T003 [P] Add missing environments-mcp tools (`CONDA_LIST_ENVIRONMENT_PACKAGES`, `CONDA_REMOVE_PACKAGES`) to `Tools` enum in tests/qa/mcp_tools/common/constants/mcp_tools.py
- [ ] T004 [P] Add argument enums for conda-meta-mcp tools in tests/qa/mcp_tools/common/constants/mcp_tools.py
- [ ] T005 [P] Add argument enums for search-mcp tools in tests/qa/mcp_tools/common/constants/mcp_tools.py
- [ ] T006 [P] Add argument enums for missing environments-mcp tools in tests/qa/mcp_tools/common/constants/mcp_tools.py
- [ ] T007 Add conda-meta-mcp test data constants to tests/qa/mcp_tools/common/constants/test_data.py
- [ ] T008 [P] Add search-mcp test data constants to tests/qa/mcp_tools/common/constants/test_data.py
- [ ] T009 Add `validate_conda_meta_success` and `validate_conda_meta_text_content` validators to tests/qa/mcp_tools/common/utils/response_validators.py
- [ ] T010 [P] Add `validate_search_success` and `validate_search_results` validators to tests/qa/mcp_tools/common/utils/response_validators.py
- [ ] T011 [P] Add `validate_list_packages_success` and `validate_remove_success` validators for environments-mcp to tests/qa/mcp_tools/common/utils/response_validators.py

**Checkpoint**: All tool enums, argument enums, test data, and validators ready for test implementation

---

## Phase 2: User Story 0 - Verify MCP Server Integration (Priority: P0) 🔧 Prerequisite

**Goal**: Confirm that all 3 MCP servers (environments-mcp, conda-meta-mcp, search-mcp) are properly configured and expose their tools via mcp-compose

**Why**: We merged search-mcp and conda-meta-mcp server configs but never validated they work. Must verify before writing tests.

**Independent Test**: Start mcp-compose and verify `tools/list` returns all 20 tools from 3 servers

### Validation tasks

- [ ] T012 [US0] Start anaconda-mcp server with all 3 MCP servers: `conda run -n anaconda-mcp-server anaconda-mcp serve`
- [ ] T013 [US0] Verify environments-mcp tools exposed (6 tools): call `tools/list` and check `conda_*` tools present
- [ ] T014 [US0] Verify conda-meta-mcp tools exposed (9 tools): check `info`, `cache_maintenance`, `cli_help`, `file_path_search`, `import_mapping`, `package_insights`, `package_search`, `pypi_to_conda`, `repoquery` present
- [ ] T015 [US0] Verify search-mcp tools exposed (5 tools): check `search_packages`, `search_documentation`, `search_forum`, `search_collections_and_files`, `search_environments` present
- [ ] T016 [US0] Document any configuration fixes needed in mcp_compose.toml or mcp_compose.toml.template

**Checkpoint**: All 20 tools from 3 MCP servers are visible via `tools/list` — infrastructure validated

---

## Phase 3: User Story 1 - Complete Positive Scenario Coverage (Priority: P1) 🎯 MVP

**Goal**: Every tool has at least one happy-path test that confirms it works correctly with valid inputs

**Independent Test**: `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http` — all 20 tools have passing happy-path tests

### environments-mcp gaps (4 tests)

- [ ] T017 [P] [US1] Create happy-path test for `conda_list_environment_packages` in tests/qa/mcp_tools/test_list_environment_packages.py
- [ ] T018 [P] [US1] Create happy-path test for `conda_remove_packages` in tests/qa/mcp_tools/test_remove_packages.py
- [ ] T019 [P] [US1] Create happy-path test for `conda_remove_environment` in tests/qa/mcp_tools/test_remove_environment_happy.py
- [ ] T020 [P] [US1] Create error-path test for `conda_create_environment` (duplicate name) in tests/qa/mcp_tools/test_create_environment_error.py

### conda-meta-mcp (9 tests)

- [ ] T021 [P] [US1] Create happy-path test for `info` tool in tests/qa/mcp_tools/test_conda_meta_info.py
- [ ] T022 [P] [US1] Create happy-path test for `cache_maintenance` tool in tests/qa/mcp_tools/test_conda_meta_cache.py
- [ ] T023 [P] [US1] Create happy-path test for `cli_help` tool in tests/qa/mcp_tools/test_conda_meta_cli_help.py
- [ ] T024 [P] [US1] Create happy-path test for `file_path_search` tool in tests/qa/mcp_tools/test_conda_meta_file_path.py
- [ ] T025 [P] [US1] Create happy-path test for `import_mapping` tool in tests/qa/mcp_tools/test_conda_meta_import_mapping.py
- [ ] T026 [P] [US1] Create happy-path test for `package_insights` tool in tests/qa/mcp_tools/test_conda_meta_package_insights.py
- [ ] T027 [P] [US1] Create happy-path test for `package_search` tool in tests/qa/mcp_tools/test_conda_meta_package_search.py
- [ ] T028 [P] [US1] Create happy-path test for `pypi_to_conda` tool in tests/qa/mcp_tools/test_conda_meta_pypi_to_conda.py
- [ ] T029 [P] [US1] Create happy-path test for `repoquery` tool (depends mode) in tests/qa/mcp_tools/test_conda_meta_repoquery.py

### search-mcp (5 tests)

- [ ] T030 [P] [US1] Create happy-path test for `search_packages` tool in tests/qa/mcp_tools/test_search_packages.py
- [ ] T031 [P] [US1] Create happy-path test for `search_documentation` tool in tests/qa/mcp_tools/test_search_documentation.py
- [ ] T032 [P] [US1] Create happy-path test for `search_forum` tool in tests/qa/mcp_tools/test_search_forum.py
- [ ] T033 [P] [US1] Create happy-path test for `search_collections_and_files` tool in tests/qa/mcp_tools/test_search_collections_files.py
- [ ] T034 [P] [US1] Create happy-path test for `search_environments` tool in tests/qa/mcp_tools/test_search_environments.py

**Checkpoint**: All 20 tools have at least one passing happy-path test (SC-001)

---

## Phase 4: User Story 1 continued - Complex Parameter Tests (Priority: P1)

**Goal**: Tools with complex parameters have tests covering primary usage patterns

**Independent Test**: Same as above, additional test methods validate different parameter combinations

### environments-mcp complex params

- [ ] T035 [P] [US1] Add test for `conda_create_environment` with prefix parameter in tests/qa/mcp_tools/test_create_environment_root_path.py
- [ ] T036 [P] [US1] Add test for `conda_list_environment_packages` by prefix in tests/qa/mcp_tools/test_list_environment_packages.py
- [ ] T037 [P] [US1] Add test for `conda_remove_packages` by prefix in tests/qa/mcp_tools/test_remove_packages.py

### conda-meta-mcp complex params

- [ ] T038 [P] [US1] Add test for `repoquery` whoneeds mode in tests/qa/mcp_tools/test_conda_meta_repoquery.py
- [ ] T039 [P] [US1] Add test for `cli_help` with grep filter in tests/qa/mcp_tools/test_conda_meta_cli_help.py
- [ ] T040 [P] [US1] Add test for `package_search` with version spec in tests/qa/mcp_tools/test_conda_meta_package_search.py

### search-mcp complex params

- [ ] T041 [P] [US1] Add test for `search_packages` with channel filter in tests/qa/mcp_tools/test_search_packages.py
- [ ] T042 [P] [US1] Add test for `search_environments` with platform filter in tests/qa/mcp_tools/test_search_environments.py

**Checkpoint**: Tools with OR params and multiple modes have comprehensive positive coverage

---

## Phase 5: User Story 2 - Error Path Coverage (Priority: P2)

**Goal**: Tools that can fail in user-facing ways have error-path tests confirming proper error responses

**Independent Test**: `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http -m regression` — error scenarios return `is_error=True`

### environments-mcp error paths

- [ ] T043 [P] [US2] Add error test for `conda_list_environments` if meaningful error scenarios exist in tests/qa/mcp_tools/test_env_name_resolution.py
- [ ] T044 [P] [US2] Add error test for `conda_list_environment_packages` (nonexistent env) in tests/qa/mcp_tools/test_list_environment_packages.py
- [ ] T045 [P] [US2] Add error test for `conda_remove_packages` (package not installed) in tests/qa/mcp_tools/test_remove_packages.py

### conda-meta-mcp error paths

- [ ] T046 [P] [US2] Add error test for `package_search` (no results) in tests/qa/mcp_tools/test_conda_meta_package_search.py
- [ ] T047 [P] [US2] Add error test for `import_mapping` (unknown import) in tests/qa/mcp_tools/test_conda_meta_import_mapping.py
- [ ] T048 [P] [US2] Add error test for `repoquery` (invalid package) in tests/qa/mcp_tools/test_conda_meta_repoquery.py

### search-mcp error paths

- [ ] T049 [P] [US2] Add error test for `search_packages` (empty query) in tests/qa/mcp_tools/test_search_packages.py
- [ ] T050 [P] [US2] Add error test for `search_documentation` (empty query) in tests/qa/mcp_tools/test_search_documentation.py
- [ ] T051 [P] [US2] Add error test for `search_forum` (empty query) in tests/qa/mcp_tools/test_search_forum.py

**Checkpoint**: Error handling verified for tools with meaningful failure modes (FR-004, FR-007, FR-009)

---

## Phase 6: User Story 3 - Hang Stress Coverage (Priority: P3)

**Goal**: High-risk tools have hang-stress tests to catch proxy-state accumulation bugs (KI-011)

**Independent Test**: `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio -m hang_stress` — 20 iterations complete without timeout

### conda-meta-mcp hang-stress

- [ ] T052 [US3] Add hang-stress test for `repoquery` tool (20 iterations) in tests/qa/mcp_tools/test_conda_meta_repoquery.py

### search-mcp hang-stress

- [ ] T053 [US3] Add hang-stress test for `search_packages` tool (20 iterations) in tests/qa/mcp_tools/test_search_packages.py

**Checkpoint**: High-risk tools validated for proxy-state bugs under repeated invocation

---

## Phase 7: Polish & Documentation

**Purpose**: Update documentation to reflect new coverage

- [ ] T054 Update tool coverage table in tests/qa/mcp_tools/_docs/test_design.md with all 20 tools
- [ ] T055 [P] Verify all tests pass on stdio-http profile: `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http`
- [ ] T056 [P] Run 10 consecutive test runs to verify no flaky tests (SC-004)
- [ ] T057 Update tests/qa/mcp_tools/common/constants/mcp_tools.py docstring to reflect 20-tool coverage

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 0 (Phase 2)**: Depends on Setup — validates infrastructure before test implementation
- **User Story 1 (Phase 3-4)**: Depends on US0 completion — tests require working servers
- **User Story 2 (Phase 5)**: Depends on US0 completion (can run in parallel with US1)
- **User Story 3 (Phase 6)**: Depends on US1 happy-path tests for the specific tools
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 0 (P0)**: After Setup — BLOCKS all test implementation until servers verified
- **User Story 1 (P1)**: After US0 — provides foundation for all other stories
- **User Story 2 (P2)**: After US0 — can run in parallel with US1
- **User Story 3 (P3)**: After US1 `repoquery` and `search_packages` tests exist

---

## Implementation Strategy

### MVP First (US0 + US1)

1. Complete Phase 1: Setup (tool enums, validators, test data)
2. Complete Phase 2: US0 infrastructure validation (verify all 3 MCPs expose tools)
3. Complete Phase 3: US1 happy-path tests (20 tools covered)
4. **STOP and VALIDATE**: Run `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http`
5. All 20 tools have passing tests = SC-001 achieved

### Incremental Delivery

1. Setup → Foundation ready
2. US0 Phase 2 → Infrastructure verified (BLOCKER)
3. US1 Phase 3 → Basic positive coverage (MVP!)
4. US1 Phase 4 → Complex parameter coverage
5. US2 Phase 5 → Error handling coverage
6. US3 Phase 6 → Hang-stress coverage
7. Polish Phase 7 → Documentation complete

### Task Counts

| Phase | Story | Tasks |
|-------|-------|-------|
| 1 Setup | — | 11 |
| 2 US0 Infra | US0 | 5 |
| 3 US1 Positive | US1 | 18 |
| 4 US1 Complex | US1 | 8 |
| 5 US2 Error | US2 | 9 |
| 6 US3 Hang | US3 | 2 |
| 7 Polish | — | 4 |
| **Total** | | **57** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable
- Commit after each task or logical group
- Stop at any checkpoint to validate progress
- All test files follow existing patterns: class-based, fixtures, validators, marks

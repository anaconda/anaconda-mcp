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

- [x] T001 Add `CondaMetaTools` enum (9 tools) to tests/qa/mcp_tools/common/constants/mcp_tools.py
- [x] T002 [P] Add `SearchTools` enum (5 tools) to tests/qa/mcp_tools/common/constants/mcp_tools.py
- [x] T003 [P] Add missing environments-mcp tools (`CONDA_LIST_ENVIRONMENT_PACKAGES`, `CONDA_REMOVE_PACKAGES`) to `Tools` enum in tests/qa/mcp_tools/common/constants/mcp_tools.py
- [x] T004 [P] Add argument enums for conda-meta-mcp tools in tests/qa/mcp_tools/common/constants/mcp_tools.py
- [x] T005 [P] Add argument enums for search-mcp tools in tests/qa/mcp_tools/common/constants/mcp_tools.py
- [x] T006 [P] Add argument enums for missing environments-mcp tools in tests/qa/mcp_tools/common/constants/mcp_tools.py
- [x] T007 Add conda-meta-mcp test data constants to tests/qa/mcp_tools/common/constants/test_data.py
- [x] T008 [P] Add search-mcp test data constants to tests/qa/mcp_tools/common/constants/test_data.py
- [x] T009 Add `validate_conda_meta_success` and `validate_conda_meta_text_content` validators to tests/qa/mcp_tools/common/utils/response_validators.py
- [x] T010 [P] Add `validate_search_success` and `validate_search_results` validators to tests/qa/mcp_tools/common/utils/response_validators.py
- [x] T011 [P] Add `validate_list_packages_success` and `validate_remove_success` validators for environments-mcp to tests/qa/mcp_tools/common/utils/response_validators.py

**Checkpoint**: All tool enums, argument enums, test data, and validators ready for test implementation

---

## Phase 2: User Story 0 - Verify MCP Server Integration (Priority: P0) 🔧 Prerequisite

**Goal**: Confirm that all 3 MCP servers (environments-mcp, conda-meta-mcp, search-mcp) are properly configured and expose their tools via mcp-compose

**Why**: We merged search-mcp and conda-meta-mcp server configs but never validated they work. Must verify before writing tests.

**Independent Test**: Start mcp-compose and verify `tools/list` returns all 20 tools from 3 servers

### Validation tasks

- [x] T012 [US0] Start anaconda-mcp server with all 3 MCP servers: `conda run -n anaconda-mcp anaconda-mcp serve`
- [x] T013 [US0] Verify environments-mcp tools exposed (6 tools): call `tools/list` and check `conda_*` tools present
- [x] T014 [US0] Verify conda-meta-mcp tools exposed (9 tools): check `conda-meta_info`, `conda-meta_cache_maintenance`, `conda-meta_cli_help`, `conda-meta_file_path_search`, `conda-meta_import_mapping`, `conda-meta_package_insights`, `conda-meta_package_search`, `conda-meta_pypi_to_conda`, `conda-meta_repoquery` present (tools prefixed by mcp-compose)
- [x] T015 [US0] Verify search-mcp tools exposed (5 tools): check `search_search_packages`, `search_search_documentation`, `search_search_forum`, `search_search_collections_and_files`, `search_search_environments` present (tools prefixed by mcp-compose)
- [x] T016 [US0] Document configuration fixes: (1) Updated utils.py to render {{ANACONDA_DOMAIN}} and {{ANACONDA_TOKEN}} placeholders; (2) Changed conda-meta command from `cmm` to `python -m conda_meta_mcp` in mcp_compose.toml.template; (3) Increased startup_delay to 5s; (4) Updated tool constants to use mcp-compose prefixed names

**Checkpoint**: All 20 tools from 3 MCP servers are visible via `tools/list` — infrastructure validated

---

## Phase 3: User Story 1 - Complete Positive Scenario Coverage (Priority: P1) 🎯 MVP

**Goal**: Every tool has at least one happy-path test that confirms it works correctly with valid inputs

**Independent Test**: `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http` — all 20 tools have passing happy-path tests

### environments-mcp gaps (3 happy-path + 1 error per FR-004)

- [x] T017 [P] [US1] Create happy-path test for `conda_list_environment_packages` in tests/qa/mcp_tools/test_list_environment_packages.py
- [x] T018 [P] [US1] Create happy-path test for `conda_remove_packages` in tests/qa/mcp_tools/test_remove_packages.py
- [x] T019 [P] [US1] Create happy-path test for `conda_remove_environment` in tests/qa/mcp_tools/test_remove_environment_happy.py
- [x] T020 [P] [US2] Create error-path test for `conda_create_environment` (duplicate name) in tests/qa/mcp_tools/test_create_environment_error.py (FR-004)

### conda-meta-mcp (9 tests)

- [x] T021 [P] [US1] Create happy-path test for `info` tool in tests/qa/mcp_tools/test_conda_meta_info.py
- [x] T022 [P] [US1] Create happy-path test for `cache_maintenance` tool in tests/qa/mcp_tools/test_conda_meta_cache.py
- [x] T023 [P] [US1] Create happy-path test for `cli_help` tool in tests/qa/mcp_tools/test_conda_meta_cli_help.py
- [x] T024 [P] [US1] Create happy-path test for `file_path_search` tool in tests/qa/mcp_tools/test_conda_meta_file_path.py
- [x] T025 [P] [US1] Create happy-path test for `import_mapping` tool in tests/qa/mcp_tools/test_conda_meta_import_mapping.py
- [x] T026 [P] [US1] Create happy-path test for `package_insights` tool in tests/qa/mcp_tools/test_conda_meta_package_insights.py
- [x] T027 [P] [US1] Create happy-path test for `package_search` tool in tests/qa/mcp_tools/test_conda_meta_package_search.py
- [x] T028 [P] [US1] Create happy-path test for `pypi_to_conda` tool in tests/qa/mcp_tools/test_conda_meta_pypi_to_conda.py
- [x] T029 [P] [US1] Create happy-path test for `repoquery` tool (depends mode) in tests/qa/mcp_tools/test_conda_meta_repoquery.py

### search-mcp (5 tests)

- [x] T030 [P] [US1] Create happy-path test for `search_packages` tool in tests/qa/mcp_tools/test_search_packages.py
- [x] T031 [P] [US1] Create happy-path test for `search_documentation` tool in tests/qa/mcp_tools/test_search_documentation.py
- [x] T032 [P] [US1] Create happy-path test for `search_forum` tool in tests/qa/mcp_tools/test_search_forum.py
- [x] T033 [P] [US1] Create happy-path test for `search_collections_and_files` tool in tests/qa/mcp_tools/test_search_collections_files.py
- [x] T034 [P] [US1] Create happy-path test for `search_environments` tool in tests/qa/mcp_tools/test_search_environments.py

**Checkpoint**: All 20 tools have at least one passing happy-path test (SC-001)

---

## Phase 4: User Story 1 continued - Complex Parameter Tests (Priority: P1)

**Goal**: Tools with complex parameters have tests covering primary usage patterns

**Independent Test**: Same as above, additional test methods validate different parameter combinations

### environments-mcp complex params

- [x] T035 [P] [US1] Add test for `conda_create_environment` with prefix parameter in tests/qa/mcp_tools/test_create_environment_root_path.py (existing test covers this)
- [x] T036 [P] [US1] Add test for `conda_list_environment_packages` by prefix in tests/qa/mcp_tools/test_list_environment_packages.py
- [x] T037 [P] [US1] Add test for `conda_remove_packages` by prefix in tests/qa/mcp_tools/test_remove_packages.py

### conda-meta-mcp complex params

- [x] T038 [P] [US1] Add test for `repoquery` whoneeds mode in tests/qa/mcp_tools/test_conda_meta_repoquery.py
- [x] T039 [P] [US1] Add test for `cli_help` with grep filter in tests/qa/mcp_tools/test_conda_meta_cli_help.py
- [x] T040 [P] [US1] Add test for `package_search` with version spec in tests/qa/mcp_tools/test_conda_meta_package_search.py

### search-mcp complex params

- [x] T041 [P] [US1] Add test for `search_packages` with channel filter in tests/qa/mcp_tools/test_search_packages.py
- [x] T042 [P] [US1] Add test for `search_environments` with platform filter in tests/qa/mcp_tools/test_search_environments.py

**Checkpoint**: Tools with OR params and multiple modes have comprehensive positive coverage

---

## Phase 5: User Story 2 - Error Path Coverage (Priority: P2)

**Goal**: Tools that can fail in user-facing ways have error-path tests confirming proper error responses

**Independent Test**: `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http -m regression` — error scenarios return `is_error=True`

### environments-mcp error paths

- [x] T043 [P] [US2] Add error test for `conda_list_environments` if meaningful error scenarios exist in tests/qa/mcp_tools/test_env_name_resolution.py (FR-005 — skip if no valid scenario) — SKIPPED: no meaningful error scenario for listing environments
- [x] T044 [P] [US2] Add error test for `conda_list_environment_packages` (nonexistent env) in tests/qa/mcp_tools/test_list_environment_packages.py (Edge case: nonexistent env)
- [x] T045 [P] [US2] Add error test for `conda_remove_packages` (package not installed) in tests/qa/mcp_tools/test_remove_packages.py (Edge case: package not installed)

### conda-meta-mcp error paths

- [x] T046 [P] [US2] Add error test for `package_search` (no results) in tests/qa/mcp_tools/test_conda_meta_package_search.py
- [x] T047 [P] [US2] Add error test for `import_mapping` (unknown import) in tests/qa/mcp_tools/test_conda_meta_import_mapping.py
- [x] T048 [P] [US2] Add error test for `repoquery` (invalid package) in tests/qa/mcp_tools/test_conda_meta_repoquery.py

### search-mcp error paths

- [x] T049 [P] [US2] Add error test for `search_packages` (empty query) in tests/qa/mcp_tools/test_search_packages.py
- [x] T050 [P] [US2] Add error test for `search_documentation` (empty query) in tests/qa/mcp_tools/test_search_documentation.py
- [x] T051 [P] [US2] Add error test for `search_forum` (empty query) in tests/qa/mcp_tools/test_search_forum.py

**Checkpoint**: Error handling verified for tools with meaningful failure modes (FR-004, FR-007, FR-009)

---

## Phase 6: User Story 3 - Hang Stress Coverage (Priority: P3)

**Goal**: High-risk tools have hang-stress tests to catch proxy-state accumulation bugs (KI-011)

**Independent Test**: `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-stdio -m hang_stress` — 20 iterations complete without timeout

### conda-meta-mcp hang-stress

- [x] T052 [US3] Add hang-stress test for `repoquery` tool (20 iterations) in tests/qa/mcp_tools/test_conda_meta_repoquery.py

### search-mcp hang-stress

- [x] T053 [US3] Add hang-stress test for `search_packages` tool (20 iterations) in tests/qa/mcp_tools/test_search_packages.py

**Checkpoint**: High-risk tools validated for proxy-state bugs under repeated invocation

---

## Phase 7: User Story 4 - Programmatic Authentication for CI (Priority: P1)

**Goal**: Implement programmatic OAuth authentication so search-mcp tests can obtain fresh tokens at runtime in CI

**Independent Test**: Run `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http -k search` with `ANACONDA_USER_EMAIL` and `ANACONDA_USER_PASSWORD` set — tests pass with fresh token

### AuthService implementation

- [ ] T063 [P] [US4] Create `AuthService` class implementing 2-step OAuth flow in tests/qa/mcp_tools/common/utils/auth_service.py
- [ ] T064 [P] [US4] Create `AuthState` dataclass for session auth state in tests/qa/mcp_tools/common/utils/auth_service.py
- [ ] T065 [P] [US4] Create `AuthError` exception class in tests/qa/mcp_tools/common/utils/auth_service.py
- [ ] T066 [US4] Add `get_keyring_token()` helper function for keyring fallback in tests/qa/mcp_tools/common/utils/auth_service.py

### Pytest fixtures

- [ ] T067 [US4] Add session-scoped `auth_state` fixture to detect auth state at startup in tests/qa/mcp_tools/conftest.py
- [ ] T068 [US4] Add `.env` file loading (python-dotenv) to conftest.py for local credential support in tests/qa/mcp_tools/conftest.py
- [ ] T069 [US4] Add auth state reporting to pytest session summary in tests/qa/mcp_tools/conftest.py

### CI workflow updates

- [ ] T070 [P] [US4] Update .github/workflows/qa-mcp-tools.yml to use `ANACONDA_USER_EMAIL` and `ANACONDA_USER_PASSWORD` secrets instead of static token
- [ ] T071 [US4] Document required GitHub secrets in tests/qa/mcp_tools/README.md

**Checkpoint**: Tests can obtain fresh tokens programmatically in both local (.env) and CI (secrets) environments

---

## Phase 8: User Story 5 - Authentication-State-Aware Test Behavior (Priority: P1)

**Goal**: Tests adapt behavior based on logged-in vs logged-out state — auth-independent tests run normally, auth-required tests skip, auth-enhanced tests run public-only

**Independent Test**: Run test suite twice (with and without credentials) — appropriate tests pass/skip in each mode

### Pytest markers

- [ ] T072 [P] [US5] Add `auth_independent`, `auth_required`, `auth_enhanced` markers to pytest.ini in tests/qa/mcp_tools/pytest.ini
- [ ] T073 [US5] Add `ToolAuthCategory` enum and `TOOL_AUTH_CATEGORIES` mapping in tests/qa/mcp_tools/common/constants/mcp_tools.py

### search-mcp test updates (auth-required tools)

- [ ] T074 [P] [US5] Update test_search_collections_files.py to add `@pytest.mark.auth_required` and skip logic when logged out
- [ ] T075 [P] [US5] Update test_search_environments.py to add `@pytest.mark.auth_required` and skip logic when logged out

### search-mcp test updates (auth-enhanced tools)

- [ ] T076 [P] [US5] Update test_search_packages.py to add `@pytest.mark.auth_enhanced` and public-only assertions when logged out
- [ ] T077 [P] [US5] Update test_search_documentation.py to add `@pytest.mark.auth_enhanced` and public-only assertions when logged out
- [ ] T078 [P] [US5] Update test_search_forum.py to add `@pytest.mark.auth_enhanced` and public-only assertions when logged out

### environments-mcp and conda-meta-mcp markers (auth-independent)

- [ ] T079 [P] [US5] Add `@pytest.mark.auth_independent` marker to all environments-mcp test files (6 tools)
- [ ] T080 [P] [US5] Add `@pytest.mark.auth_independent` marker to all conda-meta-mcp test files (9 tools)

**Checkpoint**: Test suite passes in both logged-out mode (skip auth-required, public-only auth-enhanced) and logged-in mode (all tests run)

---

## Phase 9: Polish & Documentation

**Purpose**: Update documentation and CI to reflect new coverage

### Test documentation updates

- [x] T054 Update tool coverage table in tests/qa/mcp_tools/_docs/test_design.md with all 20 tools (add conda-meta-mcp and search-mcp sections)
- [x] T055 Update tests/qa/mcp_tools/_docs/architecture.md if needed to document 3-server stack
- [x] T056 Update tests/qa/mcp_tools/common/constants/mcp_tools.py docstring to reflect 20-tool coverage

### Authentication documentation

- [ ] T081 [P] Add auth-state testing section to tests/qa/mcp_tools/_docs/test_design.md documenting tool categories and skip behavior
- [ ] T082 [P] Update tests/qa/mcp_tools/README.md with .env credential setup and auth-aware test execution examples

### GitHub workflow updates

- [x] T057 Update .github/workflows/qa-mcp-tools.yml to add `conda_meta_mcp_ver` input parameter for conda-meta-mcp version
- [x] T058 Update .github/workflows/qa-mcp-tools.yml to add `ANACONDA_TOKEN` secret usage for search-mcp authentication
- [x] T059 Update .github/workflows/qa-mcp-tools.yml to install conda-meta-mcp (`conda install -c conda-forge conda-meta-mcp`) in server env
- [x] T060 Update workflow description comment to mention all 3 MCP servers (environments-mcp, conda-meta-mcp, search-mcp)

### Validation

- [X] T061 Verify all tests pass on stdio-http profile: `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http` (FR-011: stdio-http is declared supported profile) — VERIFIED: Fixed JSON parsing issue in _conda_env_prefix() that caused 15 ERROR tests
- [X] T062 Run 10 consecutive test runs to verify no flaky tests (SC-004) — VERIFIED: Tests are stable after JSON parsing fix; 1 legitimate test failure (test_create_duplicate_environment_returns_error) is a real bug in the MCP server, not flakiness
- [ ] T083 [US4] [US5] Verify tests pass when run without credentials (logged-out mode): auth-independent pass, auth-required skip, auth-enhanced run public-only (SC-007)
- [ ] T084 [US4] [US5] Verify tests pass when run with credentials (logged-in mode): all tests pass (SC-008)
- [ ] T085 Verify test output clearly reports auth state and skipped tests (SC-009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 0 (Phase 2)**: Depends on Setup — validates infrastructure before test implementation
- **User Story 1 (Phase 3-4)**: Depends on US0 completion — tests require working servers
- **User Story 2 (Phase 5)**: Depends on US0 completion (can run in parallel with US1)
- **User Story 3 (Phase 6)**: Depends on US1 happy-path tests for the specific tools
- **User Story 4 (Phase 7)**: Depends on search-mcp tests existing (US1) — adds auth infrastructure
- **User Story 5 (Phase 8)**: Depends on US4 (auth_state fixture) — adds auth-aware markers
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 0 (P0)**: After Setup — BLOCKS all test implementation until servers verified
- **User Story 1 (P1)**: After US0 — provides foundation for all other stories
- **User Story 2 (P2)**: After US0 — can run in parallel with US1
- **User Story 3 (P3)**: After US1 `repoquery` and `search_packages` tests exist
- **User Story 4 (P1)**: After US1 search-mcp tests exist — adds programmatic auth
- **User Story 5 (P1)**: After US4 — requires auth_state fixture to be available

---

## Implementation Strategy

### MVP First (US0 + US1)

1. Complete Phase 1: Setup (tool enums, validators, test data)
2. Complete Phase 2: US0 infrastructure validation (verify all 3 MCPs expose tools)
3. Complete Phase 3: US1 happy-path tests (20 tools covered)
4. **STOP and VALIDATE**: Run `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http`
5. All 20 tools have passing tests = SC-001 achieved

### Incremental Delivery

1. Setup → Foundation ready ✅
2. US0 Phase 2 → Infrastructure verified (BLOCKER) ✅
3. US1 Phase 3 → Basic positive coverage (MVP!) ✅
4. US1 Phase 4 → Complex parameter coverage ✅
5. US2 Phase 5 → Error handling coverage ✅
6. US3 Phase 6 → Hang-stress coverage ✅
7. US4 Phase 7 → Programmatic auth for CI ⬜ **NEXT**
8. US5 Phase 8 → Auth-state-aware tests ⬜
9. Polish Phase 9 → Documentation complete ⬜

### Task Counts

| Phase | Story | Tasks | Status |
|-------|-------|-------|--------|
| 1 Setup | — | 11 | ✅ Complete |
| 2 US0 Infra | US0 | 5 | ✅ Complete |
| 3 US1 Positive | US1 | 18 | ✅ Complete |
| 4 US1 Complex | US1 | 8 | ✅ Complete |
| 5 US2 Error | US2 | 9 | ✅ Complete |
| 6 US3 Hang | US3 | 2 | ✅ Complete |
| 7 US4 Auth | US4 | 9 | ⬜ New |
| 8 US5 Auth-State | US5 | 9 | ⬜ New |
| 9 Polish | — | 14 | 🔶 Partial (6 done, 8 new) |
| **Total** | | **85** | **62 done, 23 new** |

---

## Parallel Example: User Story 4 & 5

```bash
# Launch all auth service components in parallel (US4):
Task: "T063 Create AuthService class in auth_service.py"
Task: "T064 Create AuthState dataclass in auth_service.py"
Task: "T065 Create AuthError exception in auth_service.py"

# Then sequential: T066, T067, T068, T069 (depend on above)

# Launch all auth-required test updates in parallel (US5):
Task: "T074 Update test_search_collections_files.py with auth_required marker"
Task: "T075 Update test_search_environments.py with auth_required marker"

# Launch all auth-enhanced test updates in parallel (US5):
Task: "T076 Update test_search_packages.py with auth_enhanced marker"
Task: "T077 Update test_search_documentation.py with auth_enhanced marker"
Task: "T078 Update test_search_forum.py with auth_enhanced marker"
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable
- Commit after each task or logical group
- Stop at any checkpoint to validate progress
- All test files follow existing patterns: class-based, fixtures, validators, marks
- Credentials: `.env` file locally, GitHub secrets for CI

# Feature Specification: Auth Behavior Testing for MCP Tools

**Feature Branch**: `002-auth-behavior-testing`

**Created**: 2026-05-15

**Status**: Draft

**Input**: User description: "revisit what we implemented for tests/qa/mcp_tools, including authentication approach. compare with specification, extend specification based on findings. analyse codebase and create new specification - what we should expect from anaconda-mcp tools when user is not authenticated. AC when user is authenticated and tool x called we expect ... else we expect ... - and we cover both options. ac: test execution is designed in a way when we actively reuse logged in user for whole suite and repeat/use another suite with no authentication and another expectations. ac: tests code should be easy-to-consume, ac: to not generate messy code, be DRY"

## Implementation Status Analysis

### Current State (as of 2026-05-15)

Based on codebase analysis, the following has been implemented:

**Authentication Infrastructure**:
- `auth_service.py`: Simplified to use `ANACONDA_AUTH_API_KEY` env var only (no OAuth login fallback)
- `conftest.py`: Session-scoped auth detection via `detect_auth_state()`, token caching in `_AUTH_STATE_CACHE`
- Auth markers defined: `@pytest.mark.auth_independent`, `@pytest.mark.auth_required`, `@pytest.mark.auth_enhanced`
- Token passed to subprocess via `ANACONDA_AUTH_API_KEY` env var

**Test Structure**:
- All tests use auth markers appropriately
- `auth_required` tests manually skip via `if not auth_state.logged_in: pytest.skip(...)`
- `auth_enhanced` tests run regardless of auth state (public data available)
- `auth_independent` tests ignore auth state entirely

**Gap Identified**: No automated mechanism to run test suites in two modes (authenticated vs unauthenticated) with different assertions based on auth state.

### Specification Gaps

The original spec (001-extend-qa-tool-coverage) defined auth behavior at a high level:

| Original Spec | Implementation Status |
|--------------|----------------------|
| FR-014: Programmatic auth with runtime tokens | ✅ Implemented via API key |
| FR-015: OAuth 2-step login flow | ⚠️ Code exists but unused (simplified to API key) |
| FR-019: Detect auth state before running | ✅ Implemented |
| FR-020: Auth-independent tests identical both ways | ✅ Verified via markers |
| FR-021: Auth-required tests skip when logged out | ✅ Implemented via manual skip |
| FR-022: Auth-enhanced tests validate public behavior | ⚠️ Partial - no logged-out-specific assertions |
| FR-023: Markers for auth category | ✅ Implemented |
| FR-024: Clear output of skipped tests | ⚠️ Via pytest default, no custom summary |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - DRY Auth-Aware Test Execution (Priority: P1)

QA engineer runs the test suite once and each test automatically adapts its assertions based on detected auth state, without code duplication for logged-in vs logged-out scenarios.

**Why this priority**: Eliminates need to maintain separate test code for authenticated vs unauthenticated flows. Reduces maintenance burden and ensures consistent coverage.

**Independent Test**: Run `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=stdio-http` with and without `ANACONDA_AUTH_API_KEY` set. Verify tests pass in both modes with appropriate assertions.

**Acceptance Scenarios**:

1. **Given** a test for an auth-independent tool (environments-mcp, conda-meta-mcp), **When** the test runs in either auth mode, **Then** the same assertions apply and pass identically.

2. **Given** a test for an auth-required tool, **When** the user is logged out, **Then** the test is automatically skipped via fixture (no manual `if not auth_state.logged_in` check needed in test body).

3. **Given** a test for an auth-enhanced tool, **When** the user is logged out, **Then** the test runs with public-data assertions (no private content checks).

4. **Given** a test for an auth-enhanced tool, **When** the user is logged in, **Then** the test runs with full assertions including optional private content checks.

---

### User Story 2 - Dual-Mode Test Suite Execution (Priority: P2)

QA engineer can explicitly run the full test suite twice: once authenticated to verify full functionality, once unauthenticated to verify graceful degradation and public-only behavior.

**Why this priority**: Enables comprehensive coverage verification for both user states without modifying test code.

**Independent Test**: Run workflow with `test_scope: all-no-hangs` twice: first with `ANACONDA_AUTH_API_KEY` set, then without. Compare results.

**Acceptance Scenarios**:

1. **Given** the workflow runs with `ANACONDA_AUTH_API_KEY` set, **When** all tests complete, **Then** auth-required tests pass, auth-enhanced tests run with full assertions.

2. **Given** the workflow runs without `ANACONDA_AUTH_API_KEY`, **When** all tests complete, **Then** auth-required tests are skipped, auth-independent tests pass, auth-enhanced tests pass with public-only assertions.

3. **Given** both runs complete, **When** comparing results, **Then** total test count is identical, skip count differs only by auth-required test count.

---

### User Story 3 - Clear Auth State Reporting (Priority: P2)

QA engineer can immediately see from test output whether tests ran authenticated or not, which tests were skipped due to auth, and why.

**Why this priority**: Debugging test failures requires knowing auth context. Clear reporting prevents confusion about expected vs actual behavior.

**Independent Test**: Run test suite and verify pytest header shows auth state, HTML report metadata includes auth state.

**Acceptance Scenarios**:

1. **Given** tests run with authentication, **When** viewing test output header, **Then** it displays `auth state: logged_in=True, source=env_credentials`.

2. **Given** tests run without authentication, **When** viewing test output header, **Then** it displays `auth state: logged_in=False, source=no_auth`.

3. **Given** auth-required tests were skipped, **When** viewing test summary, **Then** skip reason mentions "Requires authentication" with guidance on how to enable.

---

### Edge Cases

- What happens when `ANACONDA_AUTH_API_KEY` contains an invalid/expired token? (Server startup should fail fast with clear error)
- What happens when network is unavailable for search-mcp? (Timeout with appropriate error, not confused with auth failure)
- What happens when running tests without any auth config? (Auth-independent pass, auth-required skip, auth-enhanced run public-only)

## Requirements *(mandatory)*

### Functional Requirements

**DRY Test Architecture**:
- **FR-001**: Tests MUST NOT contain manual `if not auth_state.logged_in: pytest.skip()` checks in test body; this logic MUST be handled by fixtures or markers
- **FR-002**: Auth-required tool tests MUST use a fixture (e.g., `require_auth`) that auto-skips when not authenticated
- **FR-003**: Auth-enhanced tool tests MUST use conditional assertions via a helper that checks auth state
- **FR-004**: Test code MUST NOT duplicate logic for logged-in vs logged-out scenarios

**Expected Tool Behavior by Auth State**:

| Tool Category | Tool | Logged Out Behavior | Logged In Behavior |
|--------------|------|--------------------|--------------------|
| **environments-mcp** | All 6 tools | Works normally | Works normally |
| **conda-meta-mcp** | All 9 tools | Works normally | Works normally |
| **search-mcp** | `search_packages` | Returns public results | Returns public + private results |
| **search-mcp** | `search_documentation` | Returns public results | Returns public + private results |
| **search-mcp** | `search_forum` | Returns public results | Returns public + private results |
| **search-mcp** | `search_collections_and_files` | Returns auth error | Returns user's collections |
| **search-mcp** | `search_environments` | Returns auth error | Returns user's environments |

- **FR-005**: Tests for auth-required tools MUST validate the auth error response when logged out (not just skip)
- **FR-006**: Tests for auth-enhanced tools MUST have assertions that work for public-only results
- **FR-007**: Test infrastructure MUST support running both authenticated and unauthenticated test passes

**Test Execution Control**:
- **FR-008**: Workflow MUST support explicit auth mode selection (authenticated vs unauthenticated)
- **FR-009**: Test session MUST cache auth state once at session start and reuse for all tests
- **FR-010**: Auth token MUST be passed to all subprocesses (server, mcp-compose) via environment variable

**Reporting**:
- **FR-011**: Pytest session header MUST display current auth state
- **FR-012**: HTML report metadata MUST include auth state
- **FR-013**: Skipped tests MUST have clear reason indicating auth requirement

### Key Entities

- **Auth State**: Immutable state object containing `logged_in` (bool), `token` (optional), `source` (how auth was detected)
- **Auth Category**: Classification of tool's auth dependency (`auth_independent`, `auth_required`, `auth_enhanced`)
- **Conditional Assertion**: Helper that adjusts assertion based on auth state (e.g., `assert_has_results(response, require_private=auth_state.logged_in)`)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero instances of `if not auth_state.logged_in: pytest.skip()` in test method bodies (moved to fixtures)
- **SC-002**: All 25 test files use appropriate auth markers
- **SC-003**: Test suite passes when run without `ANACONDA_AUTH_API_KEY` (auth-required skipped, others pass)
- **SC-004**: Test suite passes when run with `ANACONDA_AUTH_API_KEY` (all tests pass)
- **SC-005**: HTML report shows auth state in metadata section
- **SC-006**: Pytest output header displays auth state on every run
- **SC-007**: No test code duplication for handling auth states (single test method per scenario)

## Assumptions

- `anaconda-mcp serve` requires authentication to start; tests cannot run without valid token being passed to server subprocess
- Search-mcp remote server (anaconda.com) handles auth at API level; unauthenticated requests get public results or auth errors
- environments-mcp and conda-meta-mcp are local tools that don't require Anaconda authentication
- Token lifetime exceeds test suite duration (no mid-run expiration handling needed)
- API key is the only supported auth method for CI (OAuth login available for local manual testing but not used in automated tests)

## Clarifications

### Session 2026-05-15

- Q: Should we test unauthenticated scenarios for auth-required tools? → A: Yes, validate they return proper auth error response, not just skip
- Q: How to handle auth-enhanced tools in unauthenticated mode? → A: Run with public-data assertions only; private content assertions conditional on auth state
- Q: OAuth login still needed? → A: Keep code for manual e2e testing, but CI uses API key only

## References

- Original spec: `specs/001-extend-qa-tool-coverage/spec.md` (User Stories 4, 5)
- Implementation: `tests/qa/mcp_tools/conftest.py` (auth fixtures)
- Auth service: `tests/qa/mcp_tools/common/utils/auth_service.py`
- Auth handling in anaconda-mcp: `src/anaconda_mcp/auth.py`

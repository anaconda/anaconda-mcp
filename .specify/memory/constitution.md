<!--
SYNC IMPACT REPORT
==================
Version Change: 0.0.0 → 1.0.0 (major - initial constitution)
Modified Principles: N/A (new document)
Added Sections:
  - Core Principles (4 principles)
  - QA Testing Standards
  - Code Quality
  - Git & PR Workflow
  - Governance
Removed Sections: N/A
Templates Requiring Updates:
  - .specify/templates/plan-template.md: ✅ aligned (Constitution Check section present)
  - .specify/templates/spec-template.md: ✅ aligned (mandatory sections match requirements)
  - .specify/templates/tasks-template.md: ✅ aligned (test-first guidance present)
Follow-up TODOs: None
-->

# Anaconda MCP Constitution

## Core Principles

### I. MCP Server Composition

All features MUST be implemented as composable MCP server components with defined tool interfaces.

- MCP tools are exposed via `mcp-compose` configuration
- Each tool MUST have a defined contract: input schema, output shape, error handling
- Transport-agnostic design: tools MUST function identically over HTTP and STDIO
- Clear separation between server composition (`anaconda-mcp`) and tool implementations (`environments-mcp`)
- Shared configuration MUST be defined in `mcp_compose.toml` with template overrides via `mcp_compose.toml.template`

**Rationale**: MCP's protocol abstraction requires consistent tool contracts regardless of transport; composition enables modular tool assembly without tight coupling.

### II. Type Safety & Code Quality

Python type hints MUST be enforced across all code paths.

- All public functions MUST have complete type annotations
- Use `mypy` strict mode for type checking
- Code MUST pass `ruff` linting before commits (enforced via pre-commit hooks)
- Shared types and interfaces MUST reside in dedicated modules
- All errors MUST be caught and reported, never swallowed silently

**Rationale**: Type safety prevents runtime errors in the MCP protocol layer where malformed responses can crash AI assistants; strict linting ensures consistent code quality.

### III. QA-Owned Test Standards

QA tests in `tests/qa/` MUST follow established patterns and documentation.

#### Transport Matrix Testing

- Tests MUST pass on profiles declared as supported for the release (e.g., if `stdio-http` is the supported profile, that is the acceptance criteria)
- Test harness MUST support all profiles (`http-http`, `stdio-http`, `stdio-stdio`) for troubleshooting and validating new combinations
- Same assertions MUST run for every profile — only the adapter changes
- Tool behavior MUST be correct regardless of how the call travels to the server
- Single-call tests verify tool contracts; hang-stress tests verify proxy state handling
- Tests MUST be deterministic: same input always produces same output

#### Test Infrastructure

- **Dual environment setup**: `anaconda-mcp-qa` (pytest runner) and server env (MCP server products)
- **Profile selection**: via `--mcp-profile` flag, not by editing packaged `mcp_compose.toml`
- **TOML generation**: deterministic from `tests/qa/shared/mcp_compose_profiles.py`
- **Fixture scopes**: module-scoped for `call_tool`, function-scoped for hang-stress (`call_no_hang_unified`)
- **Test marks**: `regression` (known bugs), `slow` (longer operations), `hang_stress` (proxy-state bugs)
- **Documentation**: architecture, configuration, test design, and reporting documented in `tests/qa/mcp_tools/_docs/`

**Rationale**: A bug can live in any hop — outer transport framing, mcp-compose proxy, upstream connection pooling, or tool implementation. Transport matrix testing isolates where a regression lives; consistent patterns enable reliable regression detection.

### IV. Observability & Error Handling

All services MUST implement structured logging and explicit error reporting.

- Use Python `logging` module with structured formatters
- Separate error handling for transport layer vs tool implementation
- All tool calls MUST return well-formed MCP responses (success or error)
- STDIO stderr MUST be captured for diagnostics; stdout reserved for JSON-RPC
- HTTP server logs MUST capture request/response cycles for debugging

**Rationale**: Multi-transport MCP servers require coordinated observability; silent failures in tool implementations are invisible to AI assistants and users.

## QA Testing Standards

### Test Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Unit | `tests/` | Core logic and utilities |
| Functional | `tests/` | Feature-level validation |
| Integration | `tests/` | Cross-component interaction |
| MCP Tools | `tests/qa/mcp_tools/` | Protocol-level tool validation across transports |

### MCP Tool Test Requirements

- **All profiles MUST pass**: `http-http`, `stdio-http`, `stdio-stdio`
- **Hang-stress tests** (`hang_stress` mark): 20 iterations with timeout guards to surface proxy-state bugs
- **Regression tests** (`regression` mark): guard known bugs, MUST pass before release
- **HTML reports**: generated to `tests/qa/mcp_tools/reports/report.html` with failure log extras

### Test Commands

- `make test` — Unit and functional tests
- `pytest tests/qa/mcp_tools -o addopts= --mcp-profile=<profile>` — MCP tool tests
- `--skip-hang-stress` or `MCP_QA_SKIP_HANG_STRESS=1` — Skip long-running hang tests for quick runs

## Code Quality

### Formatting & Linting

- **Pre-commit hooks**: `make pre-commit-install` to enable automatic checks
- **Ruff**: `make lint` to check, `make ruff-fix` to auto-fix
- **Type checking**: `make mypy` for strict type validation
- **Targeted changes only**: fix lint issues ONLY for code that was changed or added

### File Organization

- **Source**: `src/anaconda_mcp/` for main package code
- **Tests**: `tests/` for unit/functional, `tests/qa/` for QA-owned suites
- **Docs**: `docs/` for user-facing documentation
- **QA Docs**: `tests/qa/mcp_tools/_docs/` for test architecture and design

### Dependency Management

- Development dependencies in `environment-dev.yml` and `pyproject.toml[dev]`
- QA test runner env defined in `tests/qa/environment.yml`
- Server env requires explicit installation of `anaconda-mcp`, `environments-mcp`, `anaconda-connector-conda`

## Git & PR Workflow

### PR Separation

- **Codebase and QA tests are separate**: when codebase changes, QA tests (`tests/qa/`) are NOT touched in the same PR unless directly related
- **QA PRs are focused**: must be targeted, small, and single-purpose
- **No package changes without approval**: do NOT extend or change package versions/sets without explicit agreement

### Git Safety

- **Local commits only**: do NOT push to remote without explicit request
- **Preserve PR history**: do NOT amend, rebase, or alter PR history without explicit human request
- **No sensitive data**: NEVER commit or log secrets, credentials, tokens, or PII
- **No force push to main**: warn if requested, require explicit confirmation

### Commit Standards

- Pre-commit hooks MUST pass before commits
- Commit messages MUST be descriptive of the change
- Breaking changes MUST be documented in commit message

## Governance

This constitution supersedes all other development practices for Anaconda MCP.

### Amendment Process

1. Propose changes via pull request to `.specify/memory/constitution.md`
2. Changes MUST include rationale and impact assessment
3. Version bump follows semantic versioning:
   - **MAJOR**: Principle removal or incompatible redefinition
   - **MINOR**: New principle or material expansion
   - **PATCH**: Clarifications, wording, typo fixes
4. Dependent templates MUST be updated in the same PR

### Compliance

- All PRs MUST verify compliance with Core Principles
- Complexity beyond established patterns MUST be justified in PR description
- Use CLAUDE.md for runtime development guidance
- Constitution violations MUST be resolved before merge

**Version**: 1.0.0 | **Ratified**: 2026-05-14 | **Last Amended**: 2026-05-14

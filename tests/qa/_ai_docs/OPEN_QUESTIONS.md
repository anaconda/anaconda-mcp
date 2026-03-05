# Open Questions for Product Owner

## Purpose

Questions requiring product owner decision before finalizing test scope and priorities.

---

## Q1: Installation Source

**Question**: What version of MCP server should we test?

| Option | Description |
|--------|-------------|
| A | Latest from conda channels (released version) |
| B | Specific tag/version from codebase |
| C | Latest main branch (unreleased) |
| D | Multiple versions (regression across releases) |

**Current assumption**: Option A (conda channels, latest release)
---

## Q2: E2E Claude Desktop Platform

**Question**: Which platform for E2E Claude Desktop testing?

| Option | Platform |
|--------|----------|
| A | macOS only |

**Current assumption**: Option A (macOS only)

**Context**:
- Claude Desktop is available on macOS only
- No alternative platforms available for E2E Claude flows

**Note**: This is a constraint, not a choice. Included for documentation completeness.

---

## Q3: CLI/API/Config Platform Coverage

**Question**: Which platforms for CLI, API tools, and config testing?

| Option | Platforms |
|--------|-----------|
| A | macOS only |
| B | macOS + Windows (Win365) |
| C | macOS + Windows + Linux (CI runners) |

**Current assumption**: Option B (macOS + Windows)

**Context**:
- These tests don't require Claude Desktop
- Win365 available for Windows testing
- Linux available via GitHub runners

**Impact**: Cross-platform compatibility verification.

---

## Q4: Transport Mode Coverage

**Question**: Do we need to test both STDIO and HTTP transport modes?

| Option | Transport |
|--------|-----------|
| A | STDIO only (default) |
| B | STDIO + HTTP |

**Current assumption**: Option B (both transports)

**Context**:
- STDIO: Default, auto-spawns with Claude Desktop
- HTTP: Manual server start, useful for shared/Docker deployments

**Impact**: Each transport doubles E2E test execution time.

---

## Q5: Authentication & Related Features

**Question**: What authentication scope should we test?

| Option | Scope |
|--------|-------|
| A | Anonymous only (public channels, no telemetry) |
| B | Anonymous + Authenticated (basic) |
| C | Anonymous + Authenticated + Private channels + Telemetry verification |

**Current assumption**: Option B

**What each option covers**:

| Feature | Option A | Option B | Option C |
|---------|----------|----------|----------|
| Anonymous mode (public channels) | Yes | Yes | Yes |
| Authenticated mode (login flow) | No | Yes | Yes |
| Private/licensed channel access | No | No | Yes |
| Telemetry verification | No | Log check | Backend check |

**Context**:
- Anonymous: Works with public conda channels, no telemetry sent
- Authenticated: Enables telemetry, may enable private channels
- Private channels: Requires specific test packages + auth account
- Telemetry backend: Requires SnakeEyes access/coordination

**Dependencies**:
- Option B/C require valid Anaconda test account (QA team has them)
- Option C (private channels) requires identifying private-only test packages
- Option C (telemetry backend) requires coordination with backend team

---

## Q6: Python Version Coverage

**Question**: Which Python versions must be tested?

| Option | Versions |
|--------|----------|
| A | Single version (3.11) |
| B | Boundaries (3.10 + 3.13) |
| C | All supported (3.10, 3.11, 3.12, 3.13) |

**Current assumption**: Option B (boundaries: 3.10 + 3.13)

**Context**:
- Supported range: 3.10 - 3.13
- Boundary testing catches most compatibility issues

**Impact**: Test matrix size, CI runtime.

---

## Summary Table

| Question | Current Assumption | Needs Decision? |
|----------|-------------------|-----------------|
| Q1: Installation | Conda channels (latest) | Yes |
| Q2: E2E Platform | macOS only (constraint) | No |
| Q3: CLI/API/Config Platform | macOS + Windows | Yes |
| Q4: Transport | STDIO + HTTP | Yes |
| Q5: Auth & Related | Option B (Anonymous + Auth basic) | Yes |
| Q6: Python | Boundaries (3.10, 3.13) | Yes |

---

## Decision Log

| Date | Question | Decision | Rationale |
|------|----------|----------|-----------|
| ___ | Q1 | ___ | ___ |
| ___ | Q3 | ___ | ___ |
| ___ | Q4 | ___ | ___ |
| ___ | Q5 | ___ | ___ |
| ___ | Q6 | ___ | ___ |

---

## Next Steps

1. Review questions with product owner
2. Document decisions in Decision Log
3. Update TEST_MATRIX.md based on decisions
4. Adjust test documentation as needed

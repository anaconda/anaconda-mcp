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

## Constraints (FYI)

### Platform and Transport/Client Constraints
- **E2E testing**: macOS only (Claude Desktop and Cursor are available on macOS only)
    - Claude Desktop OR Cursor for STDIO transport
    - Cursor for HTTP transport [Claude Desktop does not support HTTP transport - KI-009](./KNOWN_ISSUES.md#ki-009-claude-desktop-does-not-support-http-transport)


---

## Q2: CLI/API/Config Platform Coverage

**Question**: Which platforms for CLI, API tools, and config testing?

| Option | Platforms |
|--------|-----------|
| A | macOS only |
| B | macOS + Windows (Win365) |
| C | macOS + Windows + Linux (CI runners) |

**Current assumption**: Option B (macOS + Windows)

**Context**:
- These tests don't require Claude Desktop or Cursor
- Win365 available for Windows testing
- Linux available via GitHub runners (to use this option, tests should be automated - technically possible, but we might have lack of time. What's priority for Linux?)

**Impact**: Cross-platform compatibility verification.

---

## Q3: Authentication & Related Features

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

## Q4: Python Version Coverage

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

---

## Q5: Additional MCP Client Coverage

**Question**: Should we test with other MCP clients beyond Claude Desktop and Cursor?

| Option | Clients |
|--------|---------|
| A | Claude Desktop + Cursor only (current) |
| B | + Claude Code |
| C | + VS Code |
| D | + Claude Code + VS Code |

**Current assumption**: Option A (Claude Desktop + Cursor only)

**Context**:
- Claude Code and VS Code may work via standard MCP protocol but have no dedicated integration code in anaconda-mcp
- Cursor is already required for HTTP transport validation (KI-009 constraint)
- Additional clients would increase test matrix size

**Impact**: Test matrix size, client-specific setup effort.

---

## Summary Table

| Question | Current Assumption | Needs Decision? |
|----------|-------------------|-----------------|
| Q1: Installation Source | Conda channels (latest) | Yes |
| Q2: CLI/API/Config Platform | macOS + Windows | Yes |
| Q3: Auth & Related | Option B (Anonymous + Auth basic) | Yes |
| Q4: Python Version | Boundaries (3.10, 3.13) | Yes |
| Q5: Additional MCP Clients | Claude Desktop + Cursor only | Yes |

---

## Decision Log

| Date | Question | Decision | Rationale |
|------|----------|----------|-----------|
| ___ | Q1 | ___ | ___ |
| ___ | Q2 | ___ | ___ |
| ___ | Q3 | ___ | ___ |
| ___ | Q4 | ___ | ___ |
| ___ | Q5 | ___ | ___ |

---

## Next Steps

1. Review questions with product owner
2. Document decisions in Decision Log
3. Update TEST_MATRIX.md based on decisions
4. Adjust test documentation as needed

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
**Answer**: We need to use specific versions for 
- anaconda-mcp=1.0.0.rc.1 
- environments-mcp-server=1.0.0.rc.1
- anaconda-connector — transitive dependency, version resolved by conda solver (record from `conda list` after install)
easiest way to have all specific versions (including python) is to use [Pinned RC Versions — Current Test Cycle](./QUICK_START.md#pinned-rc-versions--current-test-cycle)
---

## Constraints (FYI)

### Platform and Transport/Client Constraints
**E2E testing**: 
- macOS mostly (Claude Desktop and Cursor are available on macOS only)
    - Claude Desktop OR Cursor for STDIO transport
    - Cursor for HTTP transport [Claude Desktop does not support HTTP transport - KI-009](./KNOWN_ISSUES.md#ki-009-claude-desktop-does-not-support-http-transport)
- Windows as lower priority (likely we could have Claude Desktop here)    


---

## Q2: CLI/API/Config Platform Coverage

**Question**: Which platforms for CLI, API tools, and config testing?

| Option | Platforms |
|--------|-----------|
| A | macOS only |
| B | macOS + Windows (Win365) |
| C | macOS + Windows + Linux (CI runners) |

**Current assumption**: Option B (macOS + Windows)
**Answer**: Option B (macOS + Windows)

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
**Answer**: Option B

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
**Answer**: Option C (3.10, 3.11, 3.12, 3.13)

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
**Answer**: Option A (Claude Desktop + Cursor only)

**Context**:
- Claude Code and VS Code may work via standard MCP protocol but have no dedicated integration code in anaconda-mcp
- Cursor is already required for HTTP transport validation (KI-009 constraint)
- Additional clients would increase test matrix size

**Impact**: Test matrix size, client-specific setup effort.

---

## Summary Table

| Question | Decision | Needs Decision? |
|----------|----------|-----------------|
| Q1: Installation Source | anaconda-mcp=1.0.0.rc.1, environments-mcp-server=1.0.0.rc.1; anaconda-connector resolved as transitive dep | No |
| Q2: CLI/API/Config Platform | Option B — macOS + Windows | No |
| Q3: Auth & Related | Option B — Anonymous + Authenticated basic | No |
| Q4: Python Version | Option C — All supported: 3.10, 3.11, 3.12, 3.13 | No |
| Q5: Additional MCP Clients | Option A — Claude Desktop + Cursor only | No |

All decisions received. TEST_MATRIX.md updated accordingly.

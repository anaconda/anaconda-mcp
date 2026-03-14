# Test Design Overview

This document describes the test strategy for anaconda-mcp: what layers exist, why each is automated (or not), and how they work together to ensure quality across platforms and Python versions.

---

## Test Pyramid

```
                    ┌───────────────────┐
                    │    E2E Manual     │  ← Real MCP clients (Claude Code, Cursor)
                    │   (LLM-driven)    │     Non-deterministic, exploratory
                    └─────────┬─────────┘
                              │
              ┌───────────────┴───────────────┐
              │        API Tool Tests         │  ← MCP protocol level
              │   (HTTP & STDIO transports)   │     Deterministic, CI-automated
              └───────────────┬───────────────┘
                              │
      ┌───────────────────────┼───────────────────────┐
      │                       │                       │
┌─────┴─────┐          ┌──────┴──────┐         ┌──────┴──────┐
│ CLI Tests │          │Config Tests │         │ Unit Tests  │
│           │          │             │         │  (existing) │
└───────────┘          └─────────────┘         └─────────────┘
      ↑                       ↑                       ↑
  No server              No server              No server
  Fast, isolated         Fast, isolated         Fast, isolated
```

---

## Automation Priorities

| Priority | Layer | Why This Priority | Details |
|----------|-------|-------------------|---------|
| **P0** | API Tool Tests | Highest value — tests actual MCP tool behavior across transports and platforms; catches regressions in core functionality | [TESTS_API_TOOLS.md](./tests/automation/TESTS_API_TOOLS.md) |
| **P1** | CLI Tests | User-facing commands; platform-sensitive paths and shell behavior | [TESTS_CLI.md](./tests/automation/TESTS_CLI.md) |
| **P1** | Config Tests | Complex precedence rules; platform-specific defaults | [TESTS_CONFIG.md](./tests/automation/TESTS_CONFIG.md) |
| **—** | E2E Manual | Cannot automate — LLM non-determinism, client variability, auth flows | [tests/e2e/](./tests/e2e/) |

---

## Layer Summary

| Layer | Scope | Automated | Requires Server |
|-------|-------|-----------|-----------------|
| **Unit Tests** | Internal functions | Yes | No |
| **CLI Tests** | CLI commands, paths, exit codes | Yes | No |
| **Config Tests** | Env vars, TOML, precedence | Yes | No |
| **API Tool Tests** | MCP tools via JSON-RPC (HTTP/STDIO) | Yes | Yes |
| **E2E Manual** | Full user journeys with LLM | No | Yes |

---

## Why E2E Stays Manual

| Factor | Impact |
|--------|--------|
| **LLM non-determinism** | Same prompt → different tool calls; unstable assertions |
| **Client variability** | Claude Desktop, Cursor, Claude Code have different behaviors |
| **Auth flows** | Browser-based login requires human interaction |
| **Exploratory value** | Catches UX issues, confusing errors, edge cases |
| **Cost** | LLM API calls cost money; not scalable for CI |

Manual E2E focuses on: LLM interpretation, client UX, auth flows, new feature validation.

---

## How Automation Reduces Manual Testing

### Coverage Matrix

| Dimension | Values | Count |
|-----------|--------|-------|
| Tools | 6 | 6 |
| Transports | HTTP, STDIO | 2 |
| Platforms | Linux, macOS, Windows | 3 |
| Python versions | 3.10, 3.11, 3.12, 3.13 | 4 |

**Total**: 6 × 2 × 3 × 4 = **144 test points** (happy path only; error scenarios multiply this)

### What Each Layer Covers

| Category | Covered By | Manual? |
|----------|-----------|---------|
| Tool behavior (happy path, errors) | API Tool Tests | No |
| Transport behavior (HTTP, STDIO) | API Tool Tests | No |
| Hang/timeout regressions | API Tool Tests | No |
| Platform path handling | CLI + Config Tests | No |
| Python version compatibility | CI Matrix | No |
| LLM interpretation | E2E Manual | Yes |
| Client-specific UX | E2E Manual | Yes |
| Auth flows | E2E Manual | Yes |

**Result**: ~10 manual E2E flows vs 144+ automated test points

---

## CI Execution Model

**API Tool Tests** (require server):
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    transport: [http, stdio]
```

**CLI and Config Tests** (no server):
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
```

For API Tool tests, each matrix cell:
1. pytest fixture starts MCP server
2. Runs all tests against that server
3. pytest fixture tears down server (automatic cleanup)

No external scripts — fixture manages server lifecycle (platform-independent).

---

## Related Documents

| Document | Description |
|----------|-------------|
| [TESTS_API_TOOLS.md](./tests/automation/TESTS_API_TOOLS.md) | API tool test design (P0) |
| [TESTS_CLI.md](../tests/automation/TESTS_CLI.md) | CLI test design (P1) |
| [TESTS_CONFIG.md](../tests/automation/TESTS_CONFIG.md) | Config test design (P1) |
| [tests/e2e/](../tests/e2e/) | E2E manual test flows |
| [TEST_MATRIX.md](./TEST_MATRIX.md) | Platform/version coverage |
| [KNOWN_ISSUES.md](../_tracking/KNOWN_ISSUES.md) | Bug references for regressions |

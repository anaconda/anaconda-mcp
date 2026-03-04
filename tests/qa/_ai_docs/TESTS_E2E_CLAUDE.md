# E2E Flows - Claude Desktop (macOS Only)

## Overview

End-to-end flows requiring Claude Desktop interaction. Must run manually on macOS.

---

## Flow Summary

| Flow ID | Name | Priority |
|---------|------|----------|
| CORE-001 | Full Setup & Tools | P0 |
| CORE-002 | HTTP Transport | P0 |
| GUARD-001 | Guardrails | P0 |
| AUTH-002 | Anonymous Mode | P1 |
| REGRESS-001 | Known Issues | P0 |

---

## CORE-001: Full Setup & Tools

**Purpose**: End-to-end happy path covering installation, setup, and all 5 environment tools.

**Features Covered**:
- [x] Package Installation
- [x] Claude Desktop STDIO Setup
- [x] List Environments
- [x] Create Environment
- [x] Install Packages
- [x] Remove Packages
- [x] Delete Environment

**Preconditions**:
- [PRE] Python 3.10+ installed
- [PRE] Claude Desktop installed
- [PRE] No existing anaconda-mcp config

**Steps**:

```
Phase 1: Installation
```
1. Install package: `conda install anaconda-mcp -y`
2. Verify installation: `anaconda-mcp --help`
3. [EXPECTED] Help shows commands: serve, compose, discover, claude-desktop

```
Phase 2: Claude Desktop Setup
```
4. Get config path: `anaconda-mcp claude-desktop path`
5. [EXPECTED] Shows OS-specific path
6. Setup config: `anaconda-mcp claude-desktop setup-config`
7. [EXPECTED] Config created successfully
8. Restart Claude Desktop

```
Phase 3: Environment Tools
```
9. Ask Claude: "List my conda environments"
10. [EXPECTED] Claude uses `conda_list_environments`

11. Ask: "Create a new conda environment called e2e-test-env with Python 3.11"
12. [EXPECTED] Claude uses `conda_create_environment`

13. Ask: "Install numpy and requests in e2e-test-env"
14. [EXPECTED] Claude uses `conda_install_packages`

15. Ask: "Remove requests from e2e-test-env"
16. [EXPECTED] Claude uses `conda_remove_packages`

17. Ask: "Delete the e2e-test-env environment"
18. [EXPECTED] Claude uses `conda_delete_environment`

```
Phase 4: Verification
```
19. Ask: "List my conda environments"
20. [EXPECTED] e2e-test-env no longer appears

**Cleanup**: None needed

---

## CORE-002: HTTP Transport

**Purpose**: Test HTTP transport mode with Claude Desktop.

**Features Covered**:
- [x] Start Server (with port option)
- [x] HTTP Transport Setup
- [x] HTTP Transport Connection

**Steps**:

```
Phase 1: Server Start
```
1. Terminal 1: `anaconda-mcp serve --port 8888`
2. [EXPECTED] Server starts, logs "Listening on http://127.0.0.1:8888"

```
Phase 2: HTTP Setup
```
3. Terminal 2: `anaconda-mcp claude-desktop setup-config --transport streamable-http --port 8888`
4. [EXPECTED] Config shows URL: http://localhost:8888/mcp
5. Restart Claude Desktop

```
Phase 3: Verify Connection
```
6. Ask Claude: "List my conda environments"
7. [EXPECTED] Response received via HTTP transport

**Cleanup**: Restore STDIO config

---

## GUARD-001: Guardrails (Full Stack)

**Purpose**: Verify guardrail behaviors via Claude Desktop.

**Note**: Logic in environments-mcp-server, tested as full stack.

**Features Covered**:
- [x] Channel Ordering Respected
- [x] Hard Fail on Missing Package
- [x] Delete Confirmation Required

**Steps**:

```
Phase 1: Channel Ordering
```
1. Configure `.condarc` with channel order:
   ```yaml
   channels:
     - defaults
     - conda-forge
   ```
2. Create test env: `conda create -n guard-test python=3.11 -y`
3. Ask Claude: "Install a package in guard-test"
4. [EXPECTED] Package from first channel in `.condarc`

```
Phase 2: Hard Fail
```
5. Ask Claude: "Install nonexistent-package-xyz123 in guard-test"
6. [EXPECTED] Clear error, no pip fallback

```
Phase 3: Delete Confirmation
```
7. Ask Claude: "Delete guard-test environment"
8. [EXPECTED] Claude asks for confirmation
9. Confirm, verify deleted

**Cleanup**: Environment deleted in test

---

## AUTH-002: Anonymous Mode

**Purpose**: Test operation without authentication via Claude Desktop.

**Steps**:

1. Ensure logged out (clear tokens)
2. Setup config: `anaconda-mcp claude-desktop setup-config`
3. Restart Claude Desktop
4. Ask Claude: "List my conda environments"
5. [EXPECTED] Works with public channels
6. Ask Claude: "Create environment anon-test with Python 3.11"
7. [EXPECTED] Environment created

**Cleanup**: `conda remove -n anon-test --all -y`

---

## REGRESS-001: Known Issues

**Purpose**: Regression tests requiring Claude Desktop.

**Steps**:

```
Phase 1: Environment Name (KI-002)
```
1. Create env: `conda create -n regress-test python=3.11 -y`
2. Ask Claude: "List my conda environments"
3. [EXPECTED] Shows "regress-test" (not "base")

```
Phase 2: Install by Name (KI-003)
```
4. Ask Claude: "Install numpy in regress-test"
5. [EXPECTED] Found by name, installs successfully

```
Phase 3: Deletion Works (KI-001)
```
6. Ask Claude: "Delete regress-test environment"
7. Confirm deletion
8. Verify: `conda env list | grep regress-test` returns empty

**Cleanup**: Environment deleted in test

---

## Test Execution Order

### Every PR (macOS)
1. **REGRESS-001** - Verify known issues first
2. **CORE-001** - Full happy path
3. **GUARD-001** - Guardrails

### Release Testing
4. **CORE-002** - HTTP transport
5. **AUTH-002** - Anonymous mode

---

## Cleanup Script

```bash
#!/bin/bash
echo "Cleaning up test environments..."

conda remove -n e2e-test-env --all -y 2>/dev/null
conda remove -n guard-test --all -y 2>/dev/null
conda remove -n regress-test --all -y 2>/dev/null
conda remove -n anon-test --all -y 2>/dev/null

echo "Cleanup complete!"
```

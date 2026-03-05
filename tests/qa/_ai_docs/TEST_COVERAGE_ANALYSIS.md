# Test Coverage Analysis

## Overview

This document analyzes the **existing pytest unit/integration tests** in the codebase (`/tests/`).

For QA test flows (manual + CI automation), see:
- [TESTS_E2E.md](./TESTS_E2E.md) - E2E flows (macOS)
- [TESTS_CLI.md](./TESTS_CLI.md) - CLI flows (all platforms)
- [TESTS_CONFIG.md](./TESTS_CONFIG.md) - Config tests (all platforms)

---

## Test Types

| Type | Location | Purpose |
|------|----------|---------|
| **Unit/Integration** | `/tests/*.py` | Developer tests (pytest) |
| **QA E2E** | `TESTS_E2E.md` | Manual E2E (Claude Desktop or Cursor) |
| **QA CLI** | `TESTS_CLI.md` | CLI automation (CI) |
| **QA Config** | `TESTS_CONFIG.md` | Configuration testing (CI) |

---

## Existing Pytest Tests

**Location**: `/tests/`
**Framework**: pytest with pytest-asyncio
**Total Test Files**: 6
**Total Test Functions**: ~82

### Test Files

| File | Tests | Module Tested |
|------|-------|---------------|
| `test_auth.py` | 5 | auth.py |
| `test_claude_desktop.py` | 47 | claude_desktop.py |
| `test_serve_sigterm.py` | 14 | cli.py (serve) |
| `test_telemetry.py` | 2 | telemetry.py |
| `test_utils.py` | 8 | utils.py |
| `conftest.py` | - | Fixtures |

### Coverage by Module

| Source Module | LOC | Test File | Status |
|---------------|-----|-----------|--------|
| `auth.py` | 102 | test_auth.py | **Covered** |
| `claude_desktop.py` | 376 | test_claude_desktop.py | **Covered** |
| `cli.py` | 465 | test_serve_sigterm.py | **Partial** |
| `telemetry.py` | 79 | test_telemetry.py | **Covered** |
| `utils.py` | 50 | test_utils.py | **Covered** |
| `config.py` | 52 | - | **NOT COVERED** |
| `consts.py` | 41 | - | **NOT COVERED** |

**Coverage Estimate**: ~73% of source lines have unit tests

---

## What IS Tested (pytest)

### Authentication (test_auth.py)
- [x] Auth flow initialization
- [x] CLI serve triggers auth
- [x] Login timeout handling
- [x] Thread safety

### Claude Desktop (test_claude_desktop.py)
- [x] Config path detection (all OS)
- [x] Backup file creation
- [x] Config load/save
- [x] STDIO/HTTP config building
- [x] CLI commands

### CLI Serve (test_serve_sigterm.py)
- [x] SIGTERM handler
- [x] Graceful shutdown
- [x] Delay option
- [x] Config validation

### Telemetry (test_telemetry.py)
- [x] Metric sending
- [x] Missing auth token

### Utilities (test_utils.py)
- [x] Template replacement
- [x] Env var override
- [x] TOML preservation

---

## Gaps in Pytest Coverage

### High Priority

| Module | What's Missing |
|--------|----------------|
| `config.py` | Settings class, field validation, env parsing |
| `consts.py` | OS detection, enum values |

### Medium Priority

| Module | What's Missing |
|--------|----------------|
| `cli.py` | compose, discover commands |
| `__main__.py` | Module execution |

---

## Gap Coverage by QA Tests

Gaps in pytest coverage are addressed by QA test flows:

| Pytest Gap | Covered By QA |
|------------|---------------|
| compose command | CLI-001 |
| discover command | CLI-001 |
| Config env vars | TESTS_CONFIG (ENV-*) |
| OS path detection | TESTS_CONFIG (PATH-*) |
| Full E2E flow | TESTS_E2E |

---

## Test Execution

### Pytest (Developer Tests)
```bash
# All tests
make test

# With coverage
make test-coverage

# Specific file
pytest tests/test_auth.py -v

# Coverage report
pytest --cov=src/anaconda_mcp --cov-report=html tests/
```

### QA Tests (Manual + CI)
```bash
# CLI tests (can run in CI)
# See TESTS_CLI.md for full workflow

anaconda-mcp discover
anaconda-mcp compose
anaconda-mcp serve --port 8888 &
curl http://localhost:8888/mcp ...
```

---

## CI/CD Configuration

**Workflow**: `.github/workflows/test-claude-desktop.yml`

**Matrix**:
- OS: Ubuntu, macOS, Windows
- Python: 3.11

**Coverage**:
| Test Type | CI Automated |
|-----------|--------------|
| Pytest unit tests | Yes |
| QA CLI tests | Can be (see TESTS_CLI.md) |
| QA Config tests | Can be (see TESTS_CONFIG.md) |
| QA E2E Claude | No (manual, macOS only) |

---

## Recommendations

### For Developers
1. Add pytest tests for `config.py` (Settings validation)
2. Add pytest tests for `consts.py` (OS detection)
3. Add pytest tests for compose/discover commands

### For QA
1. Run TESTS_CLI.md flows in CI (all platforms)
2. Run TESTS_CONFIG.md flows in CI (all platforms)
3. Run TESTS_E2E.md manually on macOS before release

# Anaconda MCP - Test Coverage Analysis

## Current Test Structure

**Location**: `/tests/`
**Framework**: pytest with pytest-asyncio
**Total Test Files**: 6
**Total Test Functions**: ~82

## Test Files Overview

| File | Lines | Tests | Module Tested |
|------|-------|-------|---------------|
| `test_auth.py` | 138 | 5 | auth.py |
| `test_claude_desktop.py` | 584 | 47 | claude_desktop.py |
| `test_serve_sigterm.py` | 258 | 14 | cli.py (serve command) |
| `test_telemetry.py` | 41 | 2 | telemetry.py |
| `test_utils.py` | 159 | 8 | utils.py |
| `conftest.py` | 16 | - | Shared fixtures |

## Coverage by Source Module

| Source Module | LOC | Test Coverage | Status |
|---------------|-----|---------------|--------|
| `auth.py` | 102 | test_auth.py | **Covered** |
| `claude_desktop.py` | 376 | test_claude_desktop.py | **Covered** |
| `cli.py` | 465 | test_serve_sigterm.py, partial | **Partial** |
| `telemetry.py` | 79 | test_telemetry.py | **Covered** |
| `utils.py` | 50 | test_utils.py | **Covered** |
| `config.py` | 52 | - | **NOT COVERED** |
| `consts.py` | 41 | - | **NOT COVERED** |
| `__init__.py` | 5 | - | **NOT COVERED** |
| `__main__.py` | 6 | - | **NOT COVERED** |

**Coverage Estimate**: ~73% of source lines have associated tests

## What IS Tested

### Authentication (test_auth.py)
- [x] Auth flow initialization (single init guard)
- [x] CLI serve command starts auth flow
- [x] Login timeout handling
- [x] Login exception handling
- [x] Thread safety (10 concurrent calls)

### Claude Desktop (test_claude_desktop.py)
- [x] Config path detection (all OS)
- [x] Config directory retrieval
- [x] Backup file creation
- [x] Config load/save operations
- [x] STDIO transport config building
- [x] HTTP transport config building
- [x] Configure/remove/show operations
- [x] CLI commands (setup-config, remove-config, show, path)
- [x] OS-specific path tests

### CLI Serve Command (test_serve_sigterm.py)
- [x] SIGTERM handler registration
- [x] Graceful shutdown on SIGTERM
- [x] Exit code correctness
- [x] Delay option functionality
- [x] Config validation errors
- [x] Normal flow completion

### Telemetry (test_telemetry.py)
- [x] Metric sending success
- [x] Missing auth token handling

### Utilities (test_utils.py)
- [x] Template placeholder replacement
- [x] Environment variable override
- [x] sys.executable fallback
- [x] Non-existent config handling
- [x] Temp file creation
- [x] TOML structure preservation

## What is NOT Tested

### High Priority Gaps

#### config.py (52 lines) - Settings Class
```
NOT TESTED:
- Settings class instantiation
- Field validation (LOG_LEVEL, ENVIRONMENT)
- Environment variable parsing
- set_anaconda_domain() validator
- Domain auto-selection logic
```

#### consts.py (41 lines) - Enums
```
NOT TESTED:
- OSSystems.current() method
- Platform detection logic
- Enum value correctness
- Error handling for unknown OS
```

### Medium Priority Gaps

#### cli.py - Uncovered Commands
```
NOT TESTED:
- compose command
- discover command
- mcpb command (if exists)
- CLI group initialization
- Error handling for invalid configs
```

#### __main__.py (6 lines)
```
NOT TESTED:
- Module execution: python -m anaconda_mcp
```

#### __init__.py (5 lines)
```
NOT TESTED:
- Version retrieval
- Fallback version handling
```

## Test Types Distribution

| Type | Coverage | Notes |
|------|----------|-------|
| Unit Tests | ~70% | Config, utils, telemetry |
| Integration Tests | ~20% | CLI, auth flow |
| System Tests | ~10% | Signal handling, OS-specific |
| E2E Tests | 0% | **GAP - No full flow tests** |
| API Tests | 0% | **GAP - No MCP protocol tests** |

## CI/CD Test Configuration

**Workflow**: `.github/workflows/test-claude-desktop.yml`

**Matrix**:
- OS: Ubuntu, macOS, Windows
- Python: 3.11

**Jobs**:
1. Main test job - All platforms
2. Integration test job - Ubuntu only

## Recommended Test Additions

### Priority 1: Critical Gaps
1. **config.py tests** - Settings validation, env vars
2. **consts.py tests** - OS detection, enums
3. **MCP protocol tests** - Tool invocation, responses
4. **Guardrail tests** - See below

### Priority 2: E2E Coverage
1. Full Claude Desktop setup flow
2. Tool execution roundtrip
3. Error scenarios
4. Known issue regression tests (see [KNOWN_ISSUES.md](./KNOWN_ISSUES.md))

### Priority 3: Edge Cases
1. Large config files
2. Network timeouts
3. Concurrent access
4. Permission errors

## Guardrail Test Coverage (From Epic)

These are non-negotiable requirements that MUST have test coverage:

| Guardrail | Current Coverage | Priority |
|-----------|------------------|----------|
| All operations use conda, never pip | **NOT TESTED** | Critical |
| Respects .condarc channel ordering | **NOT TESTED** | Critical |
| Hard-fail if package not on channels | **NOT TESTED** | Critical |
| No .condarc modification without confirmation | **NOT TESTED** | Critical |
| Environment deletion requires confirmation | **NOT TESTED** | Critical |

### Recommended Guardrail Tests

```python
# test_guardrails.py (proposed)

def test_no_pip_fallback():
    """Verify pip is never used for package operations"""
    pass

def test_channel_ordering_respected():
    """Verify .condarc channel order is followed"""
    pass

def test_hard_fail_missing_package():
    """Verify failure when package not on configured channels"""
    pass

def test_condarc_modification_requires_confirmation():
    """Verify .condarc cannot be modified without confirmation"""
    pass

def test_environment_deletion_requires_confirmation():
    """Verify deletion prompts for confirmation"""
    pass
```

## Test Execution Commands

```bash
# All tests
make test

# With coverage
make test-coverage

# Specific file
pytest tests/test_auth.py -v

# Specific test
pytest tests/test_auth.py::test_auth_flow_should_be_initialized_only_once -v

# Functional tests only
make test-functional

# Integration tests only
make test-integration
```

## Coverage Reporting

```bash
# Generate coverage report
pytest --cov=src/anaconda_mcp --cov-report=html tests/

# View report
open htmlcov/index.html
```

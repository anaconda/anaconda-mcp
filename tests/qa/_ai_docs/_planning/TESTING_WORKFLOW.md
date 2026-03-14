# Testing Workflow

## Phase 0: Kickoff (One QA)

### Step 1: Resolve Open Questions
1. Review [OPEN_QUESTIONS.md](../_tracking/OPEN_QUESTIONS.md) with Product Owner
2. Document decisions in Decision Log section
3. Update [TEST_MATRIX.md](./TEST_MATRIX.md) based on decisions

### Step 2: Finalize Work Distribution
1. Distribute work among QA participants per updated TEST_MATRIX.md

## Phase 1: Preparation (Each QA Participant)

### Step 1: Environment Setup
1. Follow [QUICK_START.md](../tests/e2e/setup/QUICK_START.md) for your assigned configuration
2. Record your test configuration:
   - Python version
   - Transport mode (STDIO/HTTP)
   - Package versions (`conda list | grep -E "anaconda-mcp|environments-mcp"`)

### Step 2: Review Test Documentation
1. Read your assigned test files:
   - [tests/e2e/](../tests/e2e/) (E2E manual tests)
   - [TESTS_CLI.md](../tests/automation/TESTS_CLI.md)
   - [TESTS_CONFIG.md](../tests/automation/TESTS_CONFIG.md)
   - [TESTS_API_TOOLS.md](../tests/automation/TESTS_API_TOOLS.md)
2. Check [TEST_MATRIX.md](./TEST_MATRIX.md) for your specific assignments
3. Review [KNOWN_ISSUES.md](../_tracking/KNOWN_ISSUES.md) for expected behaviors
4. Ask questions if anything is unclear

### Step 3: Zephyr Setup
1. **Check existing test cases** - Do NOT duplicate
   - Search Zephyr for existing anaconda-mcp test cases
   - Only create new TCs if they don't exist
   - Use TC name format `[Anaconda MCP][TC ID] description` to avoid duplicates easily
2. **Create test cases** (if needed)
   - Use test IDs from documentation (CORE-001, CLI-001, etc.)
   - Include preconditions, steps, expected results (simplify work - actively use Description field)
   - Link TCs with release testing task
3. **Create test cycle**
   - Name format: `anaconda-mcp <version> - <platform> - <transport>`
   - Example: `anaconda-mcp 0.1.2 - macOS - STDIO`
   - Add metadata: Python version, transport, tester name

---

## Phase 2: Execution (Each Participant)

### Step 1: Execute Tests
1. Follow test steps from assigned test files
2. For each test case:
   - Mark status in Zephyr (Pass/Fail/Blocked)
   - Add execution notes if needed
   - Capture evidence for failures (screenshots, logs)

### Step 2: Bug Reporting
For any failures:
1. Check [KNOWN_ISSUES.md](../_tracking/KNOWN_ISSUES.md) - may be expected
2. Create bug ticket with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python, versions)
   - Logs/screenshots
3. **Link bug to QA release testing task**
4. Update Zephyr test case execution with bug link

### Step 3: Track Progress
1. Update test cycle status daily
2. Report blockers immediately
3. Document any deviations from test plan

---

## Test Cycle Naming Convention

Format: `anaconda-mcp <version> - <platform> - <transport> - <python>`

Examples:
- `anaconda-mcp 0.1.2 - macOS - STDIO - py3.10`
- `anaconda-mcp 0.1.2 - macOS - HTTP - py3.13`
- `anaconda-mcp 0.1.2 - Win365 - CLI/API - py3.13`

---

## Links

| Resource | Link |
|----------|------|
| Quick Start | [QUICK_START.md](../tests/e2e/setup/QUICK_START.md) |
| Test Matrix | [TEST_MATRIX.md](./TEST_MATRIX.md) |
| Open Questions | [OPEN_QUESTIONS.md](../_tracking/OPEN_QUESTIONS.md) |
| Known Issues | [KNOWN_ISSUES.md](../_tracking/KNOWN_ISSUES.md) |
| E2E Tests | [tests/e2e/](../tests/e2e/) |
| CLI Tests | [TESTS_CLI.md](../tests/automation/TESTS_CLI.md) |
| Config Tests | [TESTS_CONFIG.md](../tests/automation/TESTS_CONFIG.md) |
| API Tool Tests | [TESTS_API_TOOLS.md](../tests/automation/TESTS_API_TOOLS.md) |

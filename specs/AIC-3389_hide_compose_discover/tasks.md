# Tasks: Hide compose/discover commands from --help output

**Input**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md)
**Organization**: One P1 user story. `[x]` = already done and verified.

## Phase 1: Implementation (US1, P1) 🎯 MVP

**Goal**: `compose`/`discover` absent from `--help` on both entrypoints; still invokable.
**Independent Test**: the 6 commands in spec.md acceptance.

- [x] T001 [US1] Add `hidden=True` to the `compose` `@cli.command(...)` in `src/anaconda_mcp/cli.py` (L238)
- [x] T002 [US1] Add `hidden=True` to the `discover` `@cli.command(...)` in `src/anaconda_mcp/cli.py` (L276)
- [x] T003 [US1] Remove the unreachable `click_cli.main(["--help"])` fallback in `src/anaconda_mcp/app.py`

**Checkpoint**: legacy `anaconda-mcp --help` / bare clean; `anaconda mcp` unchanged (clean); commands still invokable — all verified on branch source.

## Phase 2: Regression Test

- [x] T010 [US1] Add a `CliRunner` test asserting `anaconda-mcp --help` Commands section excludes `compose`/`discover`, in `tests/test_cli_help.py`
- [x] T011 [US1] In the same test, assert `compose --help` / `discover --help` still exit 0 (remain invokable) in `tests/test_cli_help.py`

## Phase 3: Polish / Close-out

- [x] T020 Run full suite (`pytest`) — confirm no regressions → **348 passed, 3 skipped**
- [ ] T021 Commit `cli.py`, `app.py`, tests, and specs on the branch
- [ ] T022 Open PR; note in body that a conda package rebuild/republish is required to ship the fix to users

## Dependencies & Execution Order

- T001–T003 done. T010–T011 can be written now (no deps). T020 after T010–T011. T021 after T020. T022 after T021.

## Out of Scope

- `anaconda mcp` entrypoint (already clean since 1.1.0).
- Conda package rebuild/republish (separate release step; flagged in T022).
- Throwaway test envs (`mcp-103` / `mcp-110` / `mcp-test`) cleanup.

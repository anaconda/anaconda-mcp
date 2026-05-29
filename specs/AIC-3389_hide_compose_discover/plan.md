# Implementation Plan: Hide compose/discover commands from --help output

**Branch**: `AIC-3389_hide_compose_discover` | **Date**: 2026-05-29 | **Spec**: [spec.md](spec.md)
**Input**: [spec.md](spec.md) · [research.md](research.md)

## Summary

Hide the deprecated `compose`/`discover` commands from `--help` on the legacy `anaconda-mcp` Click entrypoint (they already lack `hidden=True`), and remove a now-unreachable help fallback in the `anaconda mcp` Typer wrapper. Commands stay invokable. Per research.md, only the legacy entrypoint still leaks on 1.1.x; `anaconda mcp` was fixed in 1.1.0.

## Technical Context

**Language/Version**: Python 3.11–3.13
**Primary Dependencies**: Click (legacy CLI), Typer + anaconda-cli-base (`anaconda mcp` plugin)
**Storage**: N/A
**Testing**: pytest (see `pytest.ini`, `tests/`)
**Project Type**: single (CLI library)
**Scale/Scope**: 2 source edits, 1 regression test

## Constitution Check

No `specs/constitution.md` in this repo — gate **N/A**. Change is a 2-line bug fix; no architectural decisions to gate.

## Project Structure

Files touched:

```text
src/anaconda_mcp/cli.py    # add hidden=True to compose (L238) and discover (L276)
src/anaconda_mcp/app.py    # remove unreachable click_cli.main(["--help"]) fallback
tests/                     # add regression test: legacy --help excludes compose/discover
```

No new modules, no data model, no API contracts.

## Approach

1. **`cli.py`** — add `hidden=True` to the `@cli.command(...)` decorators for `compose` and `discover`. Click renders `hidden=True` commands neither in `--help` nor the bare-group listing, while keeping them invokable (satisfies FR-001 + FR-002).
2. **`app.py`** — delete the `if ctx.invoked_subcommand is None: click_cli.main(["--help"], ...)` block. `no_args_is_help=True` already renders the clean Typer help on no-args (verified: exit 2, no compose/discover), so the fallback is dead code and its removal changes no behavior.
3. **Test** — add a pytest case invoking the legacy `--help` (and bare group) via Click's `CliRunner`, asserting `compose`/`discover` are absent from the command listing and that they remain invokable.

## Testing Strategy

- Unit/CLI: `CliRunner().invoke(cli, ["--help"])` → assert no `compose`/`discover` in the Commands section; `CliRunner().invoke(cli, ["compose", "--help"])` → exits cleanly (still registered).
- Manual (already verified across 1.0.3 / 1.1.0 / 1.1.1 + branch source): the 6 commands in spec.md acceptance.

## Out of Scope

- Rebuild/republish of the conda package (required for users to actually receive the fix — separate release step).
- The `anaconda mcp` entrypoint (already clean since 1.1.0; no change needed).

## Complexity Tracking

No violations. Minimal change, no new abstractions.

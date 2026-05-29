# Feature Specification: Hide compose/discover commands from --help output

**Feature Branch**: `AIC-3389_hide_compose_discover` · **Created**: 2026-05-29 · **Status**: Draft
**Input**: "AIC-3389 — compose/discover still appear in `--help` despite being hidden"

## User Story (P1)

A user runs `--help` to see what they can do. The deprecated `compose` and `discover` commands must not appear in either entrypoint (`anaconda mcp` and legacy `anaconda-mcp`), but must still run if called explicitly.

**Acceptance** — every command and its expected result:

Hidden from help (must show only `serve, clients, setup, remove, terms`):
- `anaconda mcp --help`
- `anaconda mcp` (no args, via `no_args_is_help`)
- `anaconda-mcp --help`
- `anaconda-mcp` (no args)

Still invokable (must execute):
- `anaconda-mcp compose`
- `anaconda-mcp discover`

## Requirements

- **FR-001**: Both entrypoints, in both `--help` and no-argument forms, MUST exclude `compose` and `discover` from the listed commands.
- **FR-002**: `compose` and `discover` MUST remain invokable on the legacy entrypoint when called explicitly.

## Success Criteria

- **SC-001**: All four — `anaconda mcp --help`, `anaconda mcp` (no args), `anaconda-mcp --help`, `anaconda-mcp` (no args) — show zero `compose`/`discover` entries.
- **SC-002**: `anaconda-mcp compose` / `discover` still run (exit behavior unchanged).

> Current status (see [research.md](research.md)): only the legacy `anaconda-mcp` entrypoint still leaks on 1.1.x; `anaconda mcp` was already fixed in 1.1.0.

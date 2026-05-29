# Specification Quality Checklist: Hide compose/discover commands from --help output

**Purpose**: Validate specification quality before proceeding to planning
**Created**: 2026-05-29
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] CHK001 No implementation details in FRs — command names (serve, compose, etc.) are the user-observable subject of this bug, not leaked implementation; no file paths or syntax in FRs
- [x] CHK002 Focused on user value and observable behaviors (help output contents)
- [x] CHK003 Readable by non-technical stakeholders
- [x] CHK004 All mandatory sections completed

## Requirement Completeness

- [x] CHK005 No [NEEDS CLARIFICATION] markers remain
- [x] CHK006 All FRs are testable and unambiguous
- [x] CHK007 All SCs are measurable (zero-occurrence grep checks)
- [x] CHK008 All acceptance scenarios defined
- [x] CHK009 Edge cases identified (direct invocation, no-subcommand)
- [x] CHK010 Scope clearly bounded (visibility only; commands remain invokable)
- [x] CHK011 Dependencies and assumptions identified

## Story Quality

- [x] CHK012 Each story has one user, one goal, one trigger
- [x] CHK013 No story has >3 scenarios with different trigger events
- [x] CHK014 Each story is independently testable

## Notes

- This checklist validates the SPEC, not the implementation.
- CHK001 caveat: command names appear in FRs because command *visibility* is the literal subject of the bug — they are domain terms here, not implementation leakage.

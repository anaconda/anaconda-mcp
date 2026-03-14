# REGRESS-001: Known Issues Regression

Regression tests for previously fixed bugs.

| Step | Action | Expected | RC1 | RC2 |
|------|--------|----------|:---:|:---:|
| Pre | [Logged Out + Public Channels](../../AUTH_SETUP.md#prerequisites-logged-out--public-channels-core-001a) | Clean auth state | + | + |
| Pre | Terminal: `conda create -n regress-test python=3.11 -y` | Test env created | + | + |
| 1 | "List my conda environments" | Shows "regress-test" (not "base") — KI-002 | + | + |
| 2 | "Install numpy in regress-test" | Found by name, installs — KI-003 | + | + |
| 3 | "Delete regress-test" | Actually deleted — KI-001 | + | + |
| 4 | Terminal: `conda env list \| grep regress-test` | Empty (env is gone) | + | + |
| Post | Terminal: `conda remove -n regress-test --all -y 2>/dev/null` | Cleanup (if test failed) | + | + |

## Release Notes

| Release | Additional Verification |
|---------|------------------------|
| RC1 | Step 2-3 may fail due to DESK-1342 (wrong prefix resolution) |
| RC2 | DESK-1342 fixed |

## Issues Covered

| Step | Issue | Description |
|------|-------|-------------|
| 1 | KI-002 | Environment misclassified as "base" |
| 2 | KI-003 | Environment operations fail by name (wrong prefix) |
| 3 | KI-001 | Environment not actually deleted |

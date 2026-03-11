# KI-016: `create_environment` Fails with Pydantic `frozen_instance` Error When `environment_root_path` Is Provided

**Component**: `environments-mcp-server`
**Affected version**: `1.0.0.rc.1`
**Jira**: [DESK-1384](https://anaconda.atlassian.net/browse/DESK-1384)
**Fixed in**: Fix applied locally in `environments-mcp` — not yet committed or released
**Bug introduced**: commit `b9184c8` ("feat: create environment with custom root", 2026-02-19) — this commit added `environment_root_path` support with the wrong implementation
**Severity**: High
**Platform**: Any OS (first observed on Windows; confirmed reproducible on macOS)
**Regression test**: `tests/qa/http_tools/test_create_environment_root_path.py`

---

## Summary

Calling `conda_create_environment` with `environment_root_path` raises a Pydantic `frozen_instance` `ValidationError`. The error surfaces as raw plain text in the MCP response instead of a structured tool result. The environment is not created and the LLM receives no actionable error message.

---

## Steps to Reproduce

1. Install `environments-mcp-server 1.0.0.rc.1`
2. Start the MCP server
3. Call `conda_create_environment` with `environment_root_path` set to any path:

```json
{
  "environment_name": "e2e-test",
  "packages": ["python=3.11"],
  "environment_root_path": "C:\\Users\\JuliaIliukhina\\miniconda3\\envs"
}
```

---

## Actual Result

The tool returns a raw Pydantic validation error as plain text instead of a structured tool result:

```
1 validation error for ContextConfig
root_path
  Instance is frozen [type=frozen_instance, input_value=WindowsPath('C:/Users/JuliaIliukhina/miniconda3/envs'), input_type=WindowsPath]
    For further information visit https://errors.pydantic.dev/2.12/v/frozen_instance
```

- The environment is **not created**
- The MCP response has `isError: false` but the content is a raw exception traceback, not JSON
- `_tool_result()` returns `{}` because the text does not start with `{`
- The LLM receives no actionable error and self-recovers by retrying with `environment_root_path` — hitting the same bug again

---

## Expected Result

The environment is created at the specified root path, **or** a meaningful conda-level error is returned if the path is invalid. No Pydantic validation error should surface to the caller.

---

## Root Cause

Two bugs on the same line in `create_environment.py`. The assignment is outside the `try/except` block — so the exception is unhandled and propagates to fastmcp:

```python
# Buggy — environments-mcp-server 1.0.0.rc.1
conda_config : ContextConfig = DEFAULT_CONFIG
if environment_root_path is not None:
    conda_config.root_path = Path(environment_root_path)   # ← BUG IS HERE
#              ^^^^^^^^^^ (1) wrong field name — correct field is `root_prefix`
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ (2) ContextConfig has
#              model_config = ConfigDict(frozen=True), so any direct attribute
#              assignment raises frozen_instance regardless of field name
```

```python
# Fix
conda_config = conda_config.merge(root_prefix=Path(environment_root_path))
```

The `else` branch immediately below already used the correct `merge()` pattern — the `if` branch was simply never updated to match.

---

## Why This Surfaced on Windows First

`environment_root_path` is an optional parameter. The LLM decides whether to include it:

- **macOS**: conda root is at a predictable system path (`/opt/miniconda3`). `get_distributions()` discovers it automatically, so the LLM omits `environment_root_path` and the buggy `if` branch is never reached.
- **Windows**: the conda root is at a per-user non-standard path (`C:\Users\...\miniconda3`). The LLM includes `environment_root_path` explicitly, triggering the bug.

The bug is **platform-independent**. Confirmed reproducible on macOS when `environment_root_path` is passed directly (via API test or LLM retry).

---

## Observed Call Sequence (from Claude Desktop logs, 2026-03-11)

```
conda_list_environments
  → KI-002 active: server env misclassified as "base"
  ↓
conda_create_environment(environment_name="e2e-test", packages=["python=3.11"])
  → get_distributions() returns wrong prefix (KI-003 cascade)
  → conda fails under wrong root
  → broad except swallows real error
  → "There was an error while creating the environment."
  ↓
LLM self-recovers: retries with environment_root_path="C:\...\miniconda3\envs"
  → get_conda_config() raises frozen_instance (KI-016) ← THIS IS WHAT USER SEES
```

KI-016 is therefore a secondary failure — triggered by the LLM's recovery attempt after a KI-002/KI-003 cascade causes the first `create_environment` call to fail silently.

---

## Evidence

**From Claude Desktop MCP log (2026-03-11, Windows)**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "conda_create_environment",
    "arguments": {
      "environment_name": "e2e-test",
      "packages": ["python=3.11"],
      "environment_root_path": "C:\\Users\\JuliaIliukhina\\miniconda3\\envs"
    }
  }
}
```

Response:
```
1 validation error for ContextConfig
root_path
  Instance is frozen [type=frozen_instance, input_value=WindowsPath('C:/Users/JuliaIliukhina/miniconda3/envs'), input_type=WindowsPath]
    For further information visit https://errors.pydantic.dev/2.12/v/frozen_instance
```

**From API regression test (macOS, `environments-mcp-server` installed from current `main`)**:
```
AssertionError: Pydantic frozen_instance validation error in response (KI-016 regression).
error_description=''
raw_content_texts=["1 validation error for ContextConfig\nroot_path\n  Instance is frozen
  [type=frozen_instance, input_value=PosixPath('/var/folders/.../nonexistent-conda-env-xyz123'),
  input_type=PosixPath]"]
```

---

## Fix

In `environments_mcp_server/tools/environments/create_environment.py`:

```python
# Before
if environment_root_path is not None:
    conda_config.root_path = Path(environment_root_path)

# After
if environment_root_path is not None:
    conda_config = conda_config.merge(root_prefix=Path(environment_root_path))
```

---

## Related

- **KI-002** / **KI-003**: root cause of the first silent `create_environment` failure that causes the LLM to retry with `environment_root_path`
- **KI-014**: same `get_conda_config()` area — missing `await` in `remove_environment.py`

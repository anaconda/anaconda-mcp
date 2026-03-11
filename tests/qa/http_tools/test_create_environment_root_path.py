"""
Regression tests: KI-016

Covers the defect in
environments_mcp_server/tools/environments/create_environment.py where
providing environment_root_path raised a Pydantic frozen_instance
ValidationError instead of a meaningful result.

Root cause (1.0.0.rc.1 and earlier):
    conda_config.root_path = Path(environment_root_path)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    (a) 'root_path' is not a field on ContextConfig — correct field is
        'root_prefix'.
    (b) ContextConfig uses model_config = ConfigDict(frozen=True), so any
        direct attribute assignment raises frozen_instance regardless of
        field name.

Fix (commit b9184c8, merged PR #36 / DESK-1329, 2026-03-09):
    conda_config = conda_config.merge(root_prefix=Path(environment_root_path))

The regression guard: call conda_create_environment with a non-null
environment_root_path and assert the response never contains a Pydantic
frozen_instance error.  The tool may return a conda-level error (e.g.
invalid path) — that is acceptable; what must NOT appear is the Pydantic
validation error text.

Platform note: reproducible on any OS.  First observed on Windows because
the LLM includes environment_root_path in the tool call when the conda envs
directory is at a non-standard per-user path (C:\\Users\\...\\miniconda3\\envs).
On macOS the LLM omits environment_root_path (conda root is auto-discovered),
so the buggy branch was never reached.

See tests/qa/_ai_docs/KNOWN_ISSUES.md (KI-016).
"""

from __future__ import annotations

import logging

import pytest

from common.constants.mcp_tools import CreateEnvironmentArgs, Tools
from common.constants.test_data import NONEXISTENT_ENV_PREFIX
from common.utils.mcp_client import _call_tool, _tool_result
from common.utils.response_validators import (
    _validate_is_error,
    _validate_no_pydantic_validation_error,
)

logger = logging.getLogger(__name__)

_ENV_NAME = "ki016-regression-test"


@pytest.mark.regression
class TestCreateEnvironmentWithRootPath:
    """
    Regression: conda_create_environment with environment_root_path must never
    return a Pydantic frozen_instance error.
    """

    def test_ki016_no_frozen_instance_error(self, session_id):
        """
        KI-016: providing environment_root_path must not raise a Pydantic
        frozen_instance ValidationError.

        Uses NONEXISTENT_ENV_PREFIX as the root path so conda fails fast
        with a directory/path error rather than actually creating an
        environment.  The assertion is only that the Pydantic error is absent
        — a conda-level error in error_description is acceptable and expected.

        Buggy behaviour  (1.0.0.rc.1): error_description contains
            "Instance is frozen [type=frozen_instance ...]"
        Fixed behaviour  (post b9184c8): error_description contains a
            conda error or the environment is created successfully.
        """
        logger.info(
            "KI-016: create_environment with environment_root_path='%s'",
            NONEXISTENT_ENV_PREFIX,
        )
        response = _call_tool(
            Tools.CONDA_CREATE_ENVIRONMENT,
            {
                CreateEnvironmentArgs.ENVIRONMENT_NAME: _ENV_NAME,
                CreateEnvironmentArgs.PACKAGES: ["python=3.11"],
                CreateEnvironmentArgs.ENVIRONMENT_ROOT_PATH: NONEXISTENT_ENV_PREFIX,
            },
            session_id,
        )
        result = _tool_result(response)
        _validate_no_pydantic_validation_error(
            result,
            response=response,
            context=f"environment_root_path={NONEXISTENT_ENV_PREFIX!r}",
        )
        logger.info("KI-016: no frozen_instance error — result: %s", result)

    def test_ki016_response_is_parseable_with_root_path(self, session_id):
        """
        KI-016 (companion): with environment_root_path provided, the tool must
        return a parseable JSON tool result — not a raw Pydantic traceback and
        not an empty response.

        On the buggy version (1.0.0.rc.1), the frozen_instance error was raised
        BEFORE the try/except block in create_environment.py, so fastmcp received
        an unhandled exception and returned a JSON-RPC error body instead of a
        tool result.  _tool_result() returns {} for JSON-RPC errors.

        On the fixed version the tool either succeeds (conda creates the path) or
        returns a structured is_error=true result.  Either way the response must
        be parseable (result != {}) and must not contain a Pydantic error.

        Note: we cannot assert is_error=true here — with the fix in place conda
        is free to succeed by creating the directory at NONEXISTENT_ENV_PREFIX.
        The regression guard is: (a) no frozen_instance, (b) parseable response.
        """
        logger.info(
            "KI-016: create_environment with environment_root_path='%s'",
            NONEXISTENT_ENV_PREFIX,
        )
        response = _call_tool(
            Tools.CONDA_CREATE_ENVIRONMENT,
            {
                CreateEnvironmentArgs.ENVIRONMENT_NAME: _ENV_NAME,
                CreateEnvironmentArgs.PACKAGES: ["python=3.11"],
                CreateEnvironmentArgs.ENVIRONMENT_ROOT_PATH: NONEXISTENT_ENV_PREFIX,
            },
            session_id,
        )
        result = _tool_result(response)
        logger.info("KI-016: raw result=%s", result)

        _validate_no_pydantic_validation_error(
            result,
            response=response,
            context=f"environment_root_path={NONEXISTENT_ENV_PREFIX!r}",
        )
        assert result != {}, (
            "KI-016 regression: _tool_result() returned {} — server returned a "
            "JSON-RPC error body instead of a tool result. On the buggy version "
            "this happens because the frozen_instance Pydantic error is unhandled "
            "and propagates past fastmcp's tool dispatcher. "
            f"Raw MCP response: {response!r}"
        )

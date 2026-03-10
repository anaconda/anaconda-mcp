"""
Regression tests: GUARD-ENV-OPS-API (KI-002, KI-003)

KI-002 — list_environments reports wrong name
    conda_list_environments() returns name="base" for an environment whose
    actual name differs (e.g. anaconda-mcp-rc-py313 shown as "base").

KI-003 — remove_environment by name resolves wrong prefix
    conda_remove_environment(environment_name="<name>") builds an incorrect
    prefix (resolves under the misclassified "base" env) and returns
    "Conda environment not found", even though the environment exists.
    Workaround: call with prefix instead of name.

See tests/qa/_ai_docs/KNOWN_ISSUES.md (KI-002, KI-003) and README.md for setup.
"""

from __future__ import annotations

import logging
import subprocess

import pytest

from common.constants.mcp_tools import RemoveEnvironmentArgs, ToolResultFields, Tools
from common.constants.test_data import REMOVABLE_ENV_NAME
from common.utils.conda_utils import _conda_env_prefix
from common.utils.mcp_client import _call_tool, _tool_result

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def removable_env():
    """
    Create a dedicated conda environment for the KI-003 removal test.

    Module-scoped so the env is created once. The test itself removes it via
    MCP; teardown cleans up with the conda CLI in case the MCP call fails.
    """
    import time as _time
    t0 = _time.monotonic()
    logger.info("[FIXTURE] removable_env: creating conda env '%s'...", REMOVABLE_ENV_NAME)
    result = subprocess.run(
        ["conda", "create", "-n", REMOVABLE_ENV_NAME, "python=3.11", "-y"],
        check=True,
        capture_output=True,
        text=True,
    )
    logger.info(
        "[FIXTURE] removable_env: conda create completed in %.1fs",
        _time.monotonic() - t0,
    )
    logger.debug("[FIXTURE] conda create stdout: %s", result.stdout[-500:] if result.stdout else "")
    prefix = _conda_env_prefix(REMOVABLE_ENV_NAME)
    logger.info("[FIXTURE] removable_env: name=%r prefix=%r", REMOVABLE_ENV_NAME, prefix)
    yield {"name": REMOVABLE_ENV_NAME, "prefix": prefix}
    logger.info("[FIXTURE] removable_env: teardown — removing env '%s'", REMOVABLE_ENV_NAME)
    subprocess.run(
        ["conda", "remove", "-n", REMOVABLE_ENV_NAME, "--all", "-y"],
        check=False,  # env may already be gone if MCP removal succeeded
    )
    logger.info("[FIXTURE] removable_env: teardown complete")


@pytest.mark.regression
class TestEnvironmentNameResolution:
    """
    Regression: environment listing and removal must use correct names and
    prefixes — not misclassify environments or resolve wrong paths.
    """

    def test_ki002_list_environments_reports_correct_name(self, conda_env, session_id):
        """
        KI-002: conda_list_environments must return the correct name for each
        environment — not "base" for a non-base environment.

        Observed: the tool returns name="base" for anaconda-mcp-rc-py313
        (path=/opt/miniconda3/envs/anaconda-mcp-rc-py313). The bug affects
        any environment whose conda context resolves incorrectly.

        This test creates a known environment (conda_env fixture →
        guard-api-test), calls conda_list_environments, finds the entry by
        prefix, and asserts the reported name matches the actual env name.
        """
        import time as _time
        t0 = _time.monotonic()
        logger.info(
            "[KI-002] START: listing environments, expecting name=%r at prefix %r session_id=%s",
            conda_env["name"],
            conda_env["prefix"],
            session_id[:8] + "..." if session_id else None,
        )
        logger.info("[KI-002] t=%.2fs: calling _call_tool...", _time.monotonic() - t0)
        response = _call_tool(Tools.CONDA_LIST_ENVIRONMENTS, {}, session_id)
        logger.info("[KI-002] t=%.2fs: _call_tool returned", _time.monotonic() - t0)
        result = _tool_result(response)

        assert not result.get(ToolResultFields.IS_ERROR), (
            f"conda_list_environments returned an error: "
            f"{result.get(ToolResultFields.ERROR_DESCRIPTION)!r}"
        )

        environments = result.get("tool_result", {}).get("environments", [])
        match = next(
            (e for e in environments if e.get("path") == conda_env["prefix"]),
            None,
        )

        assert match is not None, (
            f"Environment at prefix {conda_env['prefix']!r} not found in list. "
            f"Returned environments: {environments}"
        )
        assert match.get("name") == conda_env["name"], (
            f"KI-002: environment at {conda_env['prefix']!r} reported "
            f"name={match.get('name')!r}, expected {conda_env['name']!r}. "
            "The environment is misclassified."
        )

    def test_ki003_remove_environment_by_name(self, removable_env, session_id):
        """
        KI-003: conda_remove_environment(environment_name=<name>) must find
        and remove an existing environment — not fail with 'environment not
        found' due to wrong prefix resolution.

        Observed: the tool constructs the prefix as
        <misclassified-base>/envs/<name> instead of the real prefix, so
        EnvironmentLocationNotFound is raised even though the env exists.
        The environment can only be removed by passing prefix directly.
        """
        import time as _time
        t0 = _time.monotonic()
        logger.info(
            "[KI-003] START: removing env %r by name (prefix: %r) session_id=%s",
            removable_env["name"],
            removable_env["prefix"],
            session_id[:8] + "..." if session_id else None,
        )
        logger.info("[KI-003] t=%.2fs: calling _call_tool...", _time.monotonic() - t0)
        response = _call_tool(
            Tools.CONDA_REMOVE_ENVIRONMENT,
            {RemoveEnvironmentArgs.ENVIRONMENT_NAME: removable_env["name"]},
            session_id,
        )
        logger.info(
            "[KI-003] t=%.2fs: _call_tool returned, parsing result...",
            _time.monotonic() - t0,
        )
        result = _tool_result(response)
        logger.info(
            "[KI-003] t=%.2fs: DONE is_error=%s result=%s",
            _time.monotonic() - t0,
            result.get(ToolResultFields.IS_ERROR),
            result,
        )

        assert not result.get(ToolResultFields.IS_ERROR), (
            f"KI-003: conda_remove_environment by name {removable_env['name']!r} failed. "
            f"Wrong prefix was resolved. "
            f"error_description: {result.get(ToolResultFields.ERROR_DESCRIPTION)!r}"
        )

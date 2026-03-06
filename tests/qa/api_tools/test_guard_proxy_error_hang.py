"""
Regression tests: KI-011 — client hang after MCP tool error (HTTP transport)

Background:
  A hang was observed on 2026-03-05 where a Cursor chat session stopped
  responding after a tool call returned an error.  The session showed
  "Generating…" indefinitely.  Claude Desktop did not hang under the same
  conditions.

  Log analysis revealed the backend session lifecycle to environments_mcp_server
  (port 4041) was truncated:
    Normal flow:   POST(init) → GET(SSE) → POST(202) → POST(tool) → POST(?) → DELETE
    Hanging flow:  POST(init) → POST(202) → GET(SSE) → POST(tool)  [stops here]
  The 5th POST and DELETE to port 4041 were never sent.  The tool result was
  never forwarded to Cursor.

Root cause — two competing hypotheses (see KI-011-HTTP-PROXY-HANG.md):
  H1 (server-side): mcp-compose proxy has a race condition or async exception
     that silently drops the result when forwarding an error response.  The
     GET/POST ordering difference in the logs and the "200 OK vs 202 Accepted"
     difference for the callTool POST are consistent with this.
  H2 (client-side): mcp-compose correctly forwards the result but Cursor's
     TypeScript MCP HTTP client fails to process certain response shapes.
     Multiple independent MCP server developers have reported the same
     pattern (Cursor hangs, httpx does not).

  Each test runs WARM_ITERATIONS (20) iterations to reproduce the accumulated
  session state that triggered the production hang (~47 min, many prior calls).
  HANG-003 additionally runs WARM_ITERATIONS healthy calls as a pre-warm phase
  before triggering any errors, which most closely models the production scenario.

What these tests assert:
  HANG-001  conda_remove_environment error response arrives within TOOL_TIMEOUT
            on every one of WARM_ITERATIONS repeated calls.
  HANG-002  conda_install_packages error response arrives within TOOL_TIMEOUT
            on every one of WARM_ITERATIONS repeated calls (different code path).
  HANG-003  After WARM_ITERATIONS warm-up calls and WARM_ITERATIONS error+health
            cycles, the session remains functional throughout — no one-time or
            accumulating session corruption.

How the timeout catches the regression:
  _call_tool uses httpx.Timeout(read=TOOL_TIMEOUT).  A hang raises
  httpx.ReadTimeout, which each test catches and converts to pytest.fail()
  with a KI-011 reference.  The @pytest.mark.timeout marker is a second
  safety net at the pytest-runner level.

HTTP-transport-only scope:
  These tests talk directly to mcp-compose via httpx and bypass the Cursor
  client entirely.  If H2 (Cursor client bug) is the actual cause, these
  tests will always pass even when Cursor still hangs — because httpx
  correctly processes responses that Cursor's client does not.

  There is no way for this suite to exercise the STDIO transport path.
  STDIO requires a subprocess pipe (Claude Desktop communicates over
  stdin/stdout), which cannot be driven by httpx.

See tests/qa/_ai_docs/KI-011-HTTP-PROXY-HANG.md for the full investigation,
diagrams, and decision tree.
"""

from __future__ import annotations

import logging
import time

import httpx
import pytest

from common.constants.config import BASE_URL, TOOL_TIMEOUT
from common.constants.mcp_tools import (
    InstallPackagesArgs,
    RemoveEnvironmentArgs,
    ToolResultFields,
    Tools,
)
from common.constants.test_data import NONEXISTENT_ENV_PREFIX, NONEXISTENT_PKG
from common.utils.mcp_client import _call_tool, _tool_result

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.http_transport


@pytest.fixture
def session_id(mcp_server) -> str | None:
    """
    Function-scoped MCP session — overrides the module-scoped fixture from
    conftest.py for all tests in this file.

    Each HANG test must start with a clean session to prevent cascading
    failures: HANG-002 deliberately triggers a proxy hang that permanently
    corrupts the mcp-compose session state.  With a module-scoped session,
    HANG-003 would inherit that corrupted state and fail at warm-up before
    it ever triggers an error — masking whether HANG-003 found an independent
    regression or merely inherited HANG-002's damage.

    Making the fixture function-scoped ensures HANG-001, HANG-002, and
    HANG-003 each open a fresh session, so every test result is independent.
    """
    response = httpx.post(
        BASE_URL,
        json={
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "api-tools-hang-test", "version": "1.0"},
            },
        },
        headers={"Accept": "application/json, text/event-stream"},
        timeout=10,
    )
    sid = response.headers.get("mcp-session-id")
    headers = {"Accept": "application/json, text/event-stream"}
    if sid:
        headers["Mcp-Session-Id"] = sid
    try:
        httpx.post(
            BASE_URL,
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            headers=headers,
            timeout=5,
        )
    except Exception:
        pass
    logger.info("fresh session_id=%s", sid)
    return sid


# Number of iterations for each test loop.
#
# The production hang occurred after ~47 minutes of accumulated session state
# (many prior tool calls, repeated get_conda() re-initializations).  Running
# error-triggering calls and warm-up calls in a loop exercises that accumulated
# state within a single test session.
#
# 20 iterations is a pragmatic balance:
#   - Normal execution: ~20 × 2 s ≈ 40 s per test (fast error responses)
#   - If the race condition fires: the iteration that hangs raises ReadTimeout
#     after TOOL_TIMEOUT seconds and immediately fails the test
#   - pytest.mark.timeout is set to TOOL_TIMEOUT × WARM_ITERATIONS as a
#     safety net in case httpx itself is bypassed
WARM_ITERATIONS = 20

_HANG_FAIL_MSG = (
    "mcp-compose proxy did not forward the error response from "
    "environments_mcp_server within {timeout}s (iteration {iteration}/{total}). "
    "The backend HTTP session to port 4041 was likely abandoned "
    "(missing 5th POST + DELETE). Matches the KI-011 hang pattern. "
    "Observed on 2026-03-05 with Streamable HTTP transport, Python 3.13."
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.slow
class TestProxyErrorHangHttp:
    """
    Regression: mcp-compose proxy must forward error responses from
    environments_mcp_server to the HTTP client within TOOL_TIMEOUT — not
    abandon the backend session and leave the upstream connection hanging.
    """

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS)
    def test_hang_001_remove_nonexistent_env_does_not_hang(self, session_id):
        """
        HANG-001: conda_remove_environment for a non-existent prefix must
        return an isError=true response within TOOL_TIMEOUT seconds on every
        iteration across WARM_ITERATIONS repeated calls.

        Uses an absolute path that cannot be a real conda env prefix
        (NONEXISTENT_ENV_PREFIX) to guarantee an immediate error from
        environments_mcp_server without creating any real environment.

        The loop warms up get_conda() re-initialization state (re-initialized
        on every tool call in environments_mcp_server) to reproduce the
        accumulated-state condition that triggered the production hang after
        ~47 minutes.  If the race condition fires on any iteration, httpx
        raises ReadTimeout and the test fails with the iteration number.

        Reproduced: 2026-03-05, macOS, Streamable HTTP, Python 3.13, Cursor.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-001 [%d/%d] remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            t0 = time.monotonic()
            try:
                response = _call_tool(
                    Tools.CONDA_REMOVE_ENVIRONMENT,
                    {RemoveEnvironmentArgs.PREFIX: NONEXISTENT_ENV_PREFIX},
                    session_id,
                )
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-001: conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )

            result = _tool_result(response)
            logger.info(
                "HANG-001 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, time.monotonic() - t0,
                result.get(ToolResultFields.IS_ERROR),
            )
            assert result.get(ToolResultFields.IS_ERROR) is True, (
                f"HANG-001 iteration {i}/{WARM_ITERATIONS}: expected is_error=true "
                f"for non-existent prefix '{NONEXISTENT_ENV_PREFIX}', got: {result}"
            )

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS)
    def test_hang_002_install_into_nonexistent_env_does_not_hang(self, session_id):
        """
        HANG-002: conda_install_packages targeting a non-existent prefix must
        return an isError=true response within TOOL_TIMEOUT seconds on every
        iteration across WARM_ITERATIONS repeated calls.

        Exercises a different code path in environments_mcp_server from
        HANG-001, which may produce a different error shape; confirms the
        proxy handles all error paths from install_packages without hanging
        under accumulated session state.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-002 [%d/%d] install_packages prefix=%s pkg=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX, NONEXISTENT_PKG,
            )
            t0 = time.monotonic()
            try:
                response = _call_tool(
                    Tools.CONDA_INSTALL_PACKAGES,
                    {
                        InstallPackagesArgs.PREFIX: NONEXISTENT_ENV_PREFIX,
                        InstallPackagesArgs.PACKAGES: [NONEXISTENT_PKG],
                    },
                    session_id,
                )
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-002: conda_install_packages hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )

            result = _tool_result(response)
            logger.info(
                "HANG-002 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, time.monotonic() - t0,
                result.get(ToolResultFields.IS_ERROR),
            )
            assert result.get(ToolResultFields.IS_ERROR) is True, (
                f"HANG-002 iteration {i}/{WARM_ITERATIONS}: expected is_error=true "
                f"for non-existent prefix '{NONEXISTENT_ENV_PREFIX}', got: {result}"
            )

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS * 3)
    def test_hang_003_session_survives_error_response(self, session_id):
        """
        HANG-003: the mcp-compose server must remain functional after
        forwarding an error response — subsequent tool calls on the same
        session must also complete within TOOL_TIMEOUT.

        Sequence:
          Phase 1 — warm-up: WARM_ITERATIONS successful conda_list_environments
            calls to accumulate session state before the first error.  This
            simulates a real chat session that has been active for some time
            before encountering an error — the condition closest to the
            production hang (~47 minutes, many prior tool calls).
          Phase 2 — looped error+health: WARM_ITERATIONS iterations of:
            (a) trigger an error (remove_environment on non-existent prefix)
            (b) immediately call a healthy tool (conda_list_environments)

        Two failure modes this test can catch:

        1. Warm-up hangs on iteration 1 (KI-011 server-level corruption):
           The mcp-compose process is already corrupted before this test ran.
           Most likely HANG-002 fired in the same pytest run and left a stuck
           internal SSE connection to port 4041.  The corruption is in
           mcp-compose's internal HTTP connection pool — it is process-wide,
           NOT session-scoped.  Even new sessions on a fresh mcp-compose
           Mcp-Session-Id cannot bypass the stuck pool connection.
           Resolution: restart the MCP server.

        2. Warm-up passes, health step hangs in Phase 2:
           The proxy corrupts its connection state specifically when forwarding
           an error, causing subsequent calls on the same session to hang.
           This would distinguish a one-time error-forwarding bug from the
           broader connection-pool corruption observed in failure mode 1.

        For HANG-003 to test mode 2 independently, it must run against a
        freshly started server (no prior HANG-002 failure in the same run):
          python -m pytest tests/qa/api_tools/test_guard_proxy_error_hang.py \
              -k test_hang_003 -v

        The @pytest.mark.timeout uses WARM_ITERATIONS * 3 because three
        round-trips are made per iteration (1 warm-up + 1 error + 1 healthy).
        """
        # Phase 1: warm up the session with WARM_ITERATIONS healthy calls
        logger.info(
            "HANG-003 warm-up: %d × conda_list_environments to accumulate session state",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info("HANG-003 warm-up [%d/%d] list_environments", i, WARM_ITERATIONS)
            t0 = time.monotonic()
            try:
                _call_tool(Tools.CONDA_LIST_ENVIRONMENTS, {}, session_id)
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-003 warm-up iteration {i}/{WARM_ITERATIONS}: "
                    f"conda_list_environments hung on a healthy call. "
                    f"This is KI-011 server-level corruption: mcp-compose's internal "
                    f"HTTP connection pool to port 4041 is permanently stuck. "
                    f"If HANG-002 also failed in this run, this is a cascade — the "
                    f"same abandoned SSE connection is blocking all new forwarded calls. "
                    f"A server restart is required to recover. "
                    f"To test HANG-003 independently, run it against a fresh server."
                )
            logger.info(
                "HANG-003 warm-up [%d/%d] done in %.2fs",
                i, WARM_ITERATIONS, time.monotonic() - t0,
            )

        # Phase 2: WARM_ITERATIONS × (error trigger → session health check)
        logger.info(
            "HANG-003: warm-up done — starting %d × error+health iterations",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "HANG-003 [%d/%d] error step: remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            t0 = time.monotonic()
            try:
                _call_tool(
                    Tools.CONDA_REMOVE_ENVIRONMENT,
                    {RemoveEnvironmentArgs.PREFIX: NONEXISTENT_ENV_PREFIX},
                    session_id,
                )
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-003 iteration {i}/{WARM_ITERATIONS} (error step): "
                    f"conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )
            logger.info(
                "HANG-003 [%d/%d] error step done in %.2fs",
                i, WARM_ITERATIONS, time.monotonic() - t0,
            )

            logger.info("HANG-003 [%d/%d] health step: list_environments", i, WARM_ITERATIONS)
            t0 = time.monotonic()
            try:
                response = _call_tool(Tools.CONDA_LIST_ENVIRONMENTS, {}, session_id)
            except httpx.ReadTimeout:
                pytest.fail(
                    f"HANG-003 iteration {i}/{WARM_ITERATIONS} (health step): "
                    f"session hung after an error response. "
                    "mcp-compose proxy corrupted the HTTP session state while "
                    "handling the error from environments_mcp_server. "
                    "All subsequent calls on this session will also hang until "
                    "the MCP server is restarted. Matches KI-011."
                )

            result = _tool_result(response)
            logger.info(
                "HANG-003 [%d/%d] health step done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, time.monotonic() - t0,
                result.get(ToolResultFields.IS_ERROR),
            )
            assert not result.get(ToolResultFields.IS_ERROR), (
                f"HANG-003 iteration {i}/{WARM_ITERATIONS}: "
                f"conda_list_environments returned an error after the session "
                f"survived the previous error: {result}"
            )

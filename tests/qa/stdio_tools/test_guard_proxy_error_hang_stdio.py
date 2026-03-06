"""
Regression tests: KI-011 — client hang after MCP tool error (STDIO transport)

Background:
  The HTTP-transport tests (test_guard_proxy_error_hang.py) confirm that
  mcp-compose hangs under Streamable HTTP when a tool returns an error.
  These tests exercise the identical flows over STDIO transport (the mode
  used by Claude Desktop) to determine whether the hang is gated on the
  upstream transport or lives in mcp-compose's internal proxy logic.

Transport architecture under test:
  Test process  --stdin/stdout pipe-->  mcp-compose (STDIO mode)
                                              |
                                        Streamable HTTP (port 4042)
                                              |
                                    environments_mcp_server

  Note: mcp-compose's INTERNAL connection to environments_mcp_server is still
  Streamable HTTP in STDIO mode — the same internal path as the HTTP tests.
  Only the UPSTREAM transport (client → mcp-compose) differs.

Test result (2026-03-06):
  The hang reproduces over STDIO at iteration 16/20 (vs iteration 4/20 for
  HTTP).  The race condition lives in mcp-compose's internal Streamable HTTP
  pool to port 4042, not in the upstream transport handler.

What these tests assert:
  STDIO-HANG-001  conda_remove_environment error response arrives within
                  TOOL_TIMEOUT on every one of WARM_ITERATIONS repeated calls.
                  Mirrors HTTP HANG-001.

  STDIO-HANG-002  conda_install_packages error response arrives within
                  TOOL_TIMEOUT on every one of WARM_ITERATIONS repeated calls.
                  Mirrors HTTP HANG-002.

  STDIO-HANG-003  After WARM_ITERATIONS warm-up calls and WARM_ITERATIONS
                  error+health cycles, the server remains functional throughout.
                  Mirrors HTTP HANG-003.

STDIO session isolation:
  STDIO has no session-ID concept — the entire pipe is one session tied to
  the subprocess lifetime.  To isolate tests (so HANG-001/002 corruption does
  not cascade into HANG-003), stdio_server is function-scoped: each test gets
  a fresh mcp-compose process.  This mirrors the function-scoped session_id
  fixture used by the HTTP tests.

STDIO JSON-RPC framing:
  MCP STDIO uses newline-delimited JSON.  Each request is a single-line JSON
  object written to stdin; each response is a single-line JSON object read from
  stdout.  stderr receives mcp-compose log output and is not part of the
  protocol.

No external HTTP dependencies:
  These tests use only stdlib (subprocess, threading, json, time, tempfile) plus
  pytest.  The mcp Python SDK is NOT required in the test environment.

See tests/qa/_ai_docs/KI-011-HTTP-PROXY-HANG.md and
    tests/qa/_ai_docs/BUG-REPORT-KI011-MCP-COMPOSE-PROXY-HANG.md
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.stdio_transport

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WARM_ITERATIONS = 20
TOOL_TIMEOUT = 60  # seconds per individual tool call

# Port for environments_mcp_server in STDIO test runs.
# Deliberately different from the HTTP-test port (4041) so both test files
# can run in the same pytest session without port conflicts.
DOWNSTREAM_PORT = 4042

_DEFAULT_CONDA_ENV = os.environ.get("MCP_SERVER_CONDA_ENV", "anaconda-mcp-rc-py313")

NONEXISTENT_ENV_PREFIX = "/tmp/nonexistent-conda-env-xyz123"
NONEXISTENT_PKG = "this-package-does-not-exist-xyz123abc"

_HANG_FAIL_MSG = (
    "mcp-compose STDIO proxy did not forward the error response from "
    "environments_mcp_server within {timeout}s (iteration {iteration}/{total}). "
    "The internal HTTP session to port 4042 was likely abandoned. "
    "Matches the KI-011 hang pattern — the race condition in mcp-compose's "
    "internal Streamable HTTP pool is NOT gated on upstream transport. "
    "Observed on 2026-03-06 with STDIO transport, Python 3.13."
)


# ---------------------------------------------------------------------------
# Low-level STDIO JSON-RPC helpers
# ---------------------------------------------------------------------------

def _send(proc: subprocess.Popen, msg: dict) -> None:
    """Write one JSON-RPC message to the subprocess stdin."""
    line = json.dumps(msg).encode() + b"\n"
    proc.stdin.write(line)
    proc.stdin.flush()


def _recv(proc: subprocess.Popen, *, timeout: float = TOOL_TIMEOUT) -> dict:
    """
    Read one JSON-RPC message from the subprocess stdout.

    Uses a daemon thread so the main thread can enforce a hard timeout:
    if no complete line arrives within `timeout` seconds, raises TimeoutError.
    This is the STDIO equivalent of the SIGALRM mechanism in mcp_client.py —
    it detects a hang where mcp-compose never writes a response.
    """
    result: list = [None]
    exc: list = [None]

    def _read() -> None:
        try:
            result[0] = proc.stdout.readline()
        except Exception as e:
            exc[0] = e

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        raise TimeoutError(
            f"_recv: no response within {timeout}s "
            "(mcp-compose did not write to stdout — likely a STDIO hang, KI-011 variant)"
        )
    if exc[0]:
        raise exc[0]
    if not result[0]:
        raise EOFError("mcp-compose stdout closed unexpectedly")

    return json.loads(result[0])


# ---------------------------------------------------------------------------
# STDIO config writer
# ---------------------------------------------------------------------------

def _write_stdio_config(downstream_port: int, conda_env: str) -> Path:
    """
    Write a mcp-compose TOML config that enables STDIO upstream transport and
    auto-starts environments_mcp_server on `downstream_port`.

    Returns the path to the temporary config file (caller is responsible for
    cleanup, or it is cleaned up when the OS recycles /tmp).
    """
    python_path = subprocess.run(
        ["conda", "run", "-n", conda_env, "which", "python"],
        capture_output=True,
        text=True,
    ).stdout.strip() or "python"

    config_text = f"""\
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"

[transport]
stdio_enabled = true
streamable_http_enabled = false
sse_enabled = false

[[servers.proxied.streamable-http]]
name = "conda"
url = "http://localhost:{downstream_port}/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["{python_path}", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "{downstream_port}"]
startup_delay = 5

[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = false
"""
    fd, path = tempfile.mkstemp(suffix="-stdio-config.toml", prefix="anaconda-mcp-")
    os.write(fd, config_text.encode())
    os.close(fd)
    return Path(path)


# ---------------------------------------------------------------------------
# Fixture: STDIO mcp-compose subprocess (function-scoped for test isolation)
# ---------------------------------------------------------------------------

@pytest.fixture
def stdio_server(request: pytest.FixtureRequest):
    """
    Spawn anaconda-mcp serve in STDIO mode and return the ready subprocess.

    Function-scoped so each test gets a fresh mcp-compose process.

    This mirrors the function-scoped session_id fixture used by the HTTP tests:
    HANG-001 and HANG-002 deliberately trigger a proxy hang that permanently
    corrupts mcp-compose's internal connection pool.  With a shared subprocess,
    HANG-003 would inherit that corruption and fail during warm-up — masking
    whether HANG-003 found an independent regression or merely inherited the
    damage.  A fresh process per test ensures every result is independent.

    Lifecycle:
      1. Write a STDIO-specific config to a temp file.
      2. Spawn 'conda run -n <env> anaconda-mcp serve --config <file>'
         with stdin=PIPE / stdout=PIPE / stderr=PIPE.
      3. Send MCP initialize + notifications/initialized.
      4. Yield the Popen object for tests to use.
      5. Kill the subprocess and clean up on teardown.
    """
    conda_env = request.config.getoption("--server-conda-env", default=_DEFAULT_CONDA_ENV)
    config_path = _write_stdio_config(DOWNSTREAM_PORT, conda_env)
    logger.info(
        "Starting mcp-compose STDIO server (env=%s, downstream_port=%d, config=%s)",
        conda_env, DOWNSTREAM_PORT, config_path,
    )

    proc = subprocess.Popen(
        [
            "conda", "run", "-n", conda_env, "--no-capture-output",
            "anaconda-mcp", "serve", "--config", str(config_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    try:
        _send(proc, {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "stdio-hang-test", "version": "1.0"},
            },
        })

        init_resp = _recv(proc, timeout=45)
        logger.info(
            "STDIO server ready — serverInfo: %s",
            init_resp.get("result", {}).get("serverInfo"),
        )

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    except Exception as exc:
        proc.kill()
        config_path.unlink(missing_ok=True)
        pytest.fail(f"STDIO server did not become ready: {exc}")

    yield proc

    logger.info("Tearing down STDIO server (pid=%d)", proc.pid)
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    config_path.unlink(missing_ok=True)
    logger.info("STDIO server stopped")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NEXT_ID = 1


def _call_tool_stdio(proc: subprocess.Popen, tool_name: str, arguments: dict) -> dict:
    """
    Send a tools/call request over STDIO and return the parsed response dict.

    Raises TimeoutError if no response arrives within TOOL_TIMEOUT seconds.
    Skips notifications and other non-matching messages until the response
    with the matching id arrives.
    """
    global _NEXT_ID
    req_id = _NEXT_ID
    _NEXT_ID += 1

    _send(proc, {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    })

    deadline = time.monotonic() + TOOL_TIMEOUT
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"_call_tool_stdio: no response for id={req_id} within {TOOL_TIMEOUT}s"
            )
        msg = _recv(proc, timeout=remaining)
        if msg.get("id") == req_id:
            return msg
        logger.debug("STDIO: skipping notification/other: %s", msg.get("method"))


def _is_error(response: dict) -> bool:
    """
    Return True if the MCP tool result represents an error.

    STDIO and HTTP transports return different response shapes:

    HTTP (Streamable HTTP via mcp-compose):
      result.isError = True
      result.content = [{"type": "text", "text": "{\"is_error\":true,...}"}]

    STDIO (mcp-compose STDIO mode):
      result.isError = False   ← MCP protocol level says success
      result.content = [{"type": "text", "text": "{\"is_error\":true,...}"}]
      The actual error is serialised as a JSON string inside content[0].text.

    We check both the top-level isError flag AND the embedded JSON in each
    content text item so the same helper works for both transports.
    """
    result = response.get("result", {})
    if not isinstance(result, dict):
        return False

    if result.get("isError"):
        return True

    for item in result.get("content", []):
        if not isinstance(item, dict):
            continue
        if item.get("isError"):
            return True
        if item.get("type") == "text":
            try:
                parsed = json.loads(item.get("text", ""))
                if parsed.get("is_error") or parsed.get("isError"):
                    return True
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass

    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.slow
class TestProxyErrorHangStdio:
    """
    Regression: mcp-compose STDIO proxy must forward error responses from
    environments_mcp_server within TOOL_TIMEOUT — not abandon the backend
    session and leave the pipe hanging.

    These tests mirror TestProxyErrorHangHttp (test_guard_proxy_error_hang.py)
    exactly, using STDIO transport instead of Streamable HTTP.

    Test result (2026-03-06):
      STDIO-HANG-001 failed at iteration 16/20 (HTTP fails at iteration 4).
      STDIO-HANG-002 failed at iteration 1/20 (server already corrupted by
      HANG-001 in that run — they shared a subprocess).  With function-scoped
      stdio_server, each test now gets a clean process.

      The race condition is in mcp-compose's internal Streamable HTTP pool to
      port 4042, independent of upstream transport.
    """

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS)
    def test_stdio_hang_001_remove_nonexistent_env_does_not_hang(self, stdio_server):
        """
        STDIO-HANG-001: conda_remove_environment for a non-existent prefix must
        return an isError=true response within TOOL_TIMEOUT seconds on every
        iteration across WARM_ITERATIONS repeated calls, over STDIO transport.

        Mirrors HTTP HANG-001.

        If the race condition fires on any iteration, TimeoutError is raised
        and the test fails with the iteration number.

        Reproduced (2026-03-06): hangs at iteration 16/20 over STDIO transport.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "STDIO-HANG-001 [%d/%d] remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            t0 = time.monotonic()
            try:
                response = _call_tool_stdio(
                    stdio_server,
                    "conda_remove_environment",
                    {"prefix": NONEXISTENT_ENV_PREFIX},
                )
            except TimeoutError:
                pytest.fail(
                    f"STDIO-HANG-001: conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )

            elapsed = time.monotonic() - t0
            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-001 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, elapsed, is_err,
            )
            assert is_err, (
                f"STDIO-HANG-001 [{i}/{WARM_ITERATIONS}]: expected isError=true "
                f"for non-existent prefix '{NONEXISTENT_ENV_PREFIX}', got: {response}"
            )

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS)
    def test_stdio_hang_002_install_into_nonexistent_env_does_not_hang(self, stdio_server):
        """
        STDIO-HANG-002: conda_install_packages targeting a non-existent prefix
        must return an isError=true response within TOOL_TIMEOUT seconds on
        every iteration across WARM_ITERATIONS repeated calls, over STDIO.

        Mirrors HTTP HANG-002.  Exercises a different code path in
        environments_mcp_server from HANG-001.
        """
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "STDIO-HANG-002 [%d/%d] install_packages prefix=%s pkg=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX, NONEXISTENT_PKG,
            )
            t0 = time.monotonic()
            try:
                response = _call_tool_stdio(
                    stdio_server,
                    "conda_install_packages",
                    {"prefix": NONEXISTENT_ENV_PREFIX, "packages": [NONEXISTENT_PKG]},
                )
            except TimeoutError:
                pytest.fail(
                    f"STDIO-HANG-002: conda_install_packages hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )

            elapsed = time.monotonic() - t0
            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-002 [%d/%d] done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, elapsed, is_err,
            )
            assert is_err, (
                f"STDIO-HANG-002 [{i}/{WARM_ITERATIONS}]: expected isError=true "
                f"for non-existent prefix '{NONEXISTENT_ENV_PREFIX}', got: {response}"
            )

    @pytest.mark.timeout(TOOL_TIMEOUT * WARM_ITERATIONS * 3)
    def test_stdio_hang_003_server_survives_error_response(self, stdio_server):
        """
        STDIO-HANG-003: the mcp-compose STDIO server must remain functional after
        forwarding an error response — subsequent tool calls must also complete
        within TOOL_TIMEOUT.

        Mirrors HTTP HANG-003.

        Sequence:
          Phase 1 — warm-up: WARM_ITERATIONS successful conda_list_environments
            calls to accumulate session state before the first error.  This
            simulates a real chat session that has been active for some time
            before encountering an error.
          Phase 2 — looped error+health: WARM_ITERATIONS iterations of:
            (a) trigger an error (remove_environment on non-existent prefix)
            (b) immediately call a healthy tool (conda_list_environments)

        Two failure modes this test can catch:

        1. Warm-up hangs on iteration 1 (KI-011 server-level corruption):
           The mcp-compose process is already corrupted — its internal HTTP
           connection pool to port 4042 is permanently stuck.  Because
           stdio_server is function-scoped, this should only happen if the
           corruption occurs within HANG-003 itself, not leaked from HANG-001
           or HANG-002.

        2. Warm-up passes, health step hangs in Phase 2 (observed 2026-03-06):
           The proxy corrupts its internal state while forwarding an error,
           causing the immediately following healthy call to hang — even though
           the error call itself returned within TOOL_TIMEOUT.  Observed at
           Phase 2 iteration 20/20: all 20 warm-up calls and 19 full error+health
           cycles completed, then the 20th health call after an error timed out.

        For HANG-003 to test mode 2 independently, run it against a fresh
        server in isolation:
          python -m pytest tests/qa/stdio_tools/test_guard_proxy_error_hang_stdio.py \
              -k test_stdio_hang_003 -v

        The @pytest.mark.timeout uses WARM_ITERATIONS * 3 because three
        round-trips are made per iteration (1 warm-up + 1 error + 1 healthy).
        """
        # Phase 1: warm up the server with WARM_ITERATIONS healthy calls
        logger.info(
            "STDIO-HANG-003 warm-up: %d × conda_list_environments to accumulate session state",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info("STDIO-HANG-003 warm-up [%d/%d] list_environments", i, WARM_ITERATIONS)
            t0 = time.monotonic()
            try:
                _call_tool_stdio(stdio_server, "conda_list_environments", {})
            except TimeoutError:
                pytest.fail(
                    f"STDIO-HANG-003 warm-up iteration {i}/{WARM_ITERATIONS}: "
                    f"conda_list_environments hung on a healthy call. "
                    f"This is KI-011 server-level corruption: mcp-compose's internal "
                    f"HTTP connection pool to port {DOWNSTREAM_PORT} is permanently stuck. "
                    f"A server restart is required to recover. "
                    f"To test HANG-003 independently, run it in isolation against a "
                    f"fresh server."
                )
            logger.info(
                "STDIO-HANG-003 warm-up [%d/%d] done in %.2fs",
                i, WARM_ITERATIONS, time.monotonic() - t0,
            )

        # Phase 2: WARM_ITERATIONS × (error trigger → server health check)
        logger.info(
            "STDIO-HANG-003: warm-up done — starting %d × error+health iterations",
            WARM_ITERATIONS,
        )
        for i in range(1, WARM_ITERATIONS + 1):
            logger.info(
                "STDIO-HANG-003 [%d/%d] error step: remove_environment prefix=%s",
                i, WARM_ITERATIONS, NONEXISTENT_ENV_PREFIX,
            )
            t0 = time.monotonic()
            try:
                _call_tool_stdio(
                    stdio_server,
                    "conda_remove_environment",
                    {"prefix": NONEXISTENT_ENV_PREFIX},
                )
            except TimeoutError:
                pytest.fail(
                    f"STDIO-HANG-003 iteration {i}/{WARM_ITERATIONS} (error step): "
                    f"conda_remove_environment hung for > {TOOL_TIMEOUT}s. "
                    + _HANG_FAIL_MSG.format(
                        timeout=TOOL_TIMEOUT, iteration=i, total=WARM_ITERATIONS
                    )
                )
            logger.info(
                "STDIO-HANG-003 [%d/%d] error step done in %.2fs",
                i, WARM_ITERATIONS, time.monotonic() - t0,
            )

            logger.info(
                "STDIO-HANG-003 [%d/%d] health step: list_environments",
                i, WARM_ITERATIONS,
            )
            t0 = time.monotonic()
            try:
                response = _call_tool_stdio(stdio_server, "conda_list_environments", {})
            except TimeoutError:
                pytest.fail(
                    f"STDIO-HANG-003 iteration {i}/{WARM_ITERATIONS} (health step): "
                    f"server hung after an error response. "
                    "mcp-compose STDIO proxy corrupted the internal session state "
                    "while handling the error from environments_mcp_server. "
                    "All subsequent calls on this pipe will also hang until "
                    "the MCP server is restarted. Matches KI-011."
                )

            is_err = _is_error(response)
            logger.info(
                "STDIO-HANG-003 [%d/%d] health step done in %.2fs — is_error=%s",
                i, WARM_ITERATIONS, time.monotonic() - t0, is_err,
            )
            assert not is_err, (
                f"STDIO-HANG-003 iteration {i}/{WARM_ITERATIONS}: "
                f"conda_list_environments returned an error after the server "
                f"survived the previous error: {response}"
            )

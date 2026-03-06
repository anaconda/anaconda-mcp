"""
STDIO MCP client utilities for the stdio_tools suite.

Provides the single entry point for tool calls (_call_tool_stdio) and helpers
for writing mcp-compose STDIO config files and parsing tool responses.

All test fixtures and test methods must use _call_tool_stdio instead of
constructing raw JSON-RPC messages directly.

Timeout implementation note
---------------------------
_recv uses a daemon thread with readline() to enforce a hard per-call deadline.
If mcp-compose stops writing to stdout (the STDIO equivalent of the SSE-keepalive
hang in KI-011), the daemon thread blocks indefinitely while the main thread
raises TimeoutError after TOOL_TIMEOUT seconds.

This mirrors the SIGALRM mechanism used in http_tools/common/utils/mcp_client.py
but works on all platforms since it relies only on threading (no signal.SIGALRM).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import pytest

from common.constants.config import TOOL_TIMEOUT

logger = logging.getLogger(__name__)

_NEXT_ID = 1


# ---------------------------------------------------------------------------
# Low-level STDIO JSON-RPC primitives
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

    Returns the resolved absolute path to the temporary config file.
    The caller is responsible for cleanup (or it is cleaned up when the OS
    recycles /tmp).
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
    fd, path_str = tempfile.mkstemp(suffix="-stdio-config.toml", prefix="anaconda-mcp-")
    os.close(fd)
    config_path = Path(path_str).resolve()
    config_path.write_text(config_text, encoding="utf-8")
    return config_path


# ---------------------------------------------------------------------------
# Tool call entry point
# ---------------------------------------------------------------------------

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

    logger.info("Calling MCP tool '%s' over STDIO with arguments: %s", tool_name, arguments)

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
            logger.debug("STDIO tool response for id=%d: %s", req_id, msg)
            return msg
        logger.debug("STDIO: skipping notification/other: %s", msg.get("method"))


# ---------------------------------------------------------------------------
# Hang-safe call wrapper
# ---------------------------------------------------------------------------

def _call_no_hang(
    proc: subprocess.Popen,
    tool_name: str,
    arguments: dict,
    fail_msg: str,
) -> tuple[dict, float]:
    """
    Call a tool via STDIO and fail the test immediately on TimeoutError.

    Returns (response, elapsed_seconds). Use in place of a bare
    try/except TimeoutError block when the test should fail fast on a hang.
    """
    t0 = time.monotonic()
    try:
        response = _call_tool_stdio(proc, tool_name, arguments)
    except TimeoutError:
        pytest.fail(fail_msg)
    return response, time.monotonic() - t0


# ---------------------------------------------------------------------------
# Response inspector
# ---------------------------------------------------------------------------

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

    Checks both the top-level isError flag AND the embedded JSON in each
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

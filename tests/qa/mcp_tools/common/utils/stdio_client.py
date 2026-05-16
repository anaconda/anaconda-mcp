"""
STDIO MCP client utilities for the unified mcp_tools suite.

Provides tool calls over newline-delimited JSON-RPC and helpers for writing
mcp-compose config for any profile (stdio-stdio, stdio-http).
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

import mcp_compose_profiles as _profiles
import pytest

from common.constants.config import TOOL_TIMEOUT

logger = logging.getLogger(__name__)

_NEXT_ID = 1


def _send(proc: subprocess.Popen, msg: dict) -> None:
    """Write one JSON-RPC message to the subprocess stdin."""
    if proc.stdin is None:
        raise RuntimeError("subprocess stdin is closed")
    line = json.dumps(msg).encode() + b"\n"
    proc.stdin.write(line)
    proc.stdin.flush()


def _recv(proc: subprocess.Popen, *, timeout: float = TOOL_TIMEOUT) -> dict:
    """
    Read one JSON-RPC message from the subprocess stdout.

    Uses a daemon thread so the main thread can enforce a hard timeout.
    """
    result: list = [None]
    exc: list = [None]

    def _read() -> None:
        try:
            if proc.stdout is None:
                raise RuntimeError("subprocess stdout is closed")
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

    decoded = json.loads(result[0])
    if not isinstance(decoded, dict):
        raise ValueError(f"expected JSON object from mcp-compose, got {type(decoded)}")
    return decoded


def _write_profile_config(
    profile_slug: str,
    conda_env: str,
    *,
    compose_port: int,
    downstream_port: int,
) -> Path:
    """
    Write mcp-compose TOML for the given profile slug and return the config path.

    ``profile_slug`` must be ``stdio-http`` or ``stdio-stdio`` (STDIO client edge).
    """
    profile = _profiles.PROFILES_BY_SLUG[profile_slug]
    # Use sys.executable via conda run for cross-platform compatibility
    # ("which python" doesn't work on Windows)
    python_path = (
        subprocess.run(
            ["conda", "run", "-n", conda_env, "python", "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        or "python"
    )

    config_text = _profiles.render_for_profile(
        profile,
        compose_port=compose_port,
        downstream_port=downstream_port,
        python_executable=python_path,
    )
    fd, path_str = tempfile.mkstemp(suffix="-mcp-config.toml", prefix="anaconda-mcp-")
    os.close(fd)
    config_path = Path(path_str).resolve()
    config_path.write_text(config_text, encoding="utf-8")
    return config_path


def _call_tool_stdio(proc: subprocess.Popen, tool_name: str, arguments: dict) -> dict:
    """Send a tools/call request over STDIO and return the parsed response dict."""
    global _NEXT_ID
    req_id = _NEXT_ID
    _NEXT_ID += 1

    logger.info("Calling MCP tool '%s' over STDIO with arguments: %s", tool_name, arguments)

    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
    )

    deadline = time.monotonic() + TOOL_TIMEOUT
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"_call_tool_stdio: no response for id={req_id} within {TOOL_TIMEOUT}s")
        msg = _recv(proc, timeout=remaining)
        if msg.get("id") == req_id:
            logger.debug("STDIO tool response for id=%d: %s", req_id, msg)
            return msg
        logger.debug("STDIO: skipping notification/other: %s", msg.get("method"))


def _call_no_hang_stdio(
    proc: subprocess.Popen,
    tool_name: str,
    arguments: dict,
    fail_msg: str,
) -> tuple[dict, float]:
    """Call a tool via STDIO and fail the test immediately on TimeoutError."""
    t0 = time.monotonic()
    try:
        response = _call_tool_stdio(proc, tool_name, arguments)
    except TimeoutError:
        pytest.fail(fail_msg)
    return response, time.monotonic() - t0


def _is_error(response: dict) -> bool:
    """Return True if the MCP tool result represents an error (HTTP or STDIO shapes)."""
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

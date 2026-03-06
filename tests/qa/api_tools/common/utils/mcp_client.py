"""
MCP HTTP client utilities.

Provides the single entry point for tool calls (_call_tool) and helpers for
parsing MCP responses and extracting tool result payloads.

All test files must use _call_tool instead of constructing HTTP requests
directly to ensure consistent timeout handling and SSE parsing.

Timeout implementation note
---------------------------
mcp-compose responds to tool calls with a Streamable HTTP / SSE response.
When the proxy hangs (KI-011), it keeps the upstream HTTP connection alive by
sending SSE keepalive bytes, which resets the httpx per-chunk `read` timeout
indefinitely.  The only reliable way to interrupt a blocking socket recv() on
UNIX is SIGALRM: signal.alarm(N) delivers SIGALRM after N seconds, which
Python converts to a raised exception even inside a blocking system call.

_call_tool therefore installs a temporary SIGALRM handler for TOOL_TIMEOUT
seconds around the httpx.post() call.  On platforms without signal.SIGALRM
(Windows) it falls back to the httpx per-chunk read timeout, which may not
catch SSE-keepalive hangs but is better than nothing.
"""

from __future__ import annotations

import json
import logging
import signal
import time

import httpx

from common.constants.config import BASE_URL, TOOL_TIMEOUT

logger = logging.getLogger(__name__)

_HAS_SIGALRM = hasattr(signal, "SIGALRM")


def _parse_mcp_response(response: httpx.Response, elapsed_s: float) -> dict:
    """
    Parse an MCP HTTP response that may be plain JSON or SSE-wrapped JSON.

    Streamable HTTP servers return responses as SSE events even on POST:
        event: message\\r\\ndata: {"jsonrpc":"2.0",...}\\r\\n\\r\\n

    Extract the JSON payload from the first `data:` line.

    Logs the response type and elapsed time at INFO level — this is the key
    indicator of the KI-011 race condition: an unexpected SSE response on a
    callTool POST means the proxy opened the GET stream before initialize
    completed, causing the tool result to be delivered via SSE rather than
    inline in the POST body.
    """
    content_type = response.headers.get("content-type", "")
    text = response.text

    if "text/event-stream" in content_type or text.lstrip().startswith("event:"):
        logger.info(
            "response: SSE (%.2fs) content-type=%s body_bytes=%d",
            elapsed_s, content_type, len(text),
        )
        for line in text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:"):].strip())
        raise ValueError(f"No data: line found in SSE response: {text!r}")

    logger.info(
        "response: JSON (%.2fs) content-type=%s body_bytes=%d",
        elapsed_s, content_type, len(text),
    )
    return response.json()


def _call_tool(tool_name: str, arguments: dict, session_id: str | None) -> dict:
    """
    Call an MCP tool and return the parsed JSON-RPC response.

    Raises httpx.ReadTimeout if no complete response is received within
    TOOL_TIMEOUT seconds — callers that test for hangs should catch this.

    The timeout is enforced via SIGALRM on UNIX so that it fires even when
    the server streams SSE keepalive bytes (which defeat the httpx per-chunk
    read timeout).  See module docstring for details.

    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    logger.info("Calling MCP tool '%s' with arguments: %s", tool_name, arguments)

    headers = {"Accept": "application/json, text/event-stream"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    def _do_post() -> httpx.Response:
        return httpx.post(
            BASE_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers=headers,
            timeout=httpx.Timeout(connect=10, read=TOOL_TIMEOUT, write=10, pool=10),
        )

    t0 = time.monotonic()

    if _HAS_SIGALRM:
        def _alarm_handler(signum, frame):
            elapsed = time.monotonic() - t0
            raise httpx.ReadTimeout(
                f"_call_tool: no complete response within {TOOL_TIMEOUT}s "
                f"(SIGALRM fired after {elapsed:.1f}s — "
                "likely an SSE-keepalive hang, KI-011)"
            )

        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(TOOL_TIMEOUT)
        try:
            response = _do_post()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        response = _do_post()

    elapsed_s = time.monotonic() - t0
    response.raise_for_status()
    return _parse_mcp_response(response, elapsed_s)


def _initialize_session(server_url: str, client_name: str = "api-tools-test") -> str | None:
    """
    Perform the MCP initialize handshake and return the session ID (may be None).

    Sends POST initialize, extracts Mcp-Session-Id from the response headers,
    then sends POST notifications/initialized to complete the handshake.

    Use this instead of duplicating the two-request sequence in fixtures.
    """
    logger.info("Initializing MCP session at %s", server_url)
    response = httpx.post(
        server_url,
        json={
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": client_name, "version": "1.0"},
            },
        },
        headers={"Accept": "application/json, text/event-stream"},
        timeout=10,
    )
    sid = response.headers.get("mcp-session-id")
    logger.debug("MCP session established (session-id present: %s)", sid is not None)

    headers: dict[str, str] = {"Accept": "application/json, text/event-stream"}
    if sid:
        headers["Mcp-Session-Id"] = sid
    try:
        httpx.post(
            server_url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            headers=headers,
            timeout=5,
        )
    except Exception:
        pass

    return sid


def _tool_result(response_json: dict) -> dict:
    """
    Extract and JSON-parse the tool result payload from a tools/call response.

    MCP tool results are returned as a list of content items; this helper
    finds the first text item whose content is a JSON object and returns it
    as a dict. Returns an empty dict if no parseable result is found.
    """
    content = response_json.get("result", {}).get("content", [])
    text = next((c["text"] for c in content if c.get("type") == "text"), None)
    if text and text.strip().startswith("{"):
        return json.loads(text)
    return {}

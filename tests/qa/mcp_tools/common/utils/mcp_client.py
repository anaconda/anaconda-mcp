"""
MCP HTTP client utilities.

Provides the single entry point for tool calls (_call_tool) and helpers for
parsing MCP responses and extracting tool result payloads.

All test files must use _call_tool instead of constructing HTTP requests
directly to ensure consistent timeout handling and SSE parsing.

Timeout implementation note
---------------------------
``httpx.Timeout(read=…)`` limits idle time between bytes. Streamable HTTP/SSE
**keepalives** can reset that timer, so a missing tool result may never trigger
``ReadTimeout`` (multi-minute hangs).

Each ``tools/call`` is therefore bounded by a **wall-clock** cap: the blocking
``httpx.post`` runs in a one-shot ``ThreadPoolExecutor`` worker and the main
thread uses ``Future.result(timeout=…)``. After a wall timeout we raise
``httpx.ReadTimeout`` so hang tests fail fast; the worker may still finish in
the background.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import time

import httpx
import pytest

from common.constants.config import BASE_URL, TOOL_CALL_WALL_SECONDS, TOOL_TIMEOUT

logger = logging.getLogger(__name__)


def _sse_data_json_objects(text: str) -> list[dict]:
    """Parse each non-empty ``data:`` line in an SSE body as JSON."""
    out: list[dict] = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        raw = line[len("data:") :].strip()
        if not raw or raw == "[DONE]" or raw.startswith(":"):
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            logger.debug("Skipping non-JSON SSE data line: %r", raw[:120])
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _pick_jsonrpc_for_tool_response(candidates: list[dict]) -> dict:
    """
    Streamable HTTP may send multiple SSE ``data:`` lines; the first parseable JSON
    is not always the ``tools/call`` reply (e.g. session or keepalive). Prefer the
    last object whose ``result`` looks like a CallTool payload.
    """
    if not candidates:
        return {}
    for obj in reversed(candidates):
        res = obj.get("result")
        if isinstance(res, dict) and (res.get("content") or res.get("structuredContent")):
            return obj
        if "error" in obj:
            return obj
    return candidates[-1]


def _parse_mcp_response(response: httpx.Response, elapsed_s: float) -> dict:
    """
    Parse an MCP HTTP response that may be plain JSON or SSE-wrapped JSON.

    Streamable HTTP servers return responses as SSE events even on POST:
        event: message\\r\\ndata: {"jsonrpc":"2.0",...}\\r\\n\\r\\n

    Extract the JSON-RPC payload from SSE ``data:`` lines (prefer the event that
    carries the tool ``result`` / ``error``, not an earlier heartbeat).

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
            elapsed_s,
            content_type,
            len(text),
        )
        candidates = _sse_data_json_objects(text)
        if not candidates:
            raise ValueError(f"No JSON data: lines in SSE response: {text!r}")
        return _pick_jsonrpc_for_tool_response(candidates)

    logger.info(
        "response: JSON (%.2fs) content-type=%s body_bytes=%d",
        elapsed_s,
        content_type,
        len(text),
    )
    body = response.json()
    if not isinstance(body, dict):
        raise TypeError(f"expected JSON object from MCP HTTP response, got {type(body)}")
    return body


def _call_tool_blocking(
    tool_name: str,
    arguments: dict,
    session_id: str | None,
) -> dict:
    """Perform synchronous ``tools/call`` (runs in a worker thread when wrapped)."""
    headers = {"Accept": "application/json, text/event-stream"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    request_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    logger.debug("[REQUEST] headers=%s body=%s", headers, request_body)

    t0 = time.monotonic()
    logger.debug("[TIMING] request started at t=0")

    response = httpx.post(
        BASE_URL,
        json=request_body,
        headers=headers,
        timeout=httpx.Timeout(connect=10, read=TOOL_TIMEOUT, write=10, pool=10),
    )

    elapsed_s = time.monotonic() - t0
    logger.info(
        "[RESPONSE] status=%d elapsed=%.2fs content-type=%s body_len=%d",
        response.status_code,
        elapsed_s,
        response.headers.get("content-type", "?"),
        len(response.text),
    )
    logger.debug("[RESPONSE] headers=%s", dict(response.headers))
    response.raise_for_status()
    return _parse_mcp_response(response, elapsed_s)


def _call_tool(tool_name: str, arguments: dict, session_id: str | None) -> dict:
    """
    Call an MCP tool and return the parsed JSON-RPC response.

    Raises ``httpx.ReadTimeout`` on per-read timeouts **or** if the full call
    exceeds ``TOOL_CALL_WALL_SECONDS`` wall time (SSE keepalive case).

    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    logger.info(
        "[CALL] tool=%s args=%s session_id=%s read_timeout=%ds wall=%ds url=%s",
        tool_name,
        arguments,
        session_id[:8] + "..." if session_id else None,
        TOOL_TIMEOUT,
        TOOL_CALL_WALL_SECONDS,
        BASE_URL,
    )

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        fut = pool.submit(_call_tool_blocking, tool_name, arguments, session_id)
        try:
            return fut.result(timeout=TOOL_CALL_WALL_SECONDS)
        except concurrent.futures.TimeoutError as exc:
            raise httpx.ReadTimeout(
                f"MCP tools/call exceeded {TOOL_CALL_WALL_SECONDS}s wall clock "
                "(possible SSE keepalive stall without tool result)"
            ) from exc
    finally:
        pool.shutdown(wait=False)


def _call_no_hang(
    tool_name: str,
    arguments: dict,
    session_id: str | None,
    fail_msg: str,
) -> tuple[dict, float]:
    """
    Call a tool and fail the test immediately on httpx.ReadTimeout.

    Returns (response_json, elapsed_seconds). Use in place of a bare
    try/except ReadTimeout block when the test should fail fast on a hang.
    """
    t0 = time.monotonic()
    try:
        response = _call_tool(tool_name, arguments, session_id)
    except httpx.ReadTimeout:
        pytest.fail(fail_msg)
    return response, time.monotonic() - t0


def _initialize_session(server_url: str, client_name: str = "api-tools-test") -> str | None:
    """
    Perform the MCP initialize handshake and return the session ID (may be None).

    Sends POST initialize, extracts Mcp-Session-Id from the response headers,
    then sends POST notifications/initialized to complete the handshake.

    Use this instead of duplicating the two-request sequence in fixtures.
    """
    logger.info("[INIT] starting MCP session at %s (client=%s)", server_url, client_name)
    t0 = time.monotonic()
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
    elapsed = time.monotonic() - t0
    sid = response.headers.get("mcp-session-id")
    logger.info(
        "[INIT] initialize response: status=%d elapsed=%.2fs session_id=%s",
        response.status_code,
        elapsed,
        sid[:8] + "..." if sid else None,
    )
    logger.debug("[INIT] response headers=%s", dict(response.headers))

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

    return sid if isinstance(sid, str) else None


def _parse_tool_json_text(text: str) -> dict | None:
    """If ``text`` is a JSON object, return it as a dict (conda tool JSON-RPC body)."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _tool_result(response_json: dict) -> dict:
    """
    Extract and JSON-parse the tool result payload from a tools/call response.

    MCP tool results are usually JSON in ``content[].text``. Some stacks return
    **plain text** (e.g. ``Unknown tool: …``) with ``isError: true`` on the
    CallTool ``result`` — that must become an ``is_error``-shaped dict (KI-016).
    ``structuredContent.result`` may be a stringified JSON object or a dict.

    JSON-RPC ``error`` is mapped to an ``is_error``-shaped dict for validators.
    Returns an empty dict only if nothing can be interpreted.
    """
    if "error" in response_json:
        err = response_json["error"]
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        return {
            "is_error": True,
            "error_description": msg,
            "tool_result": {},
        }

    result = response_json.get("result") or {}
    if not isinstance(result, dict):
        return {}

    top_is_error = result.get("isError")
    if top_is_error is None:
        top_is_error = result.get("is_error")

    sc = result.get("structuredContent")
    if isinstance(sc, dict):
        inner = sc.get("result")
        if isinstance(inner, dict):
            return inner
        if isinstance(inner, str):
            parsed = _parse_tool_json_text(inner)
            if parsed is not None:
                return parsed

    content = result.get("content", [])
    text = next(
        (c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text"),
        None,
    )
    if text is not None and str(text).strip():
        parsed = _parse_tool_json_text(str(text))
        if parsed is not None:
            return parsed

        msg = str(text).strip()
        if top_is_error is True:
            return {
                "is_error": True,
                "error_description": msg,
                "tool_result": {},
            }
        if top_is_error is False:
            return {
                "is_error": False,
                "error_description": "",
                "tool_result": {"message": msg},
            }
        # isError omitted — treat obvious proxy/server errors as errors
        lower = msg.lower()
        if lower.startswith("unknown tool:") or "validation error" in lower:
            return {
                "is_error": True,
                "error_description": msg,
                "tool_result": {},
            }
        return {
            "is_error": False,
            "error_description": "",
            "tool_result": {"message": msg},
        }

    return {}

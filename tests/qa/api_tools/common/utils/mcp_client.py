"""
MCP HTTP client utilities.

Provides the single entry point for tool calls (_call_tool) and helpers for
parsing MCP responses and extracting tool result payloads.

All test files must use _call_tool instead of constructing HTTP requests
directly to ensure consistent timeout handling and SSE parsing.
"""

from __future__ import annotations

import json
import logging

import httpx

from common.constants.config import BASE_URL, TOOL_TIMEOUT

logger = logging.getLogger(__name__)


def _parse_mcp_response(response: httpx.Response) -> dict:
    """
    Parse an MCP HTTP response that may be plain JSON or SSE-wrapped JSON.

    Streamable HTTP servers return responses as SSE events even on POST:
        event: message\\r\\ndata: {"jsonrpc":"2.0",...}\\r\\n\\r\\n

    Extract the JSON payload from the first `data:` line.
    """
    content_type = response.headers.get("content-type", "")
    text = response.text

    logger.debug("MCP response content-type: %s, body: %s", content_type, text[:300])

    if "text/event-stream" in content_type or text.lstrip().startswith("event:"):
        for line in text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:"):].strip())
        raise ValueError(f"No data: line found in SSE response: {text!r}")

    return response.json()


def _call_tool(tool_name: str, arguments: dict, session_id: str | None) -> dict:
    """
    Call an MCP tool and return the parsed JSON-RPC response.

    Raises httpx.ReadTimeout if the server does not respond within TOOL_TIMEOUT
    seconds — callers that test for hangs should catch this explicitly.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    logger.info("Calling MCP tool '%s' with arguments: %s", tool_name, arguments)

    headers = {"Accept": "application/json, text/event-stream"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    response = httpx.post(
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
    response.raise_for_status()
    return _parse_mcp_response(response)


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

#!/usr/bin/env python3
"""
List MCP tool names after the same initialize + session handshake as pytest.

Requires an MCP HTTP server already listening (tests default to port 9888).

Usage (from repo root, with anaconda-mcp-qa or any env that has httpx):

  # Terminal A — start stack (uses server conda env with anaconda-mcp installed):
  conda activate <server-env>
  bash tests/qa/_ai_docs/scripts/start-http-server.sh 9888

  # Terminal B:
  python tests/qa/_ai_docs/scripts/check-tools.py
  MCP_SERVER_URL=http://127.0.0.1:9888/mcp python tests/qa/_ai_docs/scripts/check-tools.py

Debug empty tool list (prints raw SSE / response snippet):

  MCP_CHECK_TOOLS_VERBOSE=1 python tests/qa/_ai_docs/scripts/check-tools.py
"""

from __future__ import annotations

import json
import os
import sys

import httpx

URL = os.environ.get("MCP_SERVER_URL", "http://localhost:9888/mcp")
VERBOSE = os.environ.get("MCP_CHECK_TOOLS_VERBOSE", "").lower() in ("1", "true", "yes")


def _tools_from_json_obj(obj: dict) -> list | None:
    """Return tools array from a JSON-RPC object, or None if absent."""
    res = obj.get("result")
    if not isinstance(res, dict):
        return None
    tools = res.get("tools")
    return tools if isinstance(tools, list) else None


def _parse_sse_json_objects(text: str) -> list[dict]:
    out: list[dict] = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        raw = line[len("data:") :].strip()
        if not raw or raw == "[DONE]":
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _best_tools_list(objs: list[dict]) -> list | None:
    """
    Streamable HTTP may emit several SSE ``data:`` lines; the first ``tools/list``
    payload is sometimes an empty list before proxied tools register. Prefer the
    longest non-empty ``tools`` array; otherwise the last non-None list.
    """
    best: list | None = None
    best_len = -1
    last: list | None = None
    for obj in objs:
        tools = _tools_from_json_obj(obj)
        if tools is None:
            continue
        last = tools
        if len(tools) > best_len:
            best_len = len(tools)
            best = tools
    if best_len > 0:
        return best
    return last


def main() -> None:
    headers: dict[str, str] = {"Accept": "application/json, text/event-stream"}

    try:
        _run_list(headers)
    except httpx.ConnectError as exc:
        print(
            f"Cannot connect to {URL} ({exc}).\n"
            "Start anaconda-mcp first, e.g. in another shell:\n"
            "  conda activate <server-env-with-anaconda-mcp>\n"
            "  bash tests/qa/_ai_docs/scripts/start-http-server.sh 9888\n"
            "Or run pytest with --start-server (see tests/qa/mcp_tools/README.md).\n"
            "Override URL: MCP_SERVER_URL=http://host:port/mcp python ...",
            file=sys.stderr,
        )
        sys.exit(2)


def _run_list(headers: dict[str, str]) -> None:
    r = httpx.post(
        URL,
        json={
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "manual-tools-list", "version": "1.0"},
            },
        },
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    sid = r.headers.get("mcp-session-id")
    if sid:
        headers = {**headers, "Mcp-Session-Id": sid}

    httpx.post(
        URL,
        json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        headers=headers,
        timeout=5,
    )

    r2 = httpx.post(
        URL,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers=headers,
        timeout=30,
    )
    r2.raise_for_status()

    text = r2.text
    ct = r2.headers.get("content-type", "")

    if VERBOSE:
        print("Content-Type:", ct, file=sys.stderr)
        print("Response (first 6000 chars):\n", text[:6000], file=sys.stderr)

    # Plain JSON response
    if "text/event-stream" not in ct and not text.lstrip().startswith("event:"):
        try:
            obj = r2.json()
        except json.JSONDecodeError:
            print("Non-JSON response:\n", text[:4000], file=sys.stderr)
            sys.exit(1)
        if not isinstance(obj, dict):
            print("Unexpected JSON (not object):\n", text[:4000], file=sys.stderr)
            sys.exit(1)
        tools = _best_tools_list([obj])
        if tools is not None:
            _print_tool_names(tools)
            return
        print("Unexpected JSON:\n", json.dumps(obj, indent=2)[:4000])
        sys.exit(1)

    objs = _parse_sse_json_objects(text)
    tools = _best_tools_list(objs)
    if tools is not None:
        _print_tool_names(tools)
        if not tools:
            print(
                "tools/list returned an empty list.\n"
                "If anaconda-mcp logged 'Tool registration failed' / 'Total tools: 0' for the "
                "conda Streamable HTTP upstream, the proxy has no tools until that is fixed — "
                "usually environments_mcp_server on the downstream port (see start-http-server.sh). "
                "Try running the downstream command by hand and check its traceback.\n"
                "Otherwise wait for registration after startup_delay and retry. "
                "Debug SSE: MCP_CHECK_TOOLS_VERBOSE=1",
                file=sys.stderr,
            )
        return

    print("Could not parse tools from SSE. Raw (first 4000 chars):\n", text[:4000], file=sys.stderr)
    sys.exit(1)


def _print_tool_names(tools: list) -> None:
    names = [t.get("name") for t in tools if isinstance(t, dict)]
    print("URL:", URL)
    print("Tool names:", json.dumps(names, indent=2))


if __name__ == "__main__":
    main()

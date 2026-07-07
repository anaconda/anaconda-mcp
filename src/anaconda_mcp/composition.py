"""Native FastMCP composition for ``anaconda mcp serve``.

``PlatformMiddleware`` enforces authentication and Terms-of-Service acceptance and
emits tool telemetry for *every* tool call. As a FastMCP middleware on the parent
server, ``on_call_tool`` fires for tools served by both in-process mounted
sub-servers (conda) and remote proxied sub-servers (search), providing one
central enforcement and telemetry path.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Generator

import httpx
import mcp.types as mt
from anaconda_anon_usage.tokens import client_token
from anaconda_cli_base.telemetry import traced as _otel_traced
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server import create_proxy
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult

from anaconda_mcp.auth import AuthenticationError, get_auth_token, validate_auth_token
from anaconda_mcp.config import settings
from anaconda_mcp.telemetry import (
    PII_KEY_AAU_CLIENT_ID,
    MetricNames,
    _emit_tool_metrics,
    _get_client_info,
    emit_event,
)
from anaconda_mcp.terms import verify_terms_accepted

logger = logging.getLogger(__name__)


class PlatformMiddleware(Middleware):
    """Per-call auth + TOS enforcement and tool telemetry.

    Fires for both mounted (conda) and proxied (search) sub-server tools because
    the parent server's middleware runs before tool resolution/dispatch.
    """

    def __init__(self, aau_client_id: str | None = None, max_tool_call_history: int = 20) -> None:
        self._aau_client_id = aau_client_id
        self._tool_call_history: deque[str] = deque(maxlen=max_tool_call_history)

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        # --- auth enforcement ---
        token = get_auth_token()
        if token is None:
            raise AuthenticationError("Not authenticated. Please run 'anaconda login' to re-authenticate.")
        if not validate_auth_token(token):
            raise AuthenticationError(
                "Authentication token is invalid or expired. Please run 'anaconda login' to re-authenticate."
            )
        # --- TOS enforcement ---
        verify_terms_accepted()
        # --- tool telemetry ---
        name = context.message.name
        start = time.monotonic()
        is_error = False
        error_description = ""
        try:
            with _otel_traced(f"mcp_tool_{name}", plugin_name="mcp", attributes={"tool": name}) as span:
                try:
                    return await call_next(context)
                except Exception as exc:
                    is_error = True
                    # Telemetry intentionally records only the exception class, not str(exc),
                    # which can carry PII / filesystem paths / channel tokens. Note this narrows
                    # the pre-refactor "Type: message" contract: dashboards keyed on the message
                    # half no longer receive it.
                    error_description = type(exc).__name__
                    try:
                        span.add_exception(exc)
                    except Exception:
                        logger.debug("OTel span exception annotation failed", exc_info=True)
                    raise
        finally:
            self._tool_call_history.append(name)
            if settings.send_metrics:
                try:
                    client_name, client_version = _get_client_info(getattr(context, "fastmcp_context", None))
                    duration_ms = round((time.monotonic() - start) * 1000, 2)
                    event_params: dict[str, object] = {
                        "tool_name": name,
                        "client_name": client_name,
                        "client_version": client_version,
                        "duration_ms": duration_ms,
                        "is_error": is_error,
                        "error_description": error_description,
                        "tool_call_history": ",".join(self._tool_call_history),
                    }
                    if self._aau_client_id is not None:
                        event_params[PII_KEY_AAU_CLIENT_ID] = self._aau_client_id
                    emit_event(MetricNames.TOOL_COMPLETED.value, event_params)
                    _emit_tool_metrics(name, duration_ms, is_error=is_error)
                except Exception:
                    logger.debug("tool telemetry emission failed", exc_info=True)


SEARCH_READ_TIMEOUT_SECONDS = 300
# Bounds the connect + initialize handshake so an unreachable/hanging search
# backend can't stall tool listing for the full read timeout above.
SEARCH_CONNECT_TIMEOUT_SECONDS = 10


class _DynamicBearerAuth(httpx.Auth):
    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        token = get_auth_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token}"
        yield request


def build_composed_server() -> FastMCP:
    """Compose the anaconda-mcp server natively on FastMCP.

    - conda tools are mounted in-process (no subprocess, no proxy readline/timeout);
    - the remote search server is proxied with bearer auth;
    - a single ``PlatformMiddleware`` enforces auth/TOS and emits telemetry for
      every tool call across both the mounted (conda) and proxied (search) servers.
    """
    from anaconda_mcp.conda_mcp_lite import server as conda_server

    parent = FastMCP(
        "anaconda-mcp",
        middleware=[PlatformMiddleware(aau_client_id=client_token() or None)],
    )
    parent.mount(conda_server.mcp, namespace="conda")

    domain = settings.anaconda_domain or "anaconda.com"
    search_url = f"https://{domain}/api/search/mcp"
    search_client = Client(
        StreamableHttpTransport(search_url, auth=_DynamicBearerAuth()),
        timeout=SEARCH_READ_TIMEOUT_SECONDS,
        init_timeout=SEARCH_CONNECT_TIMEOUT_SECONDS,
    )
    parent.mount(create_proxy(search_client), namespace="search")
    return parent

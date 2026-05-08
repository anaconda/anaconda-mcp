"""MCP server that echoes back the Authorization header it receives.

Used to prove that anaconda-mcp can forward the user's Anaconda token
to a remote proxied MCP server without any manual configuration.

The server uses ASGI middleware to capture the Authorization header from
incoming requests and makes it available to tool handlers via a ContextVar.
"""

from contextvars import ContextVar

import anyio
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

# ContextVar to pass the Authorization header into tool handlers
_current_auth_header: ContextVar[str] = ContextVar("_current_auth_header", default="")

mcp = FastMCP("auth_echo", stateless_http=True)


@mcp.tool()
def echo_auth_token() -> str:
    """Returns the Authorization header received by this server.

    If anaconda-mcp is correctly forwarding the token, this will return
    something like: "Bearer ana-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    """
    value = _current_auth_header.get()
    if not value:
        return "No Authorization header received"
    return value


class CaptureAuthMiddleware:
    """ASGI middleware that captures the Authorization header into a ContextVar.

    This runs before the MCP streamable-http handler processes the request,
    making the header value available to tool handlers via _current_auth_header.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            # Extract Authorization header from ASGI scope
            headers = dict(scope.get("headers", []))
            auth_value = headers.get(b"authorization", b"").decode()
            token = _current_auth_header.set(auth_value)
            try:
                await self.app(scope, receive, send)
            finally:
                _current_auth_header.reset(token)
        else:
            await self.app(scope, receive, send)


if __name__ == "__main__":
    # Get the Starlette app from FastMCP and wrap with auth-capture middleware
    app = mcp.streamable_http_app()
    wrapped = CaptureAuthMiddleware(app)

    config = uvicorn.Config(wrapped, host="0.0.0.0", port=9999, log_level="info")
    server = uvicorn.Server(config)
    anyio.run(server.serve)

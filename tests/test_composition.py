"""Task 3: build_composed_server() composition tests. Offline — search proxy stubbed."""

import httpx
from fastmcp import Client, FastMCP
from mcp.types import ToolAnnotations

from anaconda_mcp import composition
from anaconda_mcp.composition import PlatformMiddleware, build_composed_server


async def test_build_composed_server_mounts_conda_prefixed_with_annotations(monkeypatch):
    monkeypatch.setattr(composition, "get_auth_token", lambda: "tok")
    # Avoid real network for the remote search proxy: stub create_proxy with an empty server.
    monkeypatch.setattr(composition, "create_proxy", lambda client: FastMCP("search-stub"))

    server = build_composed_server()
    tools = {t.name: t for t in await server.list_tools()}

    # conda tools mounted in-process under the conda_ namespace
    assert "conda_list_environments" in tools
    assert "conda_create_environment" in tools
    assert "conda_install_packages" in tools
    assert "conda_list_environment_packages" in tools

    # destructiveHint survives the mount (the annotation bug is fixed at the root)
    assert tools["conda_remove_environment"].annotations.destructiveHint is True
    assert tools["conda_remove_packages"].annotations.destructiveHint is True

    # exactly one PlatformMiddleware attached to the parent
    assert sum(isinstance(m, PlatformMiddleware) for m in server.middleware) == 1


async def test_mount_preserves_tool_annotations_regression():
    """Framework guard: fastmcp mount() must preserve MCP tool annotations.

    Upstream fastmcp has no mount-path annotation test; this pins the behavior our
    native composition relies on (destructiveHint surviving mount) so a fastmcp
    upgrade cannot silently drop it. Independent of conda_mcp_lite.
    """
    child = FastMCP("child")

    @child.tool(annotations=ToolAnnotations(destructiveHint=True))
    async def danger() -> str:
        return "ok"

    parent = FastMCP("parent")
    parent.mount(child, namespace="child")

    tools = {t.name: t for t in await parent.list_tools()}
    assert "child_danger" in tools
    assert tools["child_danger"].annotations is not None
    assert tools["child_danger"].annotations.destructiveHint is True


def _authenticated_request(auth: httpx.Auth) -> httpx.Request:
    flow = auth.auth_flow(httpx.Request("POST", "https://x"))
    return next(flow)


def test_dynamic_bearer_auth_reads_current_token_per_request(monkeypatch):
    tokens = iter(["first-token", "second-token", None])
    monkeypatch.setattr(composition, "get_auth_token", lambda: next(tokens))

    auth = composition._DynamicBearerAuth()

    assert _authenticated_request(auth).headers["Authorization"] == "Bearer first-token"
    assert _authenticated_request(auth).headers["Authorization"] == "Bearer second-token"
    assert "Authorization" not in _authenticated_request(auth).headers


def test_build_composed_server_uses_dynamic_search_auth(monkeypatch):
    captured: dict[str, object] = {}

    class _Transport:
        def __init__(self, url: str, auth: httpx.Auth) -> None:
            captured["url"] = url
            captured["auth"] = auth

    class _Client:
        def __init__(self, transport: _Transport, timeout: int, init_timeout: int) -> None:
            captured["transport"] = transport
            captured["timeout"] = timeout
            captured["init_timeout"] = init_timeout

    monkeypatch.setattr(composition, "StreamableHttpTransport", _Transport)
    monkeypatch.setattr(composition, "Client", _Client)
    monkeypatch.setattr(composition, "create_proxy", lambda client: FastMCP("search-stub"))

    build_composed_server()

    assert isinstance(captured["auth"], httpx.Auth)
    assert not isinstance(captured["auth"], str)
    assert captured["timeout"] == composition.SEARCH_READ_TIMEOUT_SECONDS
    assert captured["init_timeout"] == composition.SEARCH_CONNECT_TIMEOUT_SECONDS


async def test_middleware_enforces_auth_on_proxied_search_tool(monkeypatch):
    """Regression: the parent PlatformMiddleware must fire for tools served by the PROXIED
    search sub-server, not only the mounted conda tools. Locks behavior a fastmcp upgrade
    (middleware-ordering change) could otherwise silently break."""
    auth_checks: list[str] = []

    def _unauthenticated() -> None:
        auth_checks.append("checked")
        return None

    monkeypatch.setattr(composition, "get_auth_token", _unauthenticated)

    search_stub = FastMCP("search-stub")

    @search_stub.tool
    async def ping() -> str:
        return "pong"

    monkeypatch.setattr(composition, "create_proxy", lambda client: search_stub)

    server = build_composed_server()
    call_succeeded = False
    async with Client(server) as client:
        try:
            await client.call_tool("search_ping", {})
            call_succeeded = True
        except Exception:
            call_succeeded = False

    assert not call_succeeded, "proxied tool ran without auth — middleware did not gate it"
    assert auth_checks, "PlatformMiddleware did not fire for the proxied search tool"

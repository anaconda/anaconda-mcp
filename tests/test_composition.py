"""Task 3: build_composed_server() composition tests. Offline — search proxy stubbed."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from anaconda_mcp import composition
from anaconda_mcp.composition import PlatformMiddleware, build_composed_server


async def test_build_composed_server_mounts_conda_prefixed_with_annotations(monkeypatch):
    monkeypatch.setattr(composition, "get_auth_token", lambda: "tok")
    monkeypatch.setattr(composition, "client_token", lambda: None)
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

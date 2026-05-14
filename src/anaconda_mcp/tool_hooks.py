from collections.abc import Callable


def patch_tool_call_hooks(hooks: list[Callable]) -> None:
    """Apply middleware hooks to FastMCPToolManager.call_tool in a single patch.

    Each hook wraps the next, forming a chain: hooks[0](hooks[1](...(original))).
    A hook is a function (original_call_tool) -> wrapped_call_tool.
    """
    from mcp.server.fastmcp.tools import ToolManager as FastMCPToolManager

    original = FastMCPToolManager.call_tool
    for hook in reversed(hooks):
        original = hook(original)
    FastMCPToolManager.call_tool = original

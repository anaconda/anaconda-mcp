"""Vendored conda MCP server (stdio entry point).

Source: Anaconda-Sandbox/conda-mcp-lite (commit ba79965), BSD-3-Clause.
"""

from . import server as _server
from .server import find_conda_exe, get_conda_info, mcp


def main() -> None:
    _server._conda_exe = find_conda_exe()
    _server._conda_info = get_conda_info()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

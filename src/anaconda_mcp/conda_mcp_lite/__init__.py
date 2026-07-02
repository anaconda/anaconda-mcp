from .server import mcp, find_conda_exe, get_conda_info, _conda_exe, _conda_info
import conda_mcp_lite.server as _server


def main():
    _server._conda_exe = find_conda_exe()
    _server._conda_info = get_conda_info()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

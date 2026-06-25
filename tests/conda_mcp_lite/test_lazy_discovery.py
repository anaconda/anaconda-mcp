"""Task 1 regression: tools must work when the server is mounted in-process
(Option 4a) without ``__init__.main()`` having initialized the discovery globals."""

import pytest

from anaconda_mcp.conda_mcp_lite import server as s


def _conda_available() -> bool:
    try:
        return s.find_conda_exe() is not None
    except Exception:
        return False


@pytest.mark.skipif(not _conda_available(), reason="conda required")
async def test_tools_work_without_main_called():
    # Simulate in-process mount: globals never initialized by main()
    s._conda_exe = None
    s._conda_info = None
    result = await s.mcp.call_tool("list_environments", {})
    envelope = result.structured_content
    assert envelope["is_error"] is False
    assert s._conda_exe is not None  # lazily populated by the tool call

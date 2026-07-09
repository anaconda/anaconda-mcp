import os
import subprocess

import pytest

from anaconda_mcp.conda_mcp_lite.server import find_conda_exe

pytestmark = pytest.mark.integration


def test_find_conda_exe() -> None:
    """find_conda_exe resolves a real, working conda executable."""
    result = find_conda_exe()

    assert result is not None
    assert result.is_file(), f"conda executable not found at {result}"
    assert result.stem.lower() == "conda", f"unexpected executable name: {result.name}"
    assert os.access(result, os.X_OK), f"conda executable is not executable: {result}"

    proc = subprocess.run(
        [str(result), "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, f"conda --version failed: {proc.stderr}"
    assert "conda" in proc.stdout.lower() or "conda" in proc.stderr.lower()

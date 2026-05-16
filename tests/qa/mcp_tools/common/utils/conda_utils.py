"""
Conda environment utilities for the http_tools test suite.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess


def _get_conda_exe() -> str:
    """
    Return the path to the conda executable for cross-platform subprocess calls.

    Why this is needed:
    - On Windows, subprocess.run(["conda", ...]) fails with FileNotFoundError
      because the shell isn't used to resolve "conda" to "conda.bat"
    - Using shell=True is a security risk and changes quoting behavior
    - The reliable fix is to pass the full path to the conda executable

    Resolution order (all platforms):
    1. CONDA_EXE env var — set automatically by:
       - setup-miniconda GitHub Action
       - conda activate (conda sets this in every activated environment)
       - conda init (adds to shell profile)
    2. shutil.which("conda") — standard PATH lookup, works on Linux/macOS
    3. Bare "conda" — fallback that works on Linux/macOS but fails on Windows

    Platform behavior:
    - Linux/macOS: All three options typically work; CONDA_EXE is preferred
      for consistency but which("conda") and bare "conda" work fine
    - Windows: Only CONDA_EXE reliably works; which() may return conda.bat
      but subprocess needs the full path to work without shell=True

    Returns:
        Full path to conda executable, or "conda" as last resort
    """
    conda_exe = os.environ.get("CONDA_EXE")
    if conda_exe and os.path.isfile(conda_exe):
        return conda_exe
    which_conda = shutil.which("conda")
    if which_conda:
        return which_conda
    return "conda"


def _conda_env_prefix(env_name: str) -> str:
    """
    Return the absolute prefix path for a named conda environment.

    Uses `conda info --json` to resolve the name. Asserts that the
    environment exists so callers get an informative failure immediately
    rather than a cryptic downstream error.

    Works on both Windows (backslash) and Unix (forward slash) paths.

    Note: anaconda-anon-usage may print error text to stdout before the JSON
    (e.g., "Error loading anaconda-anon-usage: ..."). We filter this by
    finding the first line starting with '{'.
    """
    conda_exe = _get_conda_exe()
    raw_output = subprocess.check_output([conda_exe, "info", "--json"], text=True)
    # Filter out non-JSON lines (e.g., anaconda-anon-usage errors)
    json_start = raw_output.find("{")
    if json_start == -1:
        raise ValueError(f"No JSON found in conda info output: {raw_output[:200]!r}")
    json_output = raw_output[json_start:]
    info = json.loads(json_output)
    # Match using os.sep to handle both Windows (\) and Unix (/) paths
    matches = [p for p in info["envs"] if p.endswith(f"{os.sep}{env_name}")]
    assert matches, f"Conda environment '{env_name}' not found"
    return str(matches[0])


def _get_env_python_exe(env_name: str) -> str:
    """
    Return the path to the Python executable in a named conda environment.

    This matches how real IDE integrations launch anaconda-mcp: directly via
    the Python executable, not through `conda run`. Using direct Python avoids
    stdin/stdout forwarding issues that occur with `conda run` on Windows.

    Platform paths:
    - Windows: <prefix>/python.exe
    - Unix: <prefix>/bin/python
    """
    prefix = _conda_env_prefix(env_name)
    if os.name == "nt":
        python_exe = os.path.join(prefix, "python.exe")
    else:
        python_exe = os.path.join(prefix, "bin", "python")
    if not os.path.isfile(python_exe):
        raise FileNotFoundError(f"Python executable not found at {python_exe}")
    return python_exe

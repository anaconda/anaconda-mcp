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
    Return the path to the conda executable.

    Resolution order:
    1. CONDA_EXE environment variable (set by setup-miniconda and conda activation)
    2. shutil.which("conda") for PATH lookup
    3. Falls back to "conda" and lets subprocess raise the error

    This is necessary on Windows where bare "conda" doesn't work in subprocess
    without shell=True.
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

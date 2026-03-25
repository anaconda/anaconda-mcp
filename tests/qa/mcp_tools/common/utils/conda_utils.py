"""
Conda environment utilities for the http_tools test suite.
"""

from __future__ import annotations

import json
import os
import subprocess


def _conda_env_prefix(env_name: str) -> str:
    """
    Return the absolute prefix path for a named conda environment.

    Uses `conda info --json` to resolve the name. Asserts that the
    environment exists so callers get an informative failure immediately
    rather than a cryptic downstream error.

    Works on both Windows (backslash) and Unix (forward slash) paths.
    """
    info = json.loads(subprocess.check_output(["conda", "info", "--json"], text=True))
    # Match using os.sep to handle both Windows (\) and Unix (/) paths
    matches = [p for p in info["envs"] if p.endswith(f"{os.sep}{env_name}")]
    assert matches, f"Conda environment '{env_name}' not found"
    return str(matches[0])

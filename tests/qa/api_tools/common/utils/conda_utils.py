"""
Conda environment utilities for the api_tools test suite.
"""

from __future__ import annotations

import json
import subprocess


def _conda_env_prefix(env_name: str) -> str:
    """
    Return the absolute prefix path for a named conda environment.

    Uses `conda info --json` to resolve the name. Asserts that the
    environment exists so callers get an informative failure immediately
    rather than a cryptic downstream error.
    """
    info = json.loads(
        subprocess.check_output(["conda", "info", "--json"], text=True)
    )
    matches = [p for p in info["envs"] if p.endswith(f"/{env_name}")]
    assert matches, f"Conda environment '{env_name}' not found"
    return matches[0]

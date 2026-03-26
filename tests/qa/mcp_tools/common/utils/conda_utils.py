"""
Conda environment utilities for the http_tools test suite.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def conda_executable() -> str:
    """
    Return a filesystem path to use as ``argv[0]`` for conda subprocess calls.

    On Windows, ``subprocess.run([\"conda\", ...])`` commonly fails with WinError 2
    because ``CreateProcess`` does not resolve ``conda`` / ``conda.bat`` like a
    shell. Prefer ``CONDA_EXE`` or ``CONDA\\\\Scripts\\\\conda.exe``.
    """
    exe = os.environ.get("CONDA_EXE")
    if exe:
        p = Path(exe)
        if p.is_file():
            return str(p.resolve())

    base = os.environ.get("CONDA", "")
    if base:
        win_exe = Path(base) / "Scripts" / "conda.exe"
        if win_exe.is_file():
            return str(win_exe.resolve())
        unix_bin = Path(base) / "bin" / "conda"
        if unix_bin.is_file():
            return str(unix_bin.resolve())

    for name in ("conda.exe", "conda"):
        w = shutil.which(name)
        if w:
            return w

    return "conda"


def _conda_env_prefix(env_name: str) -> str:
    """
    Return the absolute prefix path for a named conda environment.

    Uses `conda info --json` to resolve the name. Asserts that the
    environment exists so callers get an informative failure immediately
    rather than a cryptic downstream error.

    Works on both Windows (backslash) and Unix (forward slash) paths.
    """
    ce = conda_executable()
    info = json.loads(subprocess.check_output([ce, "info", "--json"], text=True))
    # Match using os.sep to handle both Windows (\) and Unix (/) paths
    matches = [p for p in info["envs"] if p.endswith(f"{os.sep}{env_name}")]
    assert matches, f"Conda environment '{env_name}' not found"
    return str(matches[0])

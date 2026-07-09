"""
Unit tests for find_conda_exe priority chain, _probe_conda_from_shell,
and Windows vs non-Windows platform branching.

All tests are fully hermetic — no real conda installation needed.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from anaconda_mcp.conda_mcp_lite.server import _probe_conda_from_shell, find_conda_exe

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SERVER = "anaconda_mcp.conda_mcp_lite.server"


@pytest.fixture(autouse=True)
def clear_conda_env_vars(monkeypatch):
    """Remove CONDA_EXE and _CONDA_ROOT for every test so env vars don't leak."""
    monkeypatch.delenv("CONDA_EXE", raising=False)
    monkeypatch.delenv("_CONDA_ROOT", raising=False)


@pytest.fixture()
def no_conda_on_path():
    with patch(f"{SERVER}.shutil.which", return_value=None):
        yield


@pytest.fixture()
def windows(no_conda_on_path):
    with (
        patch(f"{SERVER}.platform.system", return_value="Windows"),
        patch(f"{SERVER}._find_conda_from_registry_autorun", return_value=None),
        patch(f"{SERVER}._find_conda_from_registry_uninstall", return_value=None),
    ):
        yield


@pytest.fixture()
def linux(no_conda_on_path):
    with (
        patch(f"{SERVER}.platform.system", return_value="Linux"),
        patch(f"{SERVER}._probe_conda_from_shell", return_value=None),
    ):
        yield


@pytest.fixture()
def fake_conda(tmp_path):
    exe = tmp_path / "conda.exe"
    exe.touch()
    return exe


# ---------------------------------------------------------------------------
# find_conda_exe — priority chain
# ---------------------------------------------------------------------------


def test_step1_conda_exe_env_var(monkeypatch, fake_conda):
    """CONDA_EXE env var pointing to a real file wins immediately."""
    monkeypatch.setenv("CONDA_EXE", str(fake_conda))
    assert find_conda_exe() == fake_conda


def test_step1_skipped_when_conda_exe_file_missing(monkeypatch, fake_conda):
    """CONDA_EXE pointing to a nonexistent file is ignored; falls through to PATH."""
    monkeypatch.setenv("CONDA_EXE", str(fake_conda.parent / "missing.exe"))
    with patch(f"{SERVER}.shutil.which", return_value=str(fake_conda)):
        assert find_conda_exe() == fake_conda


def test_step2_conda_root_env_var(monkeypatch, tmp_path):
    """_CONDA_ROOT/bin/conda is used when CONDA_EXE is absent."""
    conda = tmp_path / "bin" / "conda"
    conda.parent.mkdir()
    conda.touch()
    monkeypatch.setenv("_CONDA_ROOT", str(tmp_path))
    with patch(f"{SERVER}.shutil.which", return_value=None):
        assert find_conda_exe() == conda


def test_step3_shutil_which(fake_conda, windows):
    """shutil.which result is used when env vars are absent."""
    with patch(f"{SERVER}.shutil.which", return_value=str(fake_conda)):
        assert find_conda_exe() == fake_conda


def test_step4b_registry_autorun(fake_conda, no_conda_on_path):
    """On Windows, registry AutoRun result is used."""
    with (
        patch(f"{SERVER}.platform.system", return_value="Windows"),
        patch(f"{SERVER}._find_conda_from_registry_autorun", return_value=str(fake_conda)),
        patch(f"{SERVER}._find_conda_from_registry_uninstall", return_value=None),
    ):
        assert find_conda_exe() == fake_conda


def test_step5_registry_uninstall(fake_conda, no_conda_on_path):
    """On Windows, registry Uninstall is used when AutoRun returns None."""
    with (
        patch(f"{SERVER}.platform.system", return_value="Windows"),
        patch(f"{SERVER}._find_conda_from_registry_autorun", return_value=None),
        patch(f"{SERVER}._find_conda_from_registry_uninstall", return_value=str(fake_conda)),
    ):
        assert find_conda_exe() == fake_conda


def test_raises_when_all_strategies_fail(windows):
    """RuntimeError with actionable message when no strategy succeeds."""
    with pytest.raises(RuntimeError, match="CONDA_EXE"):
        find_conda_exe()


# ---------------------------------------------------------------------------
# find_conda_exe — platform branching
# ---------------------------------------------------------------------------


def test_windows_does_not_call_shell_probe(fake_conda, no_conda_on_path):
    """On Windows, shell probe is never called."""
    shell_probe = MagicMock(return_value=None)
    with (
        patch(f"{SERVER}.platform.system", return_value="Windows"),
        patch(f"{SERVER}._find_conda_from_registry_autorun", return_value=str(fake_conda)),
        patch(f"{SERVER}._find_conda_from_registry_uninstall", return_value=None),
        patch(f"{SERVER}._probe_conda_from_shell", shell_probe),
    ):
        find_conda_exe()
    shell_probe.assert_not_called()


def test_non_windows_does_not_call_registry(fake_conda, no_conda_on_path):
    """On non-Windows, registry functions are never called."""
    autorun = MagicMock(return_value=None)
    uninstall = MagicMock(return_value=None)
    with (
        patch(f"{SERVER}.platform.system", return_value="Linux"),
        patch(f"{SERVER}._probe_conda_from_shell", return_value=str(fake_conda)),
        patch(f"{SERVER}._find_conda_from_registry_autorun", autorun),
        patch(f"{SERVER}._find_conda_from_registry_uninstall", uninstall),
    ):
        find_conda_exe()
    autorun.assert_not_called()
    uninstall.assert_not_called()


def test_windows_autorun_before_uninstall(fake_conda, no_conda_on_path):
    """On Windows, Uninstall is not called when AutoRun already succeeds."""
    uninstall = MagicMock(return_value=None)
    with (
        patch(f"{SERVER}.platform.system", return_value="Windows"),
        patch(f"{SERVER}._find_conda_from_registry_autorun", return_value=str(fake_conda)),
        patch(f"{SERVER}._find_conda_from_registry_uninstall", uninstall),
    ):
        find_conda_exe()
    uninstall.assert_not_called()


# ---------------------------------------------------------------------------
# _probe_conda_from_shell (Unix)
# ---------------------------------------------------------------------------


def test_shell_probe_returns_none_when_shell_env_absent(monkeypatch):
    """No SHELL env var → returns None without spawning a process."""
    monkeypatch.delenv("SHELL", raising=False)
    run_mock = MagicMock()
    with patch(f"{SERVER}.subprocess.run", run_mock):
        assert _probe_conda_from_shell() is None
    run_mock.assert_not_called()


def test_shell_probe_extracts_path_from_output(monkeypatch, tmp_path):
    """Correctly extracts the conda path from marker-delimited shell output."""
    conda = tmp_path / "conda"
    conda.touch()
    monkeypatch.setenv("SHELL", "/bin/bash")

    def fake_run(args, **kwargs):
        # Pull the marker out of the echo command and wrap the path with it
        import re

        mark = re.search(r'echo "(\w+)', args[-1]).group(1)
        result = MagicMock()
        result.stdout = f"shell noise\n{mark}{conda}{mark}\nmore noise"
        return result

    with patch(f"{SERVER}.subprocess.run", side_effect=fake_run):
        assert _probe_conda_from_shell() == str(conda)


def test_shell_probe_returns_none_when_path_missing(monkeypatch, tmp_path):
    """Marker found but path doesn't exist on disk → returns None."""
    monkeypatch.setenv("SHELL", "/bin/bash")

    def fake_run(args, **kwargs):
        import re

        mark = re.search(r'echo "(\w+)', args[-1]).group(1)
        result = MagicMock()
        result.stdout = f"{mark}{tmp_path / 'missing' / 'conda'}{mark}"
        return result

    with patch(f"{SERVER}.subprocess.run", side_effect=fake_run):
        assert _probe_conda_from_shell() is None


def test_shell_probe_returns_none_on_timeout(monkeypatch):
    """TimeoutExpired is caught and returns None."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    with patch(
        f"{SERVER}.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="bash", timeout=5),
    ):
        assert _probe_conda_from_shell() is None


def test_shell_probe_returns_none_on_oserror(monkeypatch):
    """OSError is caught and returns None."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    with patch(f"{SERVER}.subprocess.run", side_effect=OSError("not found")):
        assert _probe_conda_from_shell() is None


def test_shell_probe_uses_ic_for_csh(monkeypatch):
    """tcsh/csh shells use -ic instead of -i -c."""
    monkeypatch.setenv("SHELL", "/bin/tcsh")
    run_mock = MagicMock(return_value=MagicMock(stdout=""))
    with patch(f"{SERVER}.subprocess.run", run_mock):
        _probe_conda_from_shell()
    args = run_mock.call_args[0][0]
    assert "-ic" in args
    assert "-i" not in [a for a in args if a != "-ic"]


def test_shell_probe_uses_i_c_for_bash(monkeypatch):
    """bash uses -i -c."""
    monkeypatch.setenv("SHELL", "/bin/bash")
    run_mock = MagicMock(return_value=MagicMock(stdout=""))
    with patch(f"{SERVER}.subprocess.run", run_mock):
        _probe_conda_from_shell()
    args = run_mock.call_args[0][0]
    assert "-i" in args and "-c" in args

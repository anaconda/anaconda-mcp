"""
Unit tests for Windows registry conda-discovery helpers.

All tests are fully hermetic: winreg is monkey-patched so no real registry
or conda installation is required. Non-Windows platforms skip the tests that
exercise Windows-only code paths.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from anaconda_mcp.conda_mcp_lite.server import (
    _find_conda_from_registry_autorun,
    _find_conda_from_registry_uninstall,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")


def _make_winreg(keys: dict):
    """
    Build a minimal winreg stub from a nested dict:

        {
            (hive, key_path): {
                "AutoRun": "some value",   # values in this key
                "__subkeys__": ["sub1"],   # optional child key names
            }
        }

    OpenKey accepts either a hive integer or an already-opened key handle as
    its first argument, mirroring real winreg behaviour.
    Raises OSError (FileNotFoundError) when the resolved (hive, path) is absent.
    EnumKey raises OSError when the index is out of range.
    QueryValueEx raises OSError when the value name is absent.
    """
    winreg = MagicMock()
    winreg.HKEY_CURRENT_USER = 0x80000001
    winreg.HKEY_LOCAL_MACHINE = 0x80000002

    def open_key(hive_or_key, path):
        # Resolve the root hive and accumulated path from an already-opened handle.
        if isinstance(hive_or_key, int):
            hive, base_path = hive_or_key, ""
        else:
            # hive_or_key is a previously returned key handle
            hive, base_path = hive_or_key._hive, hive_or_key._path

        full_path = rf"{base_path}\{path}".lstrip("\\") if base_path else path
        lookup = (hive, full_path)
        if lookup not in keys:
            raise FileNotFoundError(f"key not found: {lookup!r}")

        ctx = MagicMock()
        ctx.__enter__ = lambda s: ctx
        ctx.__exit__ = MagicMock(return_value=False)
        ctx._data = keys[lookup]
        ctx._hive = hive
        ctx._path = full_path
        return ctx

    def query_value_ex(key, name):
        data = key._data
        if name not in data:
            raise OSError(f"value not found: {name!r}")
        return (data[name], 1)

    def enum_key(key, index):
        subkeys = key._data.get("__subkeys__", [])
        if index >= len(subkeys):
            raise OSError("no more subkeys")
        return subkeys[index]

    winreg.OpenKey.side_effect = open_key
    winreg.QueryValueEx.side_effect = query_value_ex
    winreg.EnumKey.side_effect = enum_key
    return winreg


# ---------------------------------------------------------------------------
# _find_conda_from_registry_autorun
# ---------------------------------------------------------------------------


class TestFindCondaFromRegistryAutorun:
    def test_returns_none_when_key_does_not_exist(self):
        """Both hives missing the Command Processor key → None, no exception."""
        winreg = _make_winreg({})  # no keys at all
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_autorun()
        assert result is None

    def test_returns_none_when_autorun_value_absent(self):
        """Key exists but has no AutoRun value → None."""
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, r"Software\Microsoft\Command Processor"): {},
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_autorun()
        assert result is None

    def test_returns_none_when_autorun_has_no_conda_bat(self):
        """AutoRun exists but contains no conda-related .bat → None."""
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, r"Software\Microsoft\Command Processor"): {
                    "AutoRun": r"C:\Windows\system32\something.bat",
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_autorun()
        assert result is None

    def test_returns_conda_exe_from_valid_autorun(self, tmp_path):
        """Well-formed AutoRun with a conda hook → correct conda.exe path."""
        # Real layout: <conda_root>\Scripts\conda_hook.bat
        # hook_path.parent.parent == conda_root → Scripts\conda.exe
        scripts = tmp_path / "Scripts"
        scripts.mkdir()
        conda_exe = scripts / "conda.exe"
        conda_exe.touch()
        hook = scripts / "conda_hook.bat"
        hook.touch()

        hive = 0x80000001
        autorun_value = f'"{hook}"'
        winreg = _make_winreg(
            {
                (hive, r"Software\Microsoft\Command Processor"): {
                    "AutoRun": autorun_value,
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_autorun()
        assert result == str(conda_exe)

    def test_returns_none_when_derived_conda_exe_missing(self, tmp_path):
        """Hook path found but conda.exe doesn't exist at derived location → None."""
        scripts = tmp_path / "Scripts"
        scripts.mkdir()
        hook = scripts / "conda_hook.bat"
        hook.touch()
        # Do NOT create Scripts/conda.exe

        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, r"Software\Microsoft\Command Processor"): {
                    "AutoRun": str(hook),
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_autorun()
        assert result is None

    def test_checks_both_hives(self, tmp_path):
        """Falls through to HKLM when HKCU key is absent."""
        scripts = tmp_path / "Scripts"
        scripts.mkdir()
        conda_exe = scripts / "conda.exe"
        conda_exe.touch()
        hook = scripts / "conda_hook.bat"
        hook.touch()

        hklm = 0x80000002
        winreg = _make_winreg(
            {
                (hklm, r"Software\Microsoft\Command Processor"): {
                    "AutoRun": str(hook),
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_autorun()
        assert result == str(conda_exe)

    def test_multi_part_autorun_finds_conda_bat(self, tmp_path):
        """AutoRun with multiple &-separated commands; conda hook is one of them."""
        scripts = tmp_path / "Scripts"
        scripts.mkdir()
        conda_exe = scripts / "conda.exe"
        conda_exe.touch()
        hook = scripts / "conda_hook.bat"
        hook.touch()

        autorun = rf"C:\Windows\something.cmd & {hook} & C:\other\thing.bat"
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, r"Software\Microsoft\Command Processor"): {
                    "AutoRun": autorun,
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_autorun()
        assert result == str(conda_exe)


# ---------------------------------------------------------------------------
# _find_conda_from_registry_uninstall
# ---------------------------------------------------------------------------


class TestFindCondaFromRegistryUninstall:
    UNINSTALL = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"

    def test_returns_none_when_uninstall_key_absent(self):
        """Uninstall key missing entirely → None, no exception."""
        winreg = _make_winreg({})
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_uninstall()
        assert result is None

    def test_returns_none_when_no_conda_subkeys(self, tmp_path):
        """Uninstall key present but no conda/anaconda subkeys → None."""
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, self.UNINSTALL): {
                    "__subkeys__": ["Python 3.11.0", "Git_is1"],
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_uninstall()
        assert result is None

    def test_finds_conda_via_install_location(self, tmp_path):
        """InstallLocation present and conda.exe exists → returns path."""
        scripts = tmp_path / "Scripts"
        scripts.mkdir()
        conda_exe = scripts / "conda.exe"
        conda_exe.touch()

        subkey_name = "Miniconda3"
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, self.UNINSTALL): {
                    "__subkeys__": [subkey_name],
                },
                (hive, rf"{self.UNINSTALL}\{subkey_name}"): {
                    "InstallLocation": str(tmp_path),
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_uninstall()
        assert result == str(conda_exe)

    def test_finds_conda_via_uninstall_string_when_no_install_location(self, tmp_path):
        """No InstallLocation but UninstallString present → derives root from it."""
        scripts = tmp_path / "Scripts"
        scripts.mkdir()
        conda_exe = scripts / "conda.exe"
        conda_exe.touch()
        uninstaller = tmp_path / "Uninstall-Miniconda3.exe"
        uninstaller.touch()

        subkey_name = "Miniconda3 py313_26.1.1-1 (Python 3.13.12 64-bit)"
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, self.UNINSTALL): {
                    "__subkeys__": [subkey_name],
                },
                (hive, rf"{self.UNINSTALL}\{subkey_name}"): {
                    # No InstallLocation — only UninstallString (real Miniconda behaviour)
                    "UninstallString": f'"{uninstaller}"',
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_uninstall()
        assert result == str(conda_exe)

    def test_returns_none_when_neither_value_present(self, tmp_path):
        """Subkey exists but has neither InstallLocation nor UninstallString → None."""
        subkey_name = "Miniconda3"
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, self.UNINSTALL): {
                    "__subkeys__": [subkey_name],
                },
                (hive, rf"{self.UNINSTALL}\{subkey_name}"): {
                    "DisplayName": "Miniconda3",
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_uninstall()
        assert result is None

    def test_returns_none_when_derived_conda_exe_missing(self, tmp_path):
        """InstallLocation found but conda.exe not present at derived path → None."""
        # Scripts dir exists but conda.exe is absent
        (tmp_path / "Scripts").mkdir()

        subkey_name = "Anaconda3"
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, self.UNINSTALL): {
                    "__subkeys__": [subkey_name],
                },
                (hive, rf"{self.UNINSTALL}\{subkey_name}"): {
                    "InstallLocation": str(tmp_path),
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_uninstall()
        assert result is None

    def test_prefers_install_location_over_uninstall_string(self, tmp_path):
        """When both values are present, InstallLocation is used first."""
        # Two different roots — InstallLocation should win
        root_a = tmp_path / "conda_a"
        root_b = tmp_path / "conda_b"
        for root in (root_a, root_b):
            (root / "Scripts").mkdir(parents=True)
            (root / "Scripts" / "conda.exe").touch()
        uninstaller = root_b / "Uninstall.exe"
        uninstaller.touch()

        subkey_name = "Miniconda3"
        hive = 0x80000001
        winreg = _make_winreg(
            {
                (hive, self.UNINSTALL): {
                    "__subkeys__": [subkey_name],
                },
                (hive, rf"{self.UNINSTALL}\{subkey_name}"): {
                    "InstallLocation": str(root_a),
                    "UninstallString": f'"{uninstaller}"',
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_uninstall()
        assert result == str(root_a / "Scripts" / "conda.exe")

    def test_checks_both_hives(self, tmp_path):
        """Falls through to HKLM when HKCU has no matching subkey."""
        scripts = tmp_path / "Scripts"
        scripts.mkdir()
        conda_exe = scripts / "conda.exe"
        conda_exe.touch()

        subkey_name = "Anaconda3"
        hkcu = 0x80000001
        hklm = 0x80000002
        winreg = _make_winreg(
            {
                (hkcu, self.UNINSTALL): {"__subkeys__": []},
                (hklm, self.UNINSTALL): {"__subkeys__": [subkey_name]},
                (hklm, rf"{self.UNINSTALL}\{subkey_name}"): {
                    "InstallLocation": str(tmp_path),
                },
            }
        )
        with patch.dict("sys.modules", {"winreg": winreg}):
            result = _find_conda_from_registry_uninstall()
        assert result == str(conda_exe)

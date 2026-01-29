"""
Unit tests for Claude Desktop configuration functionality.

These tests verify that the Claude Desktop configuration works correctly
across Linux, macOS, and Windows platforms.
"""

import json
import os
import platform
import sys
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from anaconda_mcp.claude_desktop import (
    backup_config_file,
    build_stdio_config,
    build_streamable_http_config,
    configure_claude_desktop,
    get_anaconda_mcp_config_dir,
    get_claude_desktop_config_path,
    load_config,
    remove_claude_desktop_config,
    save_config,
    show_claude_desktop_config,
)
from anaconda_mcp.cli import cli


class TestGetClaudeDesktopConfigPath:
    """Tests for get_claude_desktop_config_path function."""

    def test_linux_path(self):
        """Test config path on Linux."""
        with mock.patch("platform.system", return_value="Linux"):
            with mock.patch.object(Path, "home", return_value=Path("/home/testuser")):
                path = get_claude_desktop_config_path()
                assert path == Path("/home/testuser/.config/Claude/claude_desktop_config.json")

    def test_macos_path(self):
        """Test config path on macOS."""
        with mock.patch("platform.system", return_value="Darwin"):
            with mock.patch.object(Path, "home", return_value=Path("/Users/testuser")):
                path = get_claude_desktop_config_path()
                assert path == Path(
                    "/Users/testuser/Library/Application Support/Claude/claude_desktop_config.json"
                )

    def test_windows_path_with_appdata(self):
        """Test config path on Windows with APPDATA environment variable."""
        with mock.patch("platform.system", return_value="Windows"):
            with mock.patch.dict(os.environ, {"APPDATA": "C:\\Users\\testuser\\AppData\\Roaming"}):
                path = get_claude_desktop_config_path()
                # Compare path parts to be platform-independent
                assert path.name == "claude_desktop_config.json"
                assert "Claude" in path.parts
                # Check the APPDATA prefix is used (normalize separators for comparison)
                path_str = str(path).replace("\\", "/")
                assert "C:/Users/testuser/AppData/Roaming" in path_str or "C:\\Users\\testuser\\AppData\\Roaming" in str(path)

    def test_windows_path_without_appdata(self):
        """Test config path on Windows without APPDATA environment variable."""
        with mock.patch("platform.system", return_value="Windows"):
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch.object(Path, "home", return_value=Path("C:\\Users\\testuser")):
                    # Remove APPDATA from environment
                    env_backup = os.environ.get("APPDATA")
                    if "APPDATA" in os.environ:
                        del os.environ["APPDATA"]
                    try:
                        path = get_claude_desktop_config_path()
                        # Compare path parts to be platform-independent
                        assert path.name == "claude_desktop_config.json"
                        assert "Claude" in path.parts
                        # Check the home-based path structure
                        path_str = str(path).replace("\\", "/")
                        assert "AppData/Roaming" in path_str or "AppData\\Roaming" in str(path)
                    finally:
                        if env_backup:
                            os.environ["APPDATA"] = env_backup

    def test_unsupported_os(self):
        """Test that unsupported OS raises RuntimeError."""
        with mock.patch("platform.system", return_value="FreeBSD"):
            with pytest.raises(RuntimeError, match="Unsupported operating system"):
                get_claude_desktop_config_path()

    def test_current_os_path(self):
        """Test that the function works on the current OS without mocking."""
        # This test runs on the actual OS to ensure real-world compatibility
        try:
            path = get_claude_desktop_config_path()
            assert path is not None
            assert path.name == "claude_desktop_config.json"
            assert "Claude" in str(path)
        except RuntimeError:
            # Skip if running on unsupported OS
            pytest.skip("Unsupported OS for this test")


class TestGetAnacondaMcpConfigDir:
    """Tests for get_anaconda_mcp_config_dir function."""

    def test_returns_package_directory(self):
        """Test that it returns the anaconda_mcp package installation directory."""
        config_dir = get_anaconda_mcp_config_dir()
        # Should return the directory where anaconda_mcp is installed
        # This will be something like .../site-packages/anaconda_mcp/
        assert config_dir.exists()
        assert config_dir.name == "anaconda_mcp"
        # Verify it's the directory containing the module files
        assert (config_dir / "__init__.py").exists()
        assert (config_dir / "claude_desktop.py").exists()


class TestBackupConfigFile:
    """Tests for backup_config_file function."""

    def test_backup_existing_file(self, tmp_path):
        """Test backing up an existing config file."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "data"}')

        backup_path = backup_config_file(config_file)

        assert backup_path is not None
        assert backup_path.exists()
        assert ".backup.json" in backup_path.name
        assert backup_path.read_text() == '{"test": "data"}'

    def test_backup_nonexistent_file(self, tmp_path):
        """Test backing up a non-existent file returns None."""
        config_file = tmp_path / "nonexistent.json"

        backup_path = backup_config_file(config_file)

        assert backup_path is None


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_existing_config(self, tmp_path):
        """Test loading an existing config file."""
        config_file = tmp_path / "config.json"
        config_data = {"mcpServers": {"test": {"command": "test"}}}
        config_file.write_text(json.dumps(config_data))

        loaded = load_config(config_file)

        assert loaded == config_data

    def test_load_nonexistent_config(self, tmp_path):
        """Test loading a non-existent config file returns empty dict."""
        config_file = tmp_path / "nonexistent.json"

        loaded = load_config(config_file)

        assert loaded == {}

    def test_load_corrupted_config(self, tmp_path):
        """Test loading a corrupted config file returns empty dict."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        loaded = load_config(config_file)

        assert loaded == {}


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_file(self, tmp_path):
        """Test saving config creates the file."""
        config_file = tmp_path / "config.json"
        config_data = {"mcpServers": {"test": {"command": "test"}}}

        save_config(config_file, config_data)

        assert config_file.exists()
        loaded = json.loads(config_file.read_text())
        assert loaded == config_data

    def test_save_config_creates_parent_dirs(self, tmp_path):
        """Test saving config creates parent directories."""
        config_file = tmp_path / "subdir" / "another" / "config.json"
        config_data = {"test": "data"}

        save_config(config_file, config_data)

        assert config_file.exists()


class TestBuildStdioConfig:
    """Tests for build_stdio_config function."""

    def test_builds_correct_structure(self):
        """Test that STDIO config has correct structure."""
        config = build_stdio_config()

        assert "command" in config
        assert "args" in config
        assert "env" in config
        assert "-m" in config["args"]
        assert "anaconda_mcp" in config["args"]
        assert "serve" in config["args"]
        assert config["args"] == ["-m", "anaconda_mcp", "serve"]
        assert "ANACONDA_MCP_PYTHON_EXECUTABLE" in config["env"]
        assert "MCP_COMPOSE_CONFIG_DIR" in config["env"]

    def test_env_vars_point_to_package_directory(self):
        """Test that environment variables point to package directory."""
        config = build_stdio_config()

        # Check MCP_COMPOSE_CONFIG_DIR points to package directory
        config_dir = Path(config["env"]["MCP_COMPOSE_CONFIG_DIR"])
        assert config_dir.name == "anaconda_mcp"
        assert (config_dir / "__init__.py").exists()
        
        # Check ANACONDA_MCP_PYTHON_EXECUTABLE is set to current Python
        python_exe = config["env"]["ANACONDA_MCP_PYTHON_EXECUTABLE"]
        assert python_exe == sys.executable


class TestBuildStreamableHttpConfig:
    """Tests for build_streamable_http_config function."""

    def test_builds_correct_structure(self):
        """Test that Streamable HTTP config has correct structure."""
        config = build_streamable_http_config()

        assert "url" in config
        assert "transport" in config
        assert config["transport"] == "streamable-http"
        assert "http://localhost:8888/mcp" == config["url"]

    def test_custom_host_and_port(self):
        """Test custom host and port."""
        config = build_streamable_http_config(host="192.168.1.1", port=9000)

        assert config["url"] == "http://192.168.1.1:9000/mcp"


class TestConfigureClaudeDesktop:
    """Tests for configure_claude_desktop function."""

    def test_creates_new_config(self, tmp_path):
        """Test creating a new config file."""
        config_file = tmp_path / "config.json"

        result = configure_claude_desktop(
            config_path=config_file,
            server_name="test-server",
            transport="stdio",
            backup=False,
        )

        assert result["created"] is True
        assert result["updated"] is False
        assert config_file.exists()

        config = json.loads(config_file.read_text())
        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]

    def test_adds_to_existing_config(self, tmp_path):
        """Test adding to an existing config file."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"existing": {}}}')

        result = configure_claude_desktop(
            config_path=config_file,
            server_name="test-server",
            transport="stdio",
            backup=False,
        )

        assert result["created"] is False
        config = json.loads(config_file.read_text())
        assert "existing" in config["mcpServers"]
        assert "test-server" in config["mcpServers"]

    def test_fails_if_server_exists_without_force(self, tmp_path):
        """Test that adding an existing server fails without --force."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"test-server": {}}}')

        with pytest.raises(FileExistsError, match="already exists"):
            configure_claude_desktop(
                config_path=config_file,
                server_name="test-server",
                transport="stdio",
                backup=False,
            )

    def test_overwrites_with_force(self, tmp_path):
        """Test that --force overwrites existing server."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"test-server": {"old": "config"}}}')

        result = configure_claude_desktop(
            config_path=config_file,
            server_name="test-server",
            transport="stdio",
            backup=False,
            force=True,
        )

        assert result["updated"] is True
        config = json.loads(config_file.read_text())
        assert "old" not in config["mcpServers"]["test-server"]

    def test_creates_backup(self, tmp_path):
        """Test that backup is created."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"original": "data"}')

        result = configure_claude_desktop(
            config_path=config_file,
            server_name="test-server",
            transport="stdio",
            backup=True,
        )

        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()

    def test_invalid_transport_raises_error(self, tmp_path):
        """Test that invalid transport raises ValueError."""
        config_file = tmp_path / "config.json"

        with pytest.raises(ValueError, match="Invalid transport"):
            configure_claude_desktop(
                config_path=config_file,
                transport="invalid",
            )


class TestRemoveClaudeDesktopConfig:
    """Tests for remove_claude_desktop_config function."""

    def test_removes_server(self, tmp_path):
        """Test removing a server from config."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"test-server": {}, "other": {}}}')

        result = remove_claude_desktop_config(
            config_path=config_file,
            server_name="test-server",
            backup=False,
        )

        assert result["removed"] is True
        config = json.loads(config_file.read_text())
        assert "test-server" not in config["mcpServers"]
        assert "other" in config["mcpServers"]

    def test_fails_if_config_not_found(self, tmp_path):
        """Test that removing from non-existent config fails."""
        config_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            remove_claude_desktop_config(config_path=config_file)

    def test_fails_if_server_not_found(self, tmp_path):
        """Test that removing non-existent server fails."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {}}')

        with pytest.raises(KeyError, match="not found"):
            remove_claude_desktop_config(
                config_path=config_file,
                server_name="nonexistent",
            )


class TestShowClaudeDesktopConfig:
    """Tests for show_claude_desktop_config function."""

    def test_shows_full_config(self, tmp_path):
        """Test showing full configuration."""
        config_file = tmp_path / "config.json"
        config_data = {"mcpServers": {"test": {}}}
        config_file.write_text(json.dumps(config_data))

        result = show_claude_desktop_config(config_path=config_file)

        assert result["exists"] is True
        assert result["config"] == config_data

    def test_shows_specific_server(self, tmp_path):
        """Test showing specific server configuration."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"test": {"data": "value"}}}')

        result = show_claude_desktop_config(
            config_path=config_file,
            server_name="test",
        )

        assert result["config"] == {"data": "value"}

    def test_shows_nonexistent_file(self, tmp_path):
        """Test showing non-existent config file."""
        config_file = tmp_path / "nonexistent.json"

        result = show_claude_desktop_config(config_path=config_file)

        assert result["exists"] is False
        assert result["config"] is None


class TestCLICommands:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_claude_configure_creates_config(self, runner, tmp_path):
        """Test 'anaconda-mcp claude configure' creates config."""
        config_file = tmp_path / "config.json"

        result = runner.invoke(
            cli,
            ["claude-desktop", "setup-config", "--config", str(config_file), "--no-backup"],
        )

        assert result.exit_code == 0
        assert config_file.exists()
        assert "anaconda-mcp" in config_file.read_text()

    def test_claude_configure_streamable_http(self, runner, tmp_path):
        """Test 'anaconda-mcp claude-desktop setup-config' with Streamable HTTP."""
        config_file = tmp_path / "config.json"

        result = runner.invoke(
            cli,
            [
                "claude-desktop",
                "setup-config",
                "--config",
                str(config_file),
                "--transport",
                "streamable-http",
                "--port",
                "9000",
                "--no-backup",
            ],
        )

        assert result.exit_code == 0
        config = json.loads(config_file.read_text())
        server_config = config["mcpServers"]["anaconda-mcp"]
        assert server_config["transport"] == "streamable-http"
        assert "9000" in server_config["url"]

    def test_claude_configure_fails_without_force(self, runner, tmp_path):
        """Test 'anaconda-mcp claude configure' fails if server exists."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"anaconda-mcp": {}}}')

        result = runner.invoke(
            cli,
            ["claude-desktop", "setup-config", "--config", str(config_file), "--no-backup"],
        )

        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_claude_configure_with_force(self, runner, tmp_path):
        """Test 'anaconda-mcp claude configure --force' overwrites."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"anaconda-mcp": {"old": true}}}')

        result = runner.invoke(
            cli,
            ["claude-desktop", "setup-config", "--config", str(config_file), "--no-backup", "--force"],
        )

        assert result.exit_code == 0
        config = json.loads(config_file.read_text())
        assert "old" not in config["mcpServers"]["anaconda-mcp"]

    def test_claude_uninstall_removes_server(self, runner, tmp_path):
        """Test 'anaconda-mcp claude uninstall' removes server."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"anaconda-mcp": {}}}')

        result = runner.invoke(
            cli,
            ["claude-desktop", "remove-config", "--config", str(config_file), "--no-backup"],
        )

        assert result.exit_code == 0
        config = json.loads(config_file.read_text())
        assert "anaconda-mcp" not in config["mcpServers"]

    def test_claude_show_displays_config(self, runner, tmp_path):
        """Test 'anaconda-mcp claude show' displays config."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"test": {"key": "value"}}}')

        result = runner.invoke(
            cli,
            ["claude-desktop", "show", "--config", str(config_file)],
        )

        assert result.exit_code == 0
        assert "test" in result.output

    def test_claude_show_json_output(self, runner, tmp_path):
        """Test 'anaconda-mcp claude show --json' outputs JSON."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"mcpServers": {"test": {}}}')

        result = runner.invoke(
            cli,
            ["claude-desktop", "show", "--config", str(config_file), "--json"],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["exists"] is True

    def test_claude_path_shows_path(self, runner):
        """Test 'anaconda-mcp claude path' shows default path."""
        result = runner.invoke(cli, ["claude-desktop", "path"])

        # Should succeed on Linux, macOS, Windows
        if result.exit_code == 0:
            assert "claude_desktop_config.json" in result.output
        else:
            # May fail on unsupported OS
            assert "Unsupported" in result.output


class TestOSSpecificPaths:
    """
    OS-specific tests that verify paths are correct for the current platform.

    These tests run without mocking to verify real-world behavior.
    """

    def test_path_is_absolute(self):
        """Test that the config path is absolute."""
        try:
            path = get_claude_desktop_config_path()
            assert path.is_absolute()
        except RuntimeError:
            pytest.skip("Unsupported OS")

    def test_path_has_correct_structure_linux(self):
        """Test Linux path structure."""
        if platform.system() != "Linux":
            pytest.skip("Not running on Linux")

        path = get_claude_desktop_config_path()
        assert ".config" in str(path)
        assert "Claude" in str(path)

    def test_path_has_correct_structure_macos(self):
        """Test macOS path structure."""
        if platform.system() != "Darwin":
            pytest.skip("Not running on macOS")

        path = get_claude_desktop_config_path()
        assert "Library" in str(path)
        assert "Application Support" in str(path)
        assert "Claude" in str(path)

    def test_path_has_correct_structure_windows(self):
        """Test Windows path structure."""
        if platform.system() != "Windows":
            pytest.skip("Not running on Windows")

        path = get_claude_desktop_config_path()
        assert "AppData" in str(path) or "APPDATA" in str(path).upper()
        assert "Claude" in str(path)

import json
import sys
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from anaconda_mcp.cli import cli


def _strip_warning(output: str) -> str:
    return "\n".join(line for line in output.splitlines() if not line.startswith("Warning:"))


class TestClientRegistry:
    def test_supported_clients_includes_expected_set(self):
        from anaconda_mcp.client_config import SUPPORTED_CLIENTS

        for client in ["claude-desktop", "cursor", "windsurf", "vscode", "opencode"]:
            assert client in SUPPORTED_CLIENTS

    def test_get_config_path_unknown_client_raises(self):
        from anaconda_mcp.client_config import get_client_config_path

        with pytest.raises(ValueError, match="Unsupported client"):
            get_client_config_path("notarealclient")

    def test_get_config_path_cursor_linux(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch("platform.system", return_value="Linux"):
            with mock.patch.object(Path, "home", return_value=Path("/home/u")):
                assert get_client_config_path("cursor") == Path("/home/u/.cursor/mcp.json")

    def test_get_config_path_cursor_macos(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch("platform.system", return_value="Darwin"):
            with mock.patch.object(Path, "home", return_value=Path("/Users/u")):
                assert get_client_config_path("cursor") == Path("/Users/u/.cursor/mcp.json")

    def test_get_config_path_cursor_windows(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch("platform.system", return_value="Windows"):
            with mock.patch.object(Path, "home", return_value=Path("C:/Users/u")):
                assert get_client_config_path("cursor") == Path("C:/Users/u/.cursor/mcp.json")

    def test_get_config_path_windsurf_linux(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("windsurf") == Path("/home/u/.codeium/windsurf/mcp_config.json")

    def test_get_config_path_windsurf_macos(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/Users/u")):
            assert get_client_config_path("windsurf") == Path("/Users/u/.codeium/windsurf/mcp_config.json")

    def test_get_config_path_opencode_linux(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch("anaconda_mcp.client_config.user_config_dir", return_value="/home/u/.config/opencode"):
            assert get_client_config_path("opencode") == Path("/home/u/.config/opencode/opencode.json")

    def test_get_config_path_opencode_macos(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch(
            "anaconda_mcp.client_config.user_config_dir",
            return_value="/Users/u/Library/Application Support/opencode",
        ):
            assert get_client_config_path("opencode") == Path(
                "/Users/u/Library/Application Support/opencode/opencode.json"
            )

    def test_get_config_path_vscode_macos(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch(
            "anaconda_mcp.client_config.user_data_dir",
            return_value="/Users/u/Library/Application Support/Code",
        ):
            assert get_client_config_path("vscode") == Path("/Users/u/Library/Application Support/Code/User/mcp.json")

    def test_get_config_path_vscode_linux(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch("anaconda_mcp.client_config.user_data_dir", return_value="/home/u/.config/Code"):
            assert get_client_config_path("vscode") == Path("/home/u/.config/Code/User/mcp.json")

    def test_get_config_path_vscode_windows(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch(
            "anaconda_mcp.client_config.user_data_dir",
            return_value="C:/Users/u/AppData/Roaming/Code",
        ):
            assert get_client_config_path("vscode") == Path("C:/Users/u/AppData/Roaming/Code/User/mcp.json")

    def test_get_config_path_claude_desktop_delegates(self):
        from anaconda_mcp.claude_desktop import get_claude_desktop_config_path
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch("platform.system", return_value="Darwin"):
            with mock.patch.object(Path, "home", return_value=Path("/Users/u")):
                assert get_client_config_path("claude-desktop") == get_claude_desktop_config_path()


class TestBuildClientConfig:
    def test_build_stdio_config_cursor_has_type_field(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("cursor")
        assert config["type"] == "stdio"
        assert "command" in config
        assert "args" in config

    def test_build_stdio_config_claude_desktop_has_env_vars(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("claude-desktop")
        assert "type" not in config
        assert "ANACONDA_MCP_PYTHON_EXECUTABLE" in config["env"]
        assert "MCP_COMPOSE_CONFIG_DIR" in config["env"]

    def test_build_stdio_config_claude_desktop_command_is_python(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("claude-desktop")
        assert config["command"] == sys.executable

    def test_build_stdio_config_opencode_uses_array_command(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("opencode")
        assert config["type"] == "local"
        assert isinstance(config["command"], list)
        assert "environment" in config
        assert "env" not in config

    def test_build_stdio_config_opencode_command_contains_serve(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("opencode")
        assert "serve" in config["command"]

    def test_build_stdio_config_vscode_no_type_field(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("vscode")
        assert "type" not in config
        assert "command" in config
        assert "args" in config

    def test_build_stdio_config_windsurf_standard_shape(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("windsurf")
        assert "command" in config
        assert "args" in config

    def test_build_http_config_windsurf_uses_server_url(self):
        from anaconda_mcp.client_config import build_client_http_config

        config = build_client_http_config("windsurf", host="localhost", port=8000)
        assert "serverUrl" in config
        assert "url" not in config
        assert config["serverUrl"] == "http://localhost:8000/mcp"

    def test_build_http_config_cursor_uses_url(self):
        from anaconda_mcp.client_config import build_client_http_config

        config = build_client_http_config("cursor", host="localhost", port=8000)
        assert config["url"] == "http://localhost:8000/mcp"
        assert "serverUrl" not in config

    def test_build_http_config_vscode_uses_http_type(self):
        from anaconda_mcp.client_config import build_client_http_config

        config = build_client_http_config("vscode", host="localhost", port=8000)
        assert config["type"] == "http"
        assert config["url"] == "http://localhost:8000/mcp"

    def test_build_http_config_opencode_uses_remote_type(self):
        from anaconda_mcp.client_config import build_client_http_config

        config = build_client_http_config("opencode", host="localhost", port=8000)
        assert config["type"] == "remote"
        assert "url" in config

    def test_build_http_config_claude_desktop_standard_shape(self):
        from anaconda_mcp.client_config import build_client_http_config

        config = build_client_http_config("claude-desktop", host="localhost", port=8888)
        assert config["url"] == "http://localhost:8888/mcp"
        assert config["transport"] == "streamable-http"


class TestConfigureClient:
    def test_configure_client_cursor_creates_mcp_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        result = configure_client("cursor", config_path=f, transport="stdio", backup=False)
        assert result["created"] is True
        config = json.loads(f.read_text())
        assert "mcpServers" in config
        assert "anaconda-mcp" in config["mcpServers"]

    def test_configure_client_vscode_creates_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("vscode", config_path=f, transport="stdio", backup=False)
        config = json.loads(f.read_text())
        assert "servers" in config
        assert "mcpServers" not in config

    def test_configure_client_opencode_creates_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "opencode.json"
        configure_client("opencode", config_path=f, transport="stdio", backup=False)
        config = json.loads(f.read_text())
        assert "mcp" in config

    def test_configure_client_preserves_existing_entries(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"other": {}}}')
        configure_client("cursor", config_path=f, transport="stdio", backup=False)
        config = json.loads(f.read_text())
        assert "other" in config["mcpServers"]
        assert "anaconda-mcp" in config["mcpServers"]

    def test_configure_client_fails_if_exists_without_force(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"anaconda-mcp": {}}}')
        with pytest.raises(FileExistsError, match="already exists"):
            configure_client("cursor", config_path=f, transport="stdio", backup=False)

    def test_configure_client_force_overwrites(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"anaconda-mcp": {"old": True}}}')
        configure_client("cursor", config_path=f, transport="stdio", backup=False, force=True)
        config = json.loads(f.read_text())
        assert "old" not in config["mcpServers"]["anaconda-mcp"]

    def test_configure_client_creates_parent_dirs(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "deep" / "nested" / "mcp.json"
        configure_client("cursor", config_path=f, transport="stdio", backup=False)
        assert f.exists()

    def test_configure_client_creates_backup(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {}}')
        result = configure_client("cursor", config_path=f, transport="stdio", backup=True)
        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()

    def test_configure_client_invalid_transport_raises(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with pytest.raises(ValueError, match="Invalid transport"):
            configure_client("cursor", config_path=tmp_path / "mcp.json", transport="invalid", backup=False)

    def test_configure_client_delegates_to_claude_desktop(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "config.json"
        configure_client("claude-desktop", config_path=f, transport="stdio", backup=False)
        config = json.loads(f.read_text())
        assert "ANACONDA_MCP_PYTHON_EXECUTABLE" in config["mcpServers"]["anaconda-mcp"]["env"]

    def test_configure_client_returns_result_dict(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        result = configure_client("cursor", config_path=f, transport="stdio", backup=False)
        assert "config_path" in result
        assert "created" in result
        assert "updated" in result
        assert "server_name" in result
        assert "client" in result

    def test_configure_client_windsurf_http_uses_server_url(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp_config.json"
        configure_client("windsurf", config_path=f, transport="streamable-http", backup=False)
        config = json.loads(f.read_text())
        assert "serverUrl" in config["mcpServers"]["anaconda-mcp"]

    def test_configure_client_unknown_client_raises(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with pytest.raises(ValueError, match="Unsupported client"):
            configure_client("notarealclient", config_path=tmp_path / "mcp.json", transport="stdio", backup=False)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def patch_cursor_path(tmp_path):
    cursor_config = tmp_path / "cursor_mcp.json"
    with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=cursor_config):
        yield cursor_config


class TestSetupCommand:
    def test_setup_without_client_fails(self, runner):
        result = runner.invoke(cli, ["setup"])
        assert result.exit_code != 0

    def test_setup_single_client_creates_config(self, runner, patch_cursor_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup"])
        assert result.exit_code == 0
        assert patch_cursor_path.exists()

    def test_setup_single_client_success_message(self, runner, patch_cursor_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup"])
        assert result.exit_code == 0
        assert "cursor" in result.output.lower()

    def test_setup_streamable_http(self, runner, patch_cursor_path):
        result = runner.invoke(
            cli, ["setup", "--client", "cursor", "--transport", "streamable-http", "--port", "9000", "--no-backup"]
        )
        assert result.exit_code == 0
        config = json.loads(patch_cursor_path.read_text())
        assert "9000" in config["mcpServers"]["anaconda-mcp"]["url"]

    def test_setup_fails_if_exists_without_force(self, runner, patch_cursor_path):
        patch_cursor_path.write_text('{"mcpServers": {"anaconda-mcp": {}}}')
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_setup_force_overwrites(self, runner, patch_cursor_path):
        patch_cursor_path.write_text('{"mcpServers": {"anaconda-mcp": {"old": true}}}')
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--force", "--no-backup"])
        assert result.exit_code == 0
        config = json.loads(patch_cursor_path.read_text())
        assert "old" not in config["mcpServers"]["anaconda-mcp"]

    def test_setup_json_output(self, runner, patch_cursor_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup", "--json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "cursor" in output
        assert output["cursor"]["created"] is True

    def test_setup_unsupported_client(self, runner):
        result = runner.invoke(cli, ["setup", "--client", "notarealclient"])
        assert result.exit_code != 0
        assert "notarealclient" in result.output or "invalid" in result.output.lower()

    def test_setup_list_flag(self, runner):
        result = runner.invoke(cli, ["setup", "--list"])
        assert result.exit_code == 0
        assert "CLIENT" in result.output
        assert "TRANSPORTS" in result.output
        for client in ["cursor", "claude-desktop", "windsurf", "vscode", "opencode"]:
            assert client in result.output
        assert "stdio" in result.output
        assert "streamable-http" in result.output

    def test_setup_multiple_clients(self, runner, tmp_path):
        paths = {
            "cursor": tmp_path / "cursor.json",
            "windsurf": tmp_path / "windsurf.json",
        }

        def _fake_path(client):
            return paths[client]

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(cli, ["setup", "--client", "cursor", "--client", "windsurf", "--no-backup"])

        assert result.exit_code == 0
        assert paths["cursor"].exists()
        assert paths["windsurf"].exists()

    def test_setup_multiple_clients_json_output(self, runner, tmp_path):
        paths = {
            "cursor": tmp_path / "cursor.json",
            "windsurf": tmp_path / "windsurf.json",
        }

        def _fake_path(client):
            return paths[client]

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(
                cli, ["setup", "--client", "cursor", "--client", "windsurf", "--no-backup", "--json"]
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "cursor" in output
        assert "windsurf" in output

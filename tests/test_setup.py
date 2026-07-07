import json
import sys
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from anaconda_mcp.cli import cli
from anaconda_mcp.client_config import SCOPE_GLOBAL


def _strip_warning(output: str) -> str:
    return "\n".join(line for line in output.splitlines() if not line.startswith("Warning:"))


class TestClientRegistry:
    def test_supported_clients_includes_expected_set(self):
        from anaconda_mcp.client_config import SUPPORTED_CLIENTS

        for client in ["claude-desktop", "claude-code", "cursor", "windsurf", "vscode", "opencode", "kilo"]:
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

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("opencode") == Path("/home/u/.config/opencode/opencode.json")

    def test_get_config_path_opencode_macos(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/Users/u")):
            assert get_client_config_path("opencode") == Path("/Users/u/.config/opencode/opencode.json")

    def test_supported_clients_kilo_metadata(self):
        from anaconda_mcp.client_config import SUPPORTED_CLIENTS

        assert SUPPORTED_CLIENTS["kilo"] == {"config_key": "mcp", "supports_project_scope": True}

    def test_get_config_path_kilo_all_platforms(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("kilo") == Path("/home/u/.config/kilo/kilo.json")

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

    def test_get_config_path_claude_code_all_platforms(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("claude-code") == Path("/home/u/.claude.json")


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

    def test_build_stdio_config_kilo_matches_opencode(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        assert build_client_stdio_config("kilo") == build_client_stdio_config("opencode")
        assert "env" not in build_client_stdio_config("kilo")

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

    def test_build_stdio_config_claude_code_has_type_field(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("claude-code")
        assert config["type"] == "stdio"
        assert "command" in config
        assert "args" in config

    def test_build_stdio_config_claude_code_has_env(self):
        from anaconda_mcp.client_config import build_client_stdio_config

        config = build_client_stdio_config("claude-code")
        assert "env" in config


class TestConfigureClient:
    def test_configure_client_cursor_creates_mcp_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        result = configure_client("cursor", config_path=f, backup=False)
        assert result["created"] is True
        config = json.loads(f.read_text())
        assert "mcpServers" in config
        assert "anaconda-mcp" in config["mcpServers"]

    def test_configure_client_vscode_creates_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("vscode", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "servers" in config
        assert "mcpServers" not in config

    def test_configure_client_opencode_creates_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "opencode.json"
        configure_client("opencode", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "mcp" in config

    def test_configure_client_kilo_creates_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "kilo.json"
        configure_client("kilo", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "mcp" in config
        assert "anaconda-mcp" in config["mcp"]

    def test_configure_client_preserves_existing_entries(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"other": {}}}')
        configure_client("cursor", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "other" in config["mcpServers"]
        assert "anaconda-mcp" in config["mcpServers"]

    def test_configure_client_fails_if_exists_without_force(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"anaconda-mcp": {}}}')
        with pytest.raises(FileExistsError, match="already exists"):
            configure_client("cursor", config_path=f, backup=False)

    def test_configure_client_force_overwrites(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"anaconda-mcp": {"old": True}}}')
        configure_client("cursor", config_path=f, backup=False, force=True)
        config = json.loads(f.read_text())
        assert "old" not in config["mcpServers"]["anaconda-mcp"]

    def test_configure_client_creates_parent_dirs(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "deep" / "nested" / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)
        assert f.exists()

    def test_configure_client_creates_backup(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {}}')
        result = configure_client("cursor", config_path=f, backup=True)
        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()

    def test_configure_client_rejects_transport_keyword(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with pytest.raises(TypeError, match="transport"):
            configure_client("cursor", config_path=tmp_path / "mcp.json", transport="invalid", backup=False)

    def test_configure_client_delegates_to_claude_desktop(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "config.json"
        configure_client("claude-desktop", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "ANACONDA_MCP_PYTHON_EXECUTABLE" in config["mcpServers"]["anaconda-mcp"]["env"]

    def test_configure_client_returns_result_dict(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        result = configure_client("cursor", config_path=f, backup=False)
        assert "config_path" in result
        assert "created" in result
        assert "updated" in result
        assert "server_name" in result
        assert "client" in result

    def test_configure_client_windsurf_uses_stdio_config(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp_config.json"
        configure_client("windsurf", config_path=f, backup=False)
        config_text = f.read_text()
        assert "command" in json.loads(config_text)["mcpServers"]["anaconda-mcp"]
        assert "http://" not in config_text
        assert "streamable-http" not in config_text

    def test_configure_client_unknown_client_raises(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with pytest.raises(ValueError, match="Unsupported client"):
            configure_client("notarealclient", config_path=tmp_path / "mcp.json", backup=False)

    def test_configure_client_claude_code_creates_mcp_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / ".claude.json"
        configure_client("claude-code", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "mcpServers" in config
        assert "anaconda-mcp" in config["mcpServers"]
        assert config["mcpServers"]["anaconda-mcp"]["type"] == "stdio"

    def test_configure_client_claude_code_preserves_existing_keys(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / ".claude.json"
        f.write_text('{"projects": {"/some/path": {}}, "mcpServers": {"other": {}}}')
        configure_client("claude-code", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "projects" in config
        assert "other" in config["mcpServers"]
        assert "anaconda-mcp" in config["mcpServers"]


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

    def test_setup_rejects_streamable_http(self, runner, patch_cursor_path):
        result = runner.invoke(
            cli, ["setup", "--client", "cursor", "--transport", "streamable-http", "--port", "9000", "--no-backup"]
        )
        assert result.exit_code != 0
        assert "No such option" in result.output
        assert not patch_cursor_path.exists()

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
        output = json.loads(_strip_warning(result.output))
        assert "cursor" in output
        assert output["cursor"]["created"] is True

    def test_setup_unsupported_client(self, runner):
        result = runner.invoke(cli, ["setup", "--client", "notarealclient"])
        assert result.exit_code != 0
        assert "notarealclient" in result.output or "invalid" in result.output.lower()

    def test_setup_list_flag_removed(self, runner):
        result = runner.invoke(cli, ["setup", "--list"])
        assert result.exit_code != 0

    def test_setup_multiple_clients(self, runner, tmp_path):
        paths = {
            "cursor": tmp_path / "cursor.json",
            "windsurf": tmp_path / "windsurf.json",
        }

        def _fake_path(client, scope=SCOPE_GLOBAL, project_dir=None):
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

        def _fake_path(client, scope=SCOPE_GLOBAL, project_dir=None):
            return paths[client]

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(
                cli, ["setup", "--client", "cursor", "--client", "windsurf", "--no-backup", "--json"]
            )

        assert result.exit_code == 0
        output = json.loads(_strip_warning(result.output))
        assert "cursor" in output
        assert "windsurf" in output

    def test_setup_kilo_client_creates_config(self, runner, tmp_path):
        kilo_config = tmp_path / "kilo.json"
        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=kilo_config):
            result = runner.invoke(cli, ["setup", "--client", "kilo", "--no-backup"])
        assert result.exit_code == 0
        assert kilo_config.exists()
        config = json.loads(kilo_config.read_text())
        assert "mcp" in config
        assert "anaconda-mcp" in config["mcp"]


class TestGetClientProjectConfigPath:
    def test_cursor_project_path(self, tmp_path):
        from anaconda_mcp.client_config import get_client_project_config_path

        assert get_client_project_config_path("cursor", tmp_path) == tmp_path / ".cursor" / "mcp.json"

    def test_vscode_project_path(self, tmp_path):
        from anaconda_mcp.client_config import get_client_project_config_path

        assert get_client_project_config_path("vscode", tmp_path) == tmp_path / ".vscode" / "mcp.json"

    def test_opencode_project_path(self, tmp_path):
        from anaconda_mcp.client_config import get_client_project_config_path

        assert get_client_project_config_path("opencode", tmp_path) == tmp_path / "opencode.json"

    def test_kilo_project_path(self):
        from anaconda_mcp.client_config import get_client_project_config_path

        assert get_client_project_config_path("kilo", Path("/my/project")) == Path("/my/project/.kilo/kilo.json")

    def test_claude_code_project_path(self, tmp_path):
        from anaconda_mcp.client_config import get_client_project_config_path

        assert get_client_project_config_path("claude-code", tmp_path) == tmp_path / ".mcp.json"

    def test_windsurf_project_scope_raises(self):
        from anaconda_mcp.client_config import get_client_project_config_path

        with pytest.raises(ValueError, match="does not support project scope"):
            get_client_project_config_path("windsurf", Path("/some/dir"))

    def test_claude_desktop_project_scope_raises(self):
        from anaconda_mcp.client_config import get_client_project_config_path

        with pytest.raises(ValueError, match="does not support project scope"):
            get_client_project_config_path("claude-desktop", Path("/some/dir"))

    def test_get_config_path_global_scope_unchanged(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("cursor", scope="global") == Path("/home/u/.cursor/mcp.json")

    def test_get_config_path_project_scope_cursor(self, tmp_path):
        from anaconda_mcp.client_config import get_client_config_path

        assert (
            get_client_config_path("cursor", scope="project", project_dir=tmp_path) == tmp_path / ".cursor" / "mcp.json"
        )

    def test_get_config_path_project_scope_defaults_to_cwd(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "cwd", return_value=Path("/my/project")):
            assert get_client_config_path("cursor", scope="project") == Path("/my/project/.cursor/mcp.json")

    def test_get_config_path_project_scope_unsupported_raises(self):
        from anaconda_mcp.client_config import get_client_config_path

        with pytest.raises(ValueError, match="does not support project scope"):
            get_client_config_path("windsurf", scope="project")

    def test_supported_clients_has_scope_metadata(self):
        from anaconda_mcp.client_config import SUPPORTED_CLIENTS

        for client, meta in SUPPORTED_CLIENTS.items():
            assert "supports_project_scope" in meta, f"{client} missing supports_project_scope"


class TestConfigureClientScope:
    def test_project_scope_cursor_writes_correct_path(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        configure_client("cursor", scope="project", project_dir=tmp_path, backup=False)
        assert (tmp_path / ".cursor" / "mcp.json").exists()

    def test_project_scope_vscode_writes_correct_path(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        configure_client("vscode", scope="project", project_dir=tmp_path, backup=False)
        assert (tmp_path / ".vscode" / "mcp.json").exists()
        config = json.loads((tmp_path / ".vscode" / "mcp.json").read_text())
        assert "servers" in config

    def test_project_scope_opencode_writes_correct_path(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        configure_client("opencode", scope="project", project_dir=tmp_path, backup=False)
        assert (tmp_path / "opencode.json").exists()

    def test_project_scope_claude_code_writes_correct_path(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        configure_client("claude-code", scope="project", project_dir=tmp_path, backup=False)
        assert (tmp_path / ".mcp.json").exists()
        config = json.loads((tmp_path / ".mcp.json").read_text())
        assert "mcpServers" in config

    def test_project_scope_windsurf_raises(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with pytest.raises(ValueError, match="does not support project scope"):
            configure_client("windsurf", scope="project", project_dir=tmp_path, backup=False)

    def test_project_scope_claude_desktop_raises(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with pytest.raises(ValueError, match="does not support project scope"):
            configure_client("claude-desktop", scope="project", backup=False)

    def test_result_includes_scope_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        result = configure_client("cursor", scope="project", project_dir=tmp_path, backup=False)
        assert result["scope"] == "project"

    def test_global_scope_result_includes_scope_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        result = configure_client("cursor", config_path=tmp_path / "mcp.json", scope="global", backup=False)
        assert result["scope"] == "global"

    def test_project_dir_defaults_to_cwd(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with mock.patch.object(Path, "cwd", return_value=tmp_path):
            configure_client("cursor", scope="project", backup=False)
        assert (tmp_path / ".cursor" / "mcp.json").exists()


class TestSetupScopeFlag:
    def test_scope_global_is_default(self, runner, patch_cursor_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup"])
        assert result.exit_code == 0

    def test_scope_project_cursor(self, runner, tmp_path):
        with mock.patch.object(Path, "cwd", return_value=tmp_path):
            result = runner.invoke(cli, ["setup", "--client", "cursor", "--scope", "project", "--no-backup"])
        assert result.exit_code == 0
        assert (tmp_path / ".cursor" / "mcp.json").exists()

    def test_scope_project_with_project_dir(self, runner, tmp_path):
        result = runner.invoke(
            cli,
            [
                "setup",
                "--client",
                "cursor",
                "--scope",
                "project",
                "--project-dir",
                str(tmp_path),
                "--no-backup",
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / ".cursor" / "mcp.json").exists()

    def test_project_dir_without_scope_project_errors(self, runner, tmp_path):
        result = runner.invoke(
            cli,
            [
                "setup",
                "--client",
                "cursor",
                "--project-dir",
                str(tmp_path),
                "--no-backup",
            ],
        )
        assert result.exit_code != 0
        assert "--project-dir" in result.output or "scope" in result.output.lower()

    def test_scope_project_unsupported_client_errors(self, runner):
        result = runner.invoke(cli, ["setup", "--client", "windsurf", "--scope", "project", "--no-backup"])
        assert result.exit_code == 1
        assert "does not support project scope" in result.output

    def test_scope_project_json_output(self, runner, tmp_path):
        result = runner.invoke(
            cli,
            [
                "setup",
                "--client",
                "cursor",
                "--scope",
                "project",
                "--project-dir",
                str(tmp_path),
                "--no-backup",
                "--json",
            ],
        )
        assert result.exit_code == 0
        output = json.loads(_strip_warning(result.output))
        assert output["cursor"]["scope"] == "project"

    def test_list_shows_scope_column(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert result.exit_code == 0
        assert "SCOPE" in result.output

    def test_list_shows_project_scope_for_supported_clients(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "project" in result.output

    def test_list_shows_global_only_for_unsupported_clients(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "global" in result.output


class TestIsClientInstalled:
    def test_not_installed_when_config_missing(self, tmp_path):
        from anaconda_mcp.client_config import is_client_installed

        result = is_client_installed("cursor", config_path=tmp_path / "nonexistent.json")
        assert result["global"] is False

    def test_not_installed_when_server_absent(self, tmp_path):
        from anaconda_mcp.client_config import is_client_installed

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"other-server": {}}}')
        result = is_client_installed("cursor", config_path=f)
        assert result["global"] is False

    def test_installed_globally(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)
        result = is_client_installed("cursor", config_path=f)
        assert result["global"] is True

    def test_not_installed_project_when_no_project_config(self, tmp_path):
        from anaconda_mcp.client_config import is_client_installed

        result = is_client_installed("cursor", project_dir=tmp_path)
        assert result["project"] is False

    def test_installed_project(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        configure_client("cursor", scope="project", project_dir=tmp_path, backup=False)
        result = is_client_installed("cursor", project_dir=tmp_path)
        assert result["project"] is True

    def test_global_key_absent_for_project_only_clients(self, tmp_path):
        from anaconda_mcp.client_config import is_client_installed

        result = is_client_installed("windsurf", project_dir=tmp_path)
        assert "project" not in result

    def test_project_key_absent_for_global_only_clients(self, tmp_path):
        from anaconda_mcp.client_config import is_client_installed

        result = is_client_installed("windsurf")
        assert "project" not in result

    def test_both_installed(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        global_f = tmp_path / "global_mcp.json"
        configure_client("cursor", config_path=global_f, backup=False)
        configure_client("cursor", scope="project", project_dir=tmp_path, backup=False)
        result = is_client_installed("cursor", config_path=global_f, project_dir=tmp_path)
        assert result["global"] is True
        assert result["project"] is True

    def test_vscode_uses_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        f = tmp_path / "mcp.json"
        configure_client("vscode", config_path=f, backup=False)
        result = is_client_installed("vscode", config_path=f)
        assert result["global"] is True

    def test_opencode_uses_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        f = tmp_path / "opencode.json"
        configure_client("opencode", config_path=f, backup=False)
        result = is_client_installed("opencode", config_path=f)
        assert result["global"] is True

    def test_kilo_uses_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        f = tmp_path / "kilo.json"
        configure_client("kilo", config_path=f, backup=False)
        result = is_client_installed("kilo", config_path=f)
        assert result["global"] is True

    def test_unknown_client_raises(self, tmp_path):
        from anaconda_mcp.client_config import is_client_installed

        with pytest.raises(ValueError, match="Unsupported client"):
            is_client_installed("notarealclient")


class TestRemoveClient:
    def test_remove_client_cursor_removes_server(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)
        result = remove_client("cursor", config_path=f, backup=False)
        assert result["removed"] is True
        config = json.loads(f.read_text())
        assert "anaconda-mcp" not in config["mcpServers"]

    def test_remove_client_returns_result_dict(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)
        result = remove_client("cursor", config_path=f, backup=False)
        assert "client" in result
        assert "scope" in result
        assert "config_path" in result
        assert "backup_path" in result
        assert "server_name" in result
        assert "removed" in result

    def test_remove_client_preserves_other_entries(self, tmp_path):
        from anaconda_mcp.client_config import remove_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"anaconda-mcp": {}, "other": {}}}')
        remove_client("cursor", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "other" in config["mcpServers"]
        assert "anaconda-mcp" not in config["mcpServers"]

    def test_remove_client_raises_if_config_not_found(self, tmp_path):
        from anaconda_mcp.client_config import remove_client

        with pytest.raises(FileNotFoundError):
            remove_client("cursor", config_path=tmp_path / "nonexistent.json", backup=False)

    def test_remove_client_raises_if_server_not_found(self, tmp_path):
        from anaconda_mcp.client_config import remove_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {}}')
        with pytest.raises(KeyError, match="not found"):
            remove_client("cursor", config_path=f, backup=False)

    def test_remove_client_unknown_client_raises(self, tmp_path):
        from anaconda_mcp.client_config import remove_client

        with pytest.raises(ValueError, match="Unsupported client"):
            remove_client("notarealclient", config_path=tmp_path / "mcp.json", backup=False)

    def test_remove_client_creates_backup(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)
        result = remove_client("cursor", config_path=f, backup=True)
        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()

    def test_remove_client_no_backup(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)
        result = remove_client("cursor", config_path=f, backup=False)
        assert result["backup_path"] is None

    def test_remove_client_vscode_uses_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("vscode", config_path=f, backup=False)
        result = remove_client("vscode", config_path=f, backup=False)
        assert result["removed"] is True
        config = json.loads(f.read_text())
        assert "anaconda-mcp" not in config["servers"]

    def test_remove_client_opencode_uses_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "opencode.json"
        configure_client("opencode", config_path=f, backup=False)
        result = remove_client("opencode", config_path=f, backup=False)
        assert result["removed"] is True
        config = json.loads(f.read_text())
        assert "anaconda-mcp" not in config["mcp"]

    def test_remove_client_kilo_uses_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "kilo.json"
        configure_client("kilo", config_path=f, backup=False)
        result = remove_client("kilo", config_path=f, backup=False)
        assert result["removed"] is True
        config = json.loads(f.read_text())
        assert "anaconda-mcp" not in config["mcp"]

    def test_remove_client_delegates_to_claude_desktop(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "config.json"
        configure_client("claude-desktop", config_path=f, backup=False)
        result = remove_client("claude-desktop", config_path=f, backup=False)
        assert result["removed"] is True
        config = json.loads(f.read_text())
        assert "anaconda-mcp" not in config["mcpServers"]

    def test_remove_client_project_scope_cursor(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        configure_client("cursor", scope="project", project_dir=tmp_path, backup=False)
        result = remove_client("cursor", scope="project", project_dir=tmp_path, backup=False)
        assert result["removed"] is True
        config_path = tmp_path / ".cursor" / "mcp.json"
        config = json.loads(config_path.read_text())
        assert "anaconda-mcp" not in config["mcpServers"]

    def test_remove_client_project_scope_unsupported_raises(self, tmp_path):
        from anaconda_mcp.client_config import remove_client

        with pytest.raises(ValueError, match="does not support project scope"):
            remove_client("windsurf", scope="project", project_dir=tmp_path, backup=False)

    def test_remove_client_result_includes_scope_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)
        result = remove_client("cursor", config_path=f, scope="global", backup=False)
        assert result["scope"] == "global"


class TestRemoveCommand:
    def test_remove_without_client_fails(self, runner):
        result = runner.invoke(cli, ["remove"])
        assert result.exit_code != 0

    def test_remove_single_client_success(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)

        def _fake_path(client, scope=SCOPE_GLOBAL, project_dir=None):
            return f

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup"])

        assert result.exit_code == 0
        config = json.loads(f.read_text())
        assert "anaconda-mcp" not in config["mcpServers"]

    def test_remove_single_client_success_message(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)

        def _fake_path(client, scope=SCOPE_GLOBAL, project_dir=None):
            return f

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup"])

        assert result.exit_code == 0
        assert "cursor" in result.output.lower()

    def test_remove_multiple_clients(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        cursor_f = tmp_path / "cursor.json"
        vscode_f = tmp_path / "vscode.json"
        configure_client("cursor", config_path=cursor_f, backup=False)
        configure_client("vscode", config_path=vscode_f, backup=False)

        paths = {"cursor": cursor_f, "vscode": vscode_f}

        def _fake_path(client, scope=SCOPE_GLOBAL, project_dir=None):
            return paths[client]

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--client", "vscode", "--no-backup"])

        assert result.exit_code == 0
        assert "anaconda-mcp" not in json.loads(cursor_f.read_text())["mcpServers"]
        assert "anaconda-mcp" not in json.loads(vscode_f.read_text())["servers"]

    def test_remove_config_not_found_exits_1(self, runner, tmp_path):
        missing = tmp_path / "nonexistent.json"

        def _fake_path(client, scope=SCOPE_GLOBAL, project_dir=None):
            return missing

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup"])

        assert result.exit_code == 1

    def test_remove_server_not_found_exits_1(self, runner, tmp_path):
        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {}}')

        def _fake_path(client, scope=SCOPE_GLOBAL, project_dir=None):
            return f

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup"])

        assert result.exit_code == 1

    def test_remove_json_output(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False)

        def _fake_path(client, scope=SCOPE_GLOBAL, project_dir=None):
            return f

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup", "--json"])

        assert result.exit_code == 0
        output = json.loads(_strip_warning(result.output))
        assert "cursor" in output
        assert output["cursor"]["removed"] is True

    def test_remove_unsupported_client(self, runner):
        result = runner.invoke(cli, ["remove", "--client", "notarealclient"])
        assert result.exit_code != 0

    def test_remove_scope_project(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        configure_client("cursor", scope="project", project_dir=tmp_path, backup=False)

        with mock.patch.object(Path, "cwd", return_value=tmp_path):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--scope", "project", "--no-backup"])

        assert result.exit_code == 0
        config = json.loads((tmp_path / ".cursor" / "mcp.json").read_text())
        assert "anaconda-mcp" not in config["mcpServers"]

    def test_remove_project_dir_without_scope_project_errors(self, runner, tmp_path):
        result = runner.invoke(cli, ["remove", "--client", "cursor", "--project-dir", str(tmp_path), "--no-backup"])
        assert result.exit_code != 0
        assert "--project-dir" in result.output or "scope" in result.output.lower()

    def test_remove_scope_project_unsupported_client_errors(self, runner):
        result = runner.invoke(cli, ["remove", "--client", "windsurf", "--scope", "project", "--no-backup"])
        assert result.exit_code == 1
        assert "does not support project scope" in result.output

    def test_remove_list_flag_removed(self, runner):
        result = runner.invoke(cli, ["remove", "--list"])
        assert result.exit_code != 0


class TestClientsCommand:
    def test_clients_exits_0(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert result.exit_code == 0

    def test_clients_shows_client_header(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "CLIENT" in result.output

    def test_clients_shows_transports_header(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "TRANSPORTS" in result.output

    def test_clients_shows_scope_header(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "SCOPE" in result.output

    def test_clients_lists_all_supported_clients(self, runner):
        result = runner.invoke(cli, ["clients"])
        for client in ["cursor", "claude-desktop", "claude-code", "windsurf", "vscode", "opencode", "kilo"]:
            assert client in result.output

    def test_clients_shows_stdio_transport(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "stdio" in result.output

    def test_clients_does_not_show_streamable_http_transport(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "streamable-http" not in result.output

    def test_clients_shows_project_scope_for_supported(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "project" in result.output

    def test_clients_shows_global_for_all(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "global" in result.output

    def test_clients_shows_installed_header(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "INSTALLED" in result.output

    def test_clients_shows_dash_when_not_installed(self, runner, tmp_path):
        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=tmp_path / "none.json"):
            with mock.patch.object(Path, "cwd", return_value=tmp_path):
                result = runner.invoke(cli, ["clients"])
        assert "—" in result.output

    def test_clients_shows_global_installed_when_configured(self, runner, tmp_path):
        cursor_global = tmp_path / "cursor_mcp.json"

        from anaconda_mcp.client_config import configure_client

        configure_client("cursor", config_path=cursor_global, backup=False)

        original_get_path = __import__(
            "anaconda_mcp.client_config", fromlist=["get_client_config_path"]
        ).get_client_config_path

        def _patched_path(client, scope="global", project_dir=None):
            if client == "cursor" and scope == "global":
                return cursor_global
            return original_get_path(client, scope=scope, project_dir=project_dir)

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_patched_path):
            with mock.patch.object(Path, "cwd", return_value=tmp_path):
                result = runner.invoke(cli, ["clients"])

        lines = [line for line in result.output.splitlines() if "cursor" in line]
        assert lines, "cursor row not found"
        assert "global" in lines[0]

    def test_clients_shows_project_installed_when_configured(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        configure_client("cursor", scope="project", project_dir=tmp_path, backup=False)

        with mock.patch.object(Path, "cwd", return_value=tmp_path):
            result = runner.invoke(cli, ["clients", "--project-dir", str(tmp_path)])

        lines = [line for line in result.output.splitlines() if "cursor" in line]
        assert lines, "cursor row not found"
        assert "project" in lines[0]


class TestSetupWizard:
    @pytest.fixture
    def tty_runner(self):
        return CliRunner()

    def _tty(self):
        mock_sys = mock.MagicMock()
        mock_sys.stdin.isatty.return_value = True
        mock_sys.exit = __import__("sys").exit
        return mock.patch("anaconda_mcp.cli.sys", mock_sys)

    def _fake_page(self, adds, removes=None):
        removes = removes or []

        def _page(clients, supports_project, initial):
            result = []
            for i, c in enumerate(clients):
                result.append(
                    (c, "global", (c, "global") in adds or (i, 0) in initial and (c, "global") not in removes)
                )
                if supports_project[i]:
                    result.append(
                        (c, "project", (c, "project") in adds or (i, 1) in initial and (c, "project") not in removes)
                    )
            return result

        return _page

    def test_non_tty_without_client_raises_usage_error(self, tty_runner):
        result = tty_runner.invoke(cli, ["setup"])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_wizard_configure_creates_config(self, tty_runner, tmp_path):
        cursor_config = tmp_path / "cursor_mcp.json"

        def _fake_path(client, scope="global", project_dir=None):
            return cursor_config

        with self._tty():
            with mock.patch("anaconda_mcp.cli.setup_wizard_page", side_effect=self._fake_page([("cursor", "global")])):
                with mock.patch(
                    "anaconda_mcp.cli.is_client_installed", return_value={"global": False, "project": False}
                ):
                    with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
                        result = tty_runner.invoke(cli, ["setup", "--no-backup"])

        assert result.exit_code == 0
        assert cursor_config.exists()

    def test_wizard_no_changes_exits_cleanly(self, tty_runner, tmp_path):
        with self._tty():
            with mock.patch("anaconda_mcp.cli.setup_wizard_page", side_effect=self._fake_page([])):
                with mock.patch(
                    "anaconda_mcp.cli.is_client_installed", return_value={"global": False, "project": False}
                ):
                    result = tty_runner.invoke(cli, ["setup", "--no-backup"])

        assert result.exit_code == 0
        assert "No changes" in result.output

    def test_wizard_keyboard_interrupt_aborts(self, tty_runner):
        with self._tty():
            with mock.patch("anaconda_mcp.cli.setup_wizard_page", side_effect=KeyboardInterrupt):
                with mock.patch(
                    "anaconda_mcp.cli.is_client_installed", return_value={"global": False, "project": False}
                ):
                    result = tty_runner.invoke(cli, ["setup", "--no-backup"])
        assert result.exit_code != 0

    def test_wizard_pre_populates_installed_state(self, tty_runner, tmp_path):
        captured = {}

        def _fake_page(clients, supports_project, initial):
            captured["initial"] = set(initial)
            return [
                (c, "global", (i, 0) in initial) for i, c in enumerate(clients) if not supports_project[i] or True
            ] + [(c, "project", (i, 1) in initial) for i, c in enumerate(clients) if supports_project[i]]

        with self._tty():
            with mock.patch("anaconda_mcp.cli.setup_wizard_page", side_effect=_fake_page):
                with mock.patch(
                    "anaconda_mcp.cli.is_client_installed",
                    side_effect=lambda c, **kw: (
                        {"global": c == "cursor", "project": False} if c == "cursor" else {"global": False}
                    ),
                ):
                    tty_runner.invoke(cli, ["setup", "--no-backup"])

        clients = sorted(__import__("anaconda_mcp.client_config", fromlist=["SUPPORTED_CLIENTS"]).SUPPORTED_CLIENTS)
        cursor_idx = clients.index("cursor")
        assert (cursor_idx, 0) in captured["initial"]

    def test_wizard_remove_via_uncheck(self, tty_runner, tmp_path):
        cursor_config = tmp_path / "cursor_mcp.json"
        from anaconda_mcp.client_config import configure_client

        configure_client("cursor", config_path=cursor_config, backup=False)

        def _fake_path(client, scope="global", project_dir=None):
            return cursor_config

        def _fake_page(clients, supports_project, initial):
            return [(c, "global", False) for c in clients] + [
                (c, "project", False) for i, c in enumerate(clients) if supports_project[i]
            ]

        with self._tty():
            with mock.patch("anaconda_mcp.cli.setup_wizard_page", side_effect=_fake_page):
                with mock.patch(
                    "anaconda_mcp.cli.is_client_installed",
                    side_effect=lambda c, **kw: (
                        {"global": c == "cursor", "project": False} if c == "cursor" else {"global": False}
                    ),
                ):
                    with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
                        result = tty_runner.invoke(cli, ["setup", "--no-backup"])

        assert result.exit_code == 0
        import json as _json

        config = _json.loads(cursor_config.read_text())
        assert "anaconda-mcp" not in config.get("mcpServers", {})


class TestRemoveWizard:
    def test_remove_without_client_always_errors(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["remove"])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_remove_without_client_points_to_setup(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["remove"])
        assert "setup" in result.output

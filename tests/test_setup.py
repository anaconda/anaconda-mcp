import json
from pathlib import Path
from unittest import mock

import pytest
import tomlkit
from click.testing import CliRunner

from anaconda_mcp.cli import cli

TOKEN = "test-token"
MCP_URL = "https://anaconda.com/api/mcp"


def _strip_warning(output: str) -> str:
    return "\n".join(line for line in output.splitlines() if not line.startswith("Warning:"))


class TestClientRegistry:
    def test_supported_clients_includes_expected_set(self):
        from anaconda_mcp.client_config import SUPPORTED_CLIENTS

        for client in [
            "claude-desktop",
            "claude-code",
            "cursor",
            "windsurf",
            "vscode",
            "opencode",
            "kilo",
            "codex",
        ]:
            assert client in SUPPORTED_CLIENTS

    def test_claude_desktop_is_stdio_others_are_http(self):
        from anaconda_mcp.client_config import SUPPORTED_CLIENTS

        assert SUPPORTED_CLIENTS["claude-desktop"]["transport"] == "stdio"
        for client, meta in SUPPORTED_CLIENTS.items():
            if client != "claude-desktop":
                assert meta["transport"] == "http", f"{client} should be http"

    def test_get_config_path_unknown_client_raises(self):
        from anaconda_mcp.client_config import get_client_config_path

        with pytest.raises(ValueError, match="Unsupported client"):
            get_client_config_path("notarealclient")

    def test_get_config_path_cursor(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("cursor") == Path("/home/u/.cursor/mcp.json")

    def test_get_config_path_windsurf(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("windsurf") == Path("/home/u/.codeium/windsurf/mcp_config.json")

    def test_get_config_path_opencode(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("opencode") == Path("/home/u/.config/opencode/opencode.json")

    def test_get_config_path_kilo(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("kilo") == Path("/home/u/.config/kilo/kilo.json")

    def test_get_config_path_codex(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("codex") == Path("/home/u/.codex/config.toml")

    def test_get_config_path_codex_respects_codex_home(self, monkeypatch):
        from anaconda_mcp.client_config import get_client_config_path

        monkeypatch.setenv("CODEX_HOME", "/custom/codex")
        assert get_client_config_path("codex") == Path("/custom/codex/config.toml")

    def test_get_config_path_vscode(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch(
            "anaconda_mcp.client_config.user_data_dir",
            return_value="/Users/u/Library/Application Support/Code",
        ):
            assert get_client_config_path("vscode") == Path("/Users/u/Library/Application Support/Code/User/mcp.json")

    def test_get_config_path_claude_desktop_delegates(self):
        from anaconda_mcp.claude_desktop import get_claude_desktop_config_path
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch("platform.system", return_value="Darwin"):
            with mock.patch.object(Path, "home", return_value=Path("/Users/u")):
                assert get_client_config_path("claude-desktop") == get_claude_desktop_config_path()

    def test_get_config_path_claude_code(self):
        from anaconda_mcp.client_config import get_client_config_path

        with mock.patch.object(Path, "home", return_value=Path("/home/u")):
            assert get_client_config_path("claude-code") == Path("/home/u/.claude.json")


class TestBuildClientRemoteConfig:
    def test_unknown_client_raises(self):
        from anaconda_mcp.client_config import build_client_remote_config

        with pytest.raises(ValueError, match="Unsupported client"):
            build_client_remote_config("notarealclient", MCP_URL, TOKEN)

    def test_claude_desktop_rejects_remote(self):
        from anaconda_mcp.client_config import build_client_remote_config

        with pytest.raises(ValueError, match="does not support remote"):
            build_client_remote_config("claude-desktop", MCP_URL, TOKEN)

    def test_codex_rejects_json_builder(self):
        from anaconda_mcp.client_config import build_client_remote_config

        with pytest.raises(ValueError, match="TOML"):
            build_client_remote_config("codex", MCP_URL, TOKEN)

    def test_claude_code_shape(self):
        from anaconda_mcp.client_config import build_client_remote_config

        config = build_client_remote_config("claude-code", MCP_URL, TOKEN)
        assert config["type"] == "http"
        assert config["url"] == MCP_URL
        assert config["headers"]["Authorization"] == f"Bearer {TOKEN}"

    def test_cursor_shape(self):
        from anaconda_mcp.client_config import build_client_remote_config

        config = build_client_remote_config("cursor", MCP_URL, TOKEN)
        assert config["url"] == MCP_URL
        assert config["headers"]["Authorization"] == f"Bearer {TOKEN}"
        assert "command" not in config

    def test_windsurf_uses_server_url(self):
        from anaconda_mcp.client_config import build_client_remote_config

        config = build_client_remote_config("windsurf", MCP_URL, TOKEN)
        assert config["serverUrl"] == MCP_URL
        assert "url" not in config
        assert config["headers"]["Authorization"] == f"Bearer {TOKEN}"

    def test_vscode_shape(self):
        from anaconda_mcp.client_config import build_client_remote_config

        config = build_client_remote_config("vscode", MCP_URL, TOKEN)
        assert config["type"] == "http"
        assert config["url"] == MCP_URL
        assert config["headers"]["Authorization"] == f"Bearer {TOKEN}"

    def test_opencode_and_kilo_match(self):
        from anaconda_mcp.client_config import build_client_remote_config

        opencode = build_client_remote_config("opencode", MCP_URL, TOKEN)
        kilo = build_client_remote_config("kilo", MCP_URL, TOKEN)
        assert opencode == kilo
        assert opencode["type"] == "remote"
        assert opencode["enabled"] is True
        assert opencode["headers"]["Authorization"] == f"Bearer {TOKEN}"


class TestConfigureClient:
    def test_configure_client_cursor_creates_mcp_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        result = configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        assert result["created"] is True
        config = json.loads(f.read_text())
        assert "anaconda-mcp" in config["mcpServers"]

    def test_configure_client_vscode_creates_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("vscode", config_path=f, backup=False, token=TOKEN)
        config = json.loads(f.read_text())
        assert "servers" in config
        assert "mcpServers" not in config

    def test_configure_client_opencode_creates_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "opencode.json"
        configure_client("opencode", config_path=f, backup=False, token=TOKEN)
        assert "mcp" in json.loads(f.read_text())

    def test_configure_client_kilo_creates_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "kilo.json"
        configure_client("kilo", config_path=f, backup=False, token=TOKEN)
        config = json.loads(f.read_text())
        assert config["mcp"]["anaconda-mcp"]["type"] == "remote"

    def test_configure_client_preserves_existing_entries(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"other": {}}}')
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        config = json.loads(f.read_text())
        assert "other" in config["mcpServers"]
        assert "anaconda-mcp" in config["mcpServers"]

    def test_configure_client_overwrites_existing_stdio_entry(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"anaconda-mcp": {"command": "old", "args": []}}}')
        result = configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        assert result["updated"] is True
        entry = json.loads(f.read_text())["mcpServers"]["anaconda-mcp"]
        assert "command" not in entry
        assert entry["url"] == MCP_URL

    def test_configure_client_requires_token(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with pytest.raises(ValueError, match="token"):
            configure_client("cursor", config_path=tmp_path / "mcp.json", backup=False)

    def test_configure_client_creates_parent_dirs(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "deep" / "nested" / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        assert f.exists()

    def test_configure_client_creates_backup(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {}}')
        result = configure_client("cursor", config_path=f, backup=True, token=TOKEN)
        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()

    def test_configure_client_delegates_to_claude_desktop(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "config.json"
        configure_client("claude-desktop", config_path=f, backup=False)
        config = json.loads(f.read_text())
        assert "ANACONDA_MCP_PYTHON_EXECUTABLE" in config["mcpServers"]["anaconda-mcp"]["env"]

    def test_configure_client_claude_desktop_needs_no_token(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        result = configure_client("claude-desktop", config_path=tmp_path / "config.json", backup=False)
        assert result["transport"] == "stdio"

    def test_configure_client_returns_result_dict(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        result = configure_client("cursor", config_path=tmp_path / "mcp.json", backup=False, token=TOKEN)
        assert result["transport"] == "http"
        assert "config_path" in result
        assert "created" in result
        assert "updated" in result
        assert "server_name" in result
        assert "client" in result
        assert "scope" not in result

    def test_configure_client_windsurf_uses_remote_config(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp_config.json"
        configure_client("windsurf", config_path=f, backup=False, token=TOKEN)
        entry = json.loads(f.read_text())["mcpServers"]["anaconda-mcp"]
        assert entry["serverUrl"] == MCP_URL
        assert "command" not in entry

    def test_configure_client_unknown_client_raises(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        with pytest.raises(ValueError, match="Unsupported client"):
            configure_client("notarealclient", config_path=tmp_path / "mcp.json", backup=False, token=TOKEN)

    def test_configure_client_claude_code_remote(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / ".claude.json"
        configure_client("claude-code", config_path=f, backup=False, token=TOKEN)
        entry = json.loads(f.read_text())["mcpServers"]["anaconda-mcp"]
        assert entry["type"] == "http"
        assert entry["url"] == MCP_URL

    def test_configure_client_claude_code_preserves_existing_keys(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / ".claude.json"
        f.write_text('{"projects": {"/some/path": {}}, "mcpServers": {"other": {}}}')
        configure_client("claude-code", config_path=f, backup=False, token=TOKEN)
        config = json.loads(f.read_text())
        assert "projects" in config
        assert "other" in config["mcpServers"]
        assert "anaconda-mcp" in config["mcpServers"]


class TestConfigureCodex:
    def test_creates_mcp_servers_table(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "config.toml"
        result = configure_client("codex", config_path=f, backup=False, token=TOKEN)
        assert result["created"] is True
        doc = tomlkit.parse(f.read_text())
        entry = doc["mcp_servers"]["anaconda-mcp"]
        assert entry["url"] == MCP_URL
        assert entry["http_headers"]["Authorization"] == f"Bearer {TOKEN}"

    def test_preserves_existing_toml_content_and_comments(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "config.toml"
        f.write_text(
            '# my codex config\nmodel = "gpt-5"\n\n[mcp_servers.other]\nurl = "https://example.com/mcp"  # keep me\n'
        )
        configure_client("codex", config_path=f, backup=False, token=TOKEN)
        text = f.read_text()
        doc = tomlkit.parse(text)
        assert doc["model"] == "gpt-5"
        assert doc["mcp_servers"]["other"]["url"] == "https://example.com/mcp"
        assert doc["mcp_servers"]["anaconda-mcp"]["url"] == MCP_URL
        assert "# keep me" in text

    def test_overwrites_existing_entry_with_fresh_token(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "config.toml"
        configure_client("codex", config_path=f, backup=False, token="old-token")
        result = configure_client("codex", config_path=f, backup=False, token="new-token")
        assert result["updated"] is True
        doc = tomlkit.parse(f.read_text())
        assert doc["mcp_servers"]["anaconda-mcp"]["http_headers"]["Authorization"] == "Bearer new-token"

    def test_creates_backup(self, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "config.toml"
        f.write_text('model = "gpt-5"\n')
        result = configure_client("codex", config_path=f, backup=True, token=TOKEN)
        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()


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

    def test_setup_writes_remote_url_config(self, runner, patch_cursor_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup"])
        assert result.exit_code == 0
        entry = json.loads(patch_cursor_path.read_text())["mcpServers"]["anaconda-mcp"]
        assert entry["url"] == MCP_URL
        assert entry["headers"]["Authorization"].startswith("Bearer ")

    def test_setup_single_client_success_message(self, runner, patch_cursor_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup"])
        assert result.exit_code == 0
        assert "cursor" in result.output.lower()

    def test_setup_rejects_removed_scope_option(self, runner):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--scope", "project"])
        assert result.exit_code != 0
        assert "No such option" in result.output

    def test_setup_rejects_removed_project_dir_option(self, runner, tmp_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "No such option" in result.output

    def test_setup_rejects_removed_force_option(self, runner):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--force"])
        assert result.exit_code != 0
        assert "No such option" in result.output

    def test_setup_rejects_transport_option(self, runner, patch_cursor_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--transport", "streamable-http", "--no-backup"])
        assert result.exit_code != 0
        assert "No such option" in result.output
        assert not patch_cursor_path.exists()

    def test_setup_overwrites_existing_entry_without_force(self, runner, patch_cursor_path):
        patch_cursor_path.write_text('{"mcpServers": {"anaconda-mcp": {"command": "old"}}}')
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup"])
        assert result.exit_code == 0
        entry = json.loads(patch_cursor_path.read_text())["mcpServers"]["anaconda-mcp"]
        assert "command" not in entry
        assert entry["url"] == MCP_URL

    def test_setup_json_output(self, runner, patch_cursor_path):
        result = runner.invoke(cli, ["setup", "--client", "cursor", "--no-backup", "--json"])
        assert result.exit_code == 0
        output = json.loads(_strip_warning(result.output))
        assert output["cursor"]["created"] is True
        assert output["cursor"]["transport"] == "http"

    def test_setup_unsupported_client(self, runner):
        result = runner.invoke(cli, ["setup", "--client", "notarealclient"])
        assert result.exit_code != 0

    def test_setup_list_flag_removed(self, runner):
        result = runner.invoke(cli, ["setup", "--list"])
        assert result.exit_code != 0

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
        output = json.loads(_strip_warning(result.output))
        assert "cursor" in output
        assert "windsurf" in output

    def test_setup_kilo_client_creates_config(self, runner, tmp_path):
        kilo_config = tmp_path / "kilo.json"
        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=kilo_config):
            result = runner.invoke(cli, ["setup", "--client", "kilo", "--no-backup"])
        assert result.exit_code == 0
        config = json.loads(kilo_config.read_text())
        assert config["mcp"]["anaconda-mcp"]["type"] == "remote"

    def test_setup_codex_client_writes_toml(self, runner, tmp_path):
        codex_config = tmp_path / "config.toml"
        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=codex_config):
            result = runner.invoke(cli, ["setup", "--client", "codex", "--no-backup"])
        assert result.exit_code == 0
        doc = tomlkit.parse(codex_config.read_text())
        assert doc["mcp_servers"]["anaconda-mcp"]["url"] == MCP_URL

    def test_setup_claude_desktop_prints_stdio_note(self, runner, tmp_path):
        desktop_config = tmp_path / "claude_desktop_config.json"
        with mock.patch("anaconda_mcp.claude_desktop.get_claude_desktop_config_path", return_value=desktop_config):
            result = runner.invoke(cli, ["setup", "--client", "claude-desktop", "--no-backup"])
        assert result.exit_code == 0
        assert "does not support remote MCP servers" in result.output
        entry = json.loads(desktop_config.read_text())["mcpServers"]["anaconda-mcp"]
        assert "command" in entry


class TestIsClientInstalled:
    def test_not_installed_when_config_missing(self, tmp_path):
        from anaconda_mcp.client_config import is_client_installed

        assert is_client_installed("cursor", config_path=tmp_path / "nonexistent.json") is False

    def test_not_installed_when_server_absent(self, tmp_path):
        from anaconda_mcp.client_config import is_client_installed

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"other-server": {}}}')
        assert is_client_installed("cursor", config_path=f) is False

    def test_installed(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        assert is_client_installed("cursor", config_path=f) is True

    def test_vscode_uses_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        f = tmp_path / "mcp.json"
        configure_client("vscode", config_path=f, backup=False, token=TOKEN)
        assert is_client_installed("vscode", config_path=f) is True

    def test_codex_uses_toml(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, is_client_installed

        f = tmp_path / "config.toml"
        configure_client("codex", config_path=f, backup=False, token=TOKEN)
        assert is_client_installed("codex", config_path=f) is True
        assert is_client_installed("codex", server_name="other", config_path=f) is False

    def test_unknown_client_raises(self):
        from anaconda_mcp.client_config import is_client_installed

        with pytest.raises(ValueError, match="Unsupported client"):
            is_client_installed("notarealclient")


class TestClientNeedsUpdate:
    def test_not_installed_needs_no_update(self, tmp_path):
        from anaconda_mcp.client_config import client_needs_update

        assert client_needs_update("cursor", config_path=tmp_path / "none.json") is False

    def test_remote_entry_is_current(self, tmp_path):
        from anaconda_mcp.client_config import client_needs_update, configure_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        assert client_needs_update("cursor", config_path=f) is False

    def test_legacy_stdio_entry_needs_update(self, tmp_path):
        from anaconda_mcp.client_config import client_needs_update

        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {"anaconda-mcp": {"command": "python", "args": ["-m", "anaconda_mcp"]}}}')
        assert client_needs_update("cursor", config_path=f) is True

    def test_windsurf_server_url_entry_is_current(self, tmp_path):
        from anaconda_mcp.client_config import client_needs_update, configure_client

        f = tmp_path / "mcp_config.json"
        configure_client("windsurf", config_path=f, backup=False, token=TOKEN)
        assert client_needs_update("windsurf", config_path=f) is False

    def test_claude_desktop_stdio_never_needs_update(self, tmp_path):
        from anaconda_mcp.client_config import client_needs_update, configure_client

        f = tmp_path / "config.json"
        configure_client("claude-desktop", config_path=f, backup=False)
        assert client_needs_update("claude-desktop", config_path=f) is False

    def test_codex_entry_with_url_is_current(self, tmp_path):
        from anaconda_mcp.client_config import client_needs_update, configure_client

        f = tmp_path / "config.toml"
        configure_client("codex", config_path=f, backup=False, token=TOKEN)
        assert client_needs_update("codex", config_path=f) is False


class TestRemoveClient:
    def test_remove_client_cursor_removes_server(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        result = remove_client("cursor", config_path=f, backup=False)
        assert result["removed"] is True
        assert "anaconda-mcp" not in json.loads(f.read_text())["mcpServers"]

    def test_remove_client_returns_result_dict(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        result = remove_client("cursor", config_path=f, backup=False)
        assert "client" in result
        assert "config_path" in result
        assert "backup_path" in result
        assert "server_name" in result
        assert "removed" in result
        assert "scope" not in result

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
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        result = remove_client("cursor", config_path=f, backup=True)
        assert result["backup_path"] is not None
        assert Path(result["backup_path"]).exists()

    def test_remove_client_no_backup(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)
        result = remove_client("cursor", config_path=f, backup=False)
        assert result["backup_path"] is None

    def test_remove_client_vscode_uses_servers_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "mcp.json"
        configure_client("vscode", config_path=f, backup=False, token=TOKEN)
        result = remove_client("vscode", config_path=f, backup=False)
        assert result["removed"] is True
        assert "anaconda-mcp" not in json.loads(f.read_text())["servers"]

    def test_remove_client_opencode_uses_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "opencode.json"
        configure_client("opencode", config_path=f, backup=False, token=TOKEN)
        result = remove_client("opencode", config_path=f, backup=False)
        assert result["removed"] is True
        assert "anaconda-mcp" not in json.loads(f.read_text())["mcp"]

    def test_remove_client_kilo_uses_mcp_key(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "kilo.json"
        configure_client("kilo", config_path=f, backup=False, token=TOKEN)
        result = remove_client("kilo", config_path=f, backup=False)
        assert result["removed"] is True
        assert "anaconda-mcp" not in json.loads(f.read_text())["mcp"]

    def test_remove_client_codex_uses_toml(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "config.toml"
        configure_client("codex", config_path=f, backup=False, token=TOKEN)
        result = remove_client("codex", config_path=f, backup=False)
        assert result["removed"] is True
        doc = tomlkit.parse(f.read_text())
        assert "anaconda-mcp" not in doc.get("mcp_servers", {})

    def test_remove_client_codex_raises_if_server_not_found(self, tmp_path):
        from anaconda_mcp.client_config import remove_client

        f = tmp_path / "config.toml"
        f.write_text("[mcp_servers]\n")
        with pytest.raises(KeyError, match="not found"):
            remove_client("codex", config_path=f, backup=False)

    def test_remove_client_delegates_to_claude_desktop(self, tmp_path):
        from anaconda_mcp.client_config import configure_client, remove_client

        f = tmp_path / "config.json"
        configure_client("claude-desktop", config_path=f, backup=False)
        result = remove_client("claude-desktop", config_path=f, backup=False)
        assert result["removed"] is True
        assert "anaconda-mcp" not in json.loads(f.read_text())["mcpServers"]


class TestRemoveCommand:
    def test_remove_without_client_fails(self, runner):
        result = runner.invoke(cli, ["remove"])
        assert result.exit_code != 0

    def test_remove_single_client_success(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=f):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup"])

        assert result.exit_code == 0
        assert "anaconda-mcp" not in json.loads(f.read_text())["mcpServers"]

    def test_remove_single_client_success_message(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=f):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup"])

        assert result.exit_code == 0
        assert "cursor" in result.output.lower()

    def test_remove_multiple_clients(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        cursor_f = tmp_path / "cursor.json"
        vscode_f = tmp_path / "vscode.json"
        configure_client("cursor", config_path=cursor_f, backup=False, token=TOKEN)
        configure_client("vscode", config_path=vscode_f, backup=False, token=TOKEN)

        paths = {"cursor": cursor_f, "vscode": vscode_f}

        def _fake_path(client):
            return paths[client]

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--client", "vscode", "--no-backup"])

        assert result.exit_code == 0
        assert "anaconda-mcp" not in json.loads(cursor_f.read_text())["mcpServers"]
        assert "anaconda-mcp" not in json.loads(vscode_f.read_text())["servers"]

    def test_remove_config_not_found_exits_1(self, runner, tmp_path):
        missing = tmp_path / "nonexistent.json"

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=missing):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup"])

        assert result.exit_code == 1

    def test_remove_server_not_found_exits_1(self, runner, tmp_path):
        f = tmp_path / "mcp.json"
        f.write_text('{"mcpServers": {}}')

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=f):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup"])

        assert result.exit_code == 1

    def test_remove_json_output(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        f = tmp_path / "mcp.json"
        configure_client("cursor", config_path=f, backup=False, token=TOKEN)

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=f):
            result = runner.invoke(cli, ["remove", "--client", "cursor", "--no-backup", "--json"])

        assert result.exit_code == 0
        output = json.loads(_strip_warning(result.output))
        assert output["cursor"]["removed"] is True

    def test_remove_unsupported_client(self, runner):
        result = runner.invoke(cli, ["remove", "--client", "notarealclient"])
        assert result.exit_code != 0

    def test_remove_rejects_removed_scope_option(self, runner):
        result = runner.invoke(cli, ["remove", "--client", "cursor", "--scope", "project"])
        assert result.exit_code != 0
        assert "No such option" in result.output

    def test_remove_rejects_removed_project_dir_option(self, runner, tmp_path):
        result = runner.invoke(cli, ["remove", "--client", "cursor", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "No such option" in result.output

    def test_remove_list_flag_removed(self, runner):
        result = runner.invoke(cli, ["remove", "--list"])
        assert result.exit_code != 0


class TestClientsCommand:
    def test_clients_exits_0(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert result.exit_code == 0

    def test_clients_shows_expected_headers(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "CLIENT" in result.output
        assert "TRANSPORT" in result.output
        assert "INSTALLED" in result.output

    def test_clients_has_no_scope_column(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "SCOPE" not in result.output

    def test_clients_lists_all_supported_clients(self, runner):
        result = runner.invoke(cli, ["clients"])
        for client in ["cursor", "claude-desktop", "claude-code", "windsurf", "vscode", "opencode", "kilo", "codex"]:
            assert client in result.output

    def test_clients_shows_http_and_stdio_transports(self, runner):
        result = runner.invoke(cli, ["clients"])
        assert "http" in result.output
        assert "stdio" in result.output

    def test_clients_shows_dash_when_not_installed(self, runner, tmp_path):
        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=tmp_path / "none.json"):
            result = runner.invoke(cli, ["clients"])
        assert "—" in result.output

    def test_clients_shows_installed_when_configured(self, runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        cursor_config = tmp_path / "cursor_mcp.json"
        configure_client("cursor", config_path=cursor_config, backup=False, token=TOKEN)

        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=tmp_path / "none.json"):
            with mock.patch(
                "anaconda_mcp.client_config.get_client_config_path",
                side_effect=lambda client: cursor_config if client == "cursor" else tmp_path / f"{client}.none",
            ):
                result = runner.invoke(cli, ["clients"])

        lines = [line for line in result.output.splitlines() if "cursor" in line]
        assert lines, "cursor row not found"
        assert "yes" in lines[0]

    def test_clients_json_output(self, runner, tmp_path):
        with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=tmp_path / "none.json"):
            result = runner.invoke(cli, ["clients", "--json"])
        assert result.exit_code == 0
        data = json.loads(_strip_warning(result.output))
        assert data["codex"]["transport"] == "http"
        assert data["claude-desktop"]["transport"] == "stdio"
        assert data["codex"]["installed"] is False


class TestSetupWizard:
    @pytest.fixture
    def tty_runner(self):
        return CliRunner()

    def _tty(self):
        mock_sys = mock.MagicMock()
        mock_sys.stdin.isatty.return_value = True
        mock_sys.exit = __import__("sys").exit
        return mock.patch("anaconda_mcp.cli.sys", mock_sys)

    def test_non_tty_without_client_raises_usage_error(self, tty_runner):
        result = tty_runner.invoke(cli, ["setup"])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_wizard_configure_creates_config(self, tty_runner, tmp_path):
        cursor_config = tmp_path / "cursor_mcp.json"

        with self._tty():
            with mock.patch("anaconda_mcp.cli.multiselect_checkbox", return_value=["cursor"]):
                with mock.patch("anaconda_mcp.cli.is_client_installed", return_value=False):
                    with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=cursor_config):
                        result = tty_runner.invoke(cli, ["setup", "--no-backup"])

        assert result.exit_code == 0
        assert cursor_config.exists()
        entry = json.loads(cursor_config.read_text())["mcpServers"]["anaconda-mcp"]
        assert entry["url"] == MCP_URL

    def test_wizard_no_changes_exits_cleanly(self, tty_runner):
        with self._tty():
            with mock.patch("anaconda_mcp.cli.multiselect_checkbox", return_value=[]):
                with mock.patch("anaconda_mcp.cli.is_client_installed", return_value=False):
                    result = tty_runner.invoke(cli, ["setup", "--no-backup"])

        assert result.exit_code == 0
        assert "No changes" in result.output

    def test_wizard_keyboard_interrupt_aborts(self, tty_runner):
        with self._tty():
            with mock.patch("anaconda_mcp.cli.multiselect_checkbox", side_effect=KeyboardInterrupt):
                with mock.patch("anaconda_mcp.cli.is_client_installed", return_value=False):
                    result = tty_runner.invoke(cli, ["setup", "--no-backup"])
        assert result.exit_code != 0

    def test_wizard_pre_populates_installed_state(self, tty_runner):
        captured = {}

        def _fake_select(header, choices, checked=()):
            captured["checked"] = list(checked)
            return list(checked)

        def _installed(client, **kwargs):
            return client == "cursor"

        with self._tty():
            with mock.patch("anaconda_mcp.cli.multiselect_checkbox", side_effect=_fake_select):
                with mock.patch("anaconda_mcp.cli.is_client_installed", side_effect=_installed):
                    with mock.patch("anaconda_mcp.cli.client_needs_update", return_value=False):
                        tty_runner.invoke(cli, ["setup", "--no-backup"])

        assert captured["checked"] == ["cursor"]

    def test_wizard_remove_via_uncheck(self, tty_runner, tmp_path):
        from anaconda_mcp.client_config import configure_client

        cursor_config = tmp_path / "cursor_mcp.json"
        configure_client("cursor", config_path=cursor_config, backup=False, token=TOKEN)

        def _installed(client, **kwargs):
            return client == "cursor"

        with self._tty():
            with mock.patch("anaconda_mcp.cli.multiselect_checkbox", return_value=[]):
                with mock.patch("anaconda_mcp.cli.is_client_installed", side_effect=_installed):
                    with mock.patch("anaconda_mcp.client_config.get_client_config_path", return_value=cursor_config):
                        result = tty_runner.invoke(cli, ["setup", "--no-backup"])

        assert result.exit_code == 0
        assert "anaconda-mcp" not in json.loads(cursor_config.read_text()).get("mcpServers", {})

    def test_wizard_migrates_legacy_stdio_entry_when_kept_selected(self, tty_runner, tmp_path):
        cursor_config = tmp_path / "cursor_mcp.json"
        cursor_config.write_text('{"mcpServers": {"anaconda-mcp": {"command": "python", "args": []}}}')

        def _installed(client, **kwargs):
            return client == "cursor"

        def _fake_path(client):
            return cursor_config if client == "cursor" else tmp_path / f"{client}.json"

        with self._tty():
            with mock.patch("anaconda_mcp.cli.multiselect_checkbox", return_value=["cursor"]):
                with mock.patch("anaconda_mcp.cli.is_client_installed", side_effect=_installed):
                    with mock.patch("anaconda_mcp.client_config.get_client_config_path", side_effect=_fake_path):
                        result = tty_runner.invoke(cli, ["setup", "--no-backup"])

        assert result.exit_code == 0
        entry = json.loads(cursor_config.read_text())["mcpServers"]["anaconda-mcp"]
        assert entry["url"] == MCP_URL
        assert "command" not in entry


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

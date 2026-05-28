import json
from unittest import mock

from click.testing import CliRunner

from anaconda_mcp.mcp_state import is_new_install, mark_installed


def test_is_new_install_returns_true_when_no_file(tmp_path):
    fake_state = tmp_path / "mcp_state.json"
    with mock.patch("anaconda_mcp.mcp_state._STATE_PATH", fake_state):
        assert is_new_install() is True


def test_is_new_install_returns_false_when_valid_file(tmp_path):
    fake_state = tmp_path / "mcp_state.json"
    fake_state.write_text(json.dumps({"first_install_at": "2026-01-01T00:00:00"}))
    with mock.patch("anaconda_mcp.mcp_state._STATE_PATH", fake_state):
        assert is_new_install() is False


def test_is_new_install_returns_true_when_corrupt_file(tmp_path):
    fake_state = tmp_path / "mcp_state.json"
    fake_state.write_text("not json at all")
    with mock.patch("anaconda_mcp.mcp_state._STATE_PATH", fake_state):
        assert is_new_install() is True


def test_mark_installed_creates_file_with_timestamp(tmp_path):
    fake_state = tmp_path / "mcp_state.json"
    with mock.patch("anaconda_mcp.mcp_state._STATE_PATH", fake_state):
        mark_installed()
    data = json.loads(fake_state.read_text())
    assert "first_install_at" in data
    assert isinstance(data["first_install_at"], str)
    assert len(data["first_install_at"]) > 0


def test_mark_installed_handles_permission_error(tmp_path):
    fake_state = tmp_path / "nonexistent" / "deep" / "mcp_state.json"
    with mock.patch("anaconda_mcp.mcp_state._STATE_PATH", fake_state):
        with mock.patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            mark_installed()


def test_setup_emits_install_completed_event():
    from anaconda_mcp.cli import cli

    runner = CliRunner()
    with (
        mock.patch("anaconda_mcp.cli.configure_client") as mock_configure,
        mock.patch("anaconda_mcp.cli.is_new_install", return_value=True),
        mock.patch("anaconda_mcp.cli.mark_installed"),
        mock.patch("anaconda_mcp.cli.SnakeEyes") as mock_snake_eyes,
        mock.patch("anaconda_mcp.cli.get_auth_token", return_value="fake-token"),
    ):
        mock_configure.return_value = {
            "config_path": "/tmp/test",
            "backup_path": None,
            "server_name": "anaconda-mcp",
            "scope": "global",
            "created": True,
            "updated": False,
        }
        result = runner.invoke(cli, ["setup", "--client", "claude-desktop"])
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        send_mock = mock_snake_eyes.return_value.send
        assert send_mock.called, "SnakeEyes.send was never called"
        found = False
        for call in send_mock.call_args_list:
            metric_data = call[0][0] if call[0] else call[1].get("metric_data")
            if metric_data and metric_data.event == "anaconda_mcp_install_completed":
                assert metric_data.event_params == {"new_install": True}
                assert call[1].get("blocking") is True
                found = True
                break
        assert found, f"INSTALL_COMPLETED event not found in calls: {send_mock.call_args_list}"

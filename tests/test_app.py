from unittest import mock

import pytest
import typer
from typer.testing import CliRunner

from anaconda_mcp.app import _forward_to_click, app


@pytest.fixture
def runner():
    return CliRunner()


class TestSubcommandForwarding:
    """Each app subcommand should forward its name + any extra args to Click."""

    @pytest.mark.parametrize("subcommand", ["serve", "compose", "discover", "clients", "setup", "remove"])
    def test_subcommand_forwards_to_click(self, runner, subcommand):
        with mock.patch("anaconda_mcp.app._forward_to_click") as mock_fwd:
            runner.invoke(app, [subcommand])
        mock_fwd.assert_called_once_with([subcommand])

    @pytest.mark.parametrize(
        "subcommand,extra_args",
        [
            ("serve", ["--port", "9000"]),
            ("setup", ["--client", "cursor", "--no-backup"]),
        ],
    )
    def test_extra_args_are_passed_through(self, runner, subcommand, extra_args):
        with mock.patch("anaconda_mcp.app._forward_to_click") as mock_fwd:
            runner.invoke(app, [subcommand] + extra_args)
        mock_fwd.assert_called_once_with([subcommand] + extra_args)


class TestForwardToClick:
    """_forward_to_click error handling — the one piece of logic in app.py."""

    def test_nonzero_exit_raises_typer_exit(self):
        with mock.patch("anaconda_mcp.app.click_cli.main", side_effect=SystemExit(1)):
            with pytest.raises(typer.Exit) as exc_info:
                _forward_to_click(["serve"])
        assert exc_info.value.exit_code == 1

    def test_zero_exit_does_not_raise(self):
        with mock.patch("anaconda_mcp.app.click_cli.main", side_effect=SystemExit(0)):
            _forward_to_click(["serve"])  # Should not raise

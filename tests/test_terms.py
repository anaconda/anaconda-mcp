import click
import pytest
from anaconda_cli_base.config import AnacondaConfigTomlSettingsSource
from click.testing import CliRunner

from anaconda_mcp.cli import cli
from anaconda_mcp.config import Settings
from anaconda_mcp.terms import check_terms_accepted, persist_acceptance


@pytest.fixture
def config_toml(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("ANACONDA_CONFIG_TOML", str(config_file))
    yield config_file


@pytest.fixture
def fresh_settings(config_toml):
    def _make():
        AnacondaConfigTomlSettingsSource._cache.clear()
        return Settings()

    return _make


class TestCheckTermsAccepted:
    def test_accepted_terms_true_passes_through(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", True)
        ctx = click.Context(click.Command("serve"))
        check_terms_accepted(ctx)

    def test_accepted_terms_false_exits(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", False)
        ctx = click.Context(click.Command("serve"))
        with pytest.raises(SystemExit) as exc_info:
            check_terms_accepted(ctx)
        assert exc_info.value.code == 1

    def test_accepted_terms_none_prompts_and_accepts(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("anaconda_mcp.terms.Confirm.ask", lambda *a, **kw: True)
        monkeypatch.setattr("anaconda_mcp.terms.persist_acceptance", lambda v: None)
        ctx = click.Context(click.Command("serve"))
        check_terms_accepted(ctx)

    def test_accepted_terms_none_prompts_and_declines(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("anaconda_mcp.terms.Confirm.ask", lambda *a, **kw: False)
        monkeypatch.setattr("anaconda_mcp.terms.persist_acceptance", lambda v: None)
        ctx = click.Context(click.Command("serve"))
        with pytest.raises(SystemExit) as exc_info:
            check_terms_accepted(ctx)
        assert exc_info.value.code == 1

    def test_non_tty_without_acceptance_exits(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
        monkeypatch.setattr("sys.stdout.isatty", lambda: False)
        ctx = click.Context(click.Command("serve"))
        with pytest.raises(SystemExit) as exc_info:
            check_terms_accepted(ctx)
        assert exc_info.value.code == 1

    def test_help_flag_bypasses_gate(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
        monkeypatch.setattr("sys.argv", ["anaconda-mcp", "serve", "--help"])
        ctx = click.Context(click.Command("serve"))
        check_terms_accepted(ctx)

    def test_short_help_flag_bypasses_gate(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
        monkeypatch.setattr("sys.argv", ["anaconda-mcp", "serve", "-h"])
        ctx = click.Context(click.Command("serve"))
        check_terms_accepted(ctx)

    def test_resilient_parsing_bypasses_gate(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
        ctx = click.Context(click.Command("serve"), resilient_parsing=True)
        check_terms_accepted(ctx)

    def test_terms_subcommand_bypasses_gate(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
        ctx = click.Context(click.Group("cli"))
        ctx.invoked_subcommand = "terms"
        check_terms_accepted(ctx)


class TestPersistAcceptance:
    def test_persist_writes_true_to_config_toml(self, config_toml, fresh_settings):
        persist_acceptance(True)
        s = fresh_settings()
        assert s.accepted_terms is True

    def test_persist_writes_false_to_config_toml(self, config_toml, fresh_settings):
        persist_acceptance(False)
        s = fresh_settings()
        assert s.accepted_terms is False

    def test_config_toml_contains_accepted_terms(self, config_toml):
        persist_acceptance(True)
        content = config_toml.read_text()
        assert "accepted_terms = true" in content


class TestTermsStatusCommand:
    def test_status_accepted(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", True)
        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "status"])
        assert result.exit_code == 0
        assert "accepted" in result.output

    def test_status_declined(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", False)
        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "status"])
        assert result.exit_code == 1
        assert "declined" in result.output

    def test_status_not_responded(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", None)
        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "status"])
        assert result.exit_code == 1
        assert "not yet responded" in result.output


class TestTermsAcceptCommand:
    def test_accept_persists(self, config_toml, monkeypatch, fresh_settings):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", None)
        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "accept"])
        assert result.exit_code == 0
        assert "accepted" in result.output
        s = fresh_settings()
        assert s.accepted_terms is True

    def test_accept_already_accepted(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", True)
        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "accept"])
        assert result.exit_code == 0
        assert "already" in result.output


class TestTermsGroupBareInvocation:
    def test_bare_terms_shows_terms_text(self, monkeypatch):
        runner = CliRunner()
        result = runner.invoke(cli, ["terms"])
        assert result.exit_code == 0
        assert "Terms of Service" in result.output

import json
from unittest.mock import MagicMock

import click
import pytest
from anaconda_cli_base.config import AnacondaConfigTomlSettingsSource
from click.testing import CliRunner

from anaconda_mcp.cli import cli
from anaconda_mcp.config import Settings
from anaconda_mcp.terms import (
    CURRENT_TOS_VERSION,
    TermsError,
    _prompt_contact_consent,
    check_terms_accepted,
    is_terms_current,
    persist_acceptance,
    send_contact_consent_event,
)


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


@pytest.fixture
def no_terms(monkeypatch):
    monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
    monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms_version", None)


class TestCheckTermsAccepted:
    def test_accepted_terms_true_passes_through(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", True)
        ctx = click.Context(click.Command("serve"))
        check_terms_accepted(ctx)

    def test_accepted_terms_none_prompts_and_accepts(self, monkeypatch, no_terms):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("anaconda_mcp.terms.Confirm.ask", lambda *a, **kw: True)
        monkeypatch.setattr("anaconda_mcp.terms.persist_acceptance", lambda v: None)
        monkeypatch.setattr("anaconda_mcp.terms._prompt_contact_consent", lambda: None)
        ctx = click.Context(click.Command("serve"))
        check_terms_accepted(ctx)

    def test_accepted_terms_none_prompts_and_declines(self, monkeypatch, no_terms):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        monkeypatch.setattr("anaconda_mcp.terms.Confirm.ask", lambda *a, **kw: False)
        monkeypatch.setattr("anaconda_mcp.terms.persist_acceptance", lambda v: None)
        ctx = click.Context(click.Command("serve"))
        with pytest.raises(TermsError) as exc_info:
            check_terms_accepted(ctx)
        assert exc_info.value.check_name == "terms"

    def test_non_tty_without_acceptance_exits(self, monkeypatch, no_terms):
        monkeypatch.setattr("sys.stdout.isatty", lambda: False)
        ctx = click.Context(click.Command("serve"))
        with pytest.raises(TermsError) as exc_info:
            check_terms_accepted(ctx)
        assert exc_info.value.check_name == "terms"

    @pytest.mark.parametrize(
        "argv",
        [
            ["anaconda-mcp", "serve", "--help"],
            ["anaconda-mcp", "serve", "-h"],
        ],
    )
    def test_help_flags_bypass_gate(self, monkeypatch, no_terms, argv):
        monkeypatch.setattr("sys.argv", argv)
        ctx = click.Context(click.Command("serve"))
        check_terms_accepted(ctx)

    def test_resilient_parsing_bypasses_gate(self, monkeypatch, no_terms):
        ctx = click.Context(click.Command("serve"), resilient_parsing=True)
        check_terms_accepted(ctx)

    def test_terms_subcommand_bypasses_gate(self, monkeypatch, no_terms):
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
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms_version", CURRENT_TOS_VERSION)
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

    def test_status_needs_reaccept(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", True)
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms_version", "2025-01-01")
        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "status"])
        assert result.exit_code == 1
        assert "re-accept" in result.output
        assert "2025-01-01" in result.output
        assert CURRENT_TOS_VERSION in result.output


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


class TestVersionedAcceptance:
    def test_current_version_accepted_passes(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", True)
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms_version", CURRENT_TOS_VERSION)
        ctx = click.Context(click.Command("serve"))
        check_terms_accepted(ctx)

    def test_version_only_without_accepted_terms_raises(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms", None)
        monkeypatch.setattr("anaconda_mcp.terms.settings.accepted_terms_version", CURRENT_TOS_VERSION)
        monkeypatch.setattr("sys.stdout.isatty", lambda: False)
        ctx = click.Context(click.Command("serve"))
        with pytest.raises(TermsError):
            check_terms_accepted(ctx)

    def test_none_version_none_accepted_non_tty_raises(self, monkeypatch, no_terms):
        monkeypatch.setattr("sys.stdout.isatty", lambda: False)
        ctx = click.Context(click.Command("serve"))
        with pytest.raises(TermsError) as exc_info:
            check_terms_accepted(ctx)
        assert exc_info.value.check_name == "terms"

    def test_persist_acceptance_writes_version(self, config_toml, fresh_settings):
        persist_acceptance(True)
        s = fresh_settings()
        assert s.accepted_terms_version == CURRENT_TOS_VERSION

    def test_persist_decline_clears_version(self, config_toml, fresh_settings):
        persist_acceptance(False)
        s = fresh_settings()
        assert s.accepted_terms_version is None

    @pytest.mark.parametrize(
        "version,expected",
        [
            (None, False),
            (CURRENT_TOS_VERSION, True),
            ("2020-01-01", False),
            ("not-a-date", False),
        ],
    )
    def test_is_terms_current(self, version, expected):
        assert is_terms_current(version) is expected


class TestServePrerequisiteFailure:
    def test_serve_without_tos_exits_78(self, monkeypatch, no_terms):
        runner = CliRunner()
        result = runner.invoke(cli, ["serve"], catch_exceptions=False)
        assert result.exit_code == 78
        assert "anaconda mcp terms accept" in result.output


class TestTermsJsonOutput:
    @pytest.mark.parametrize(
        "accepted_terms,accepted_version,expected_exit,expected_accepted",
        [
            (True, CURRENT_TOS_VERSION, 0, True),
            (True, "2025-01-01", 1, True),  # accepted but stale version
            (None, None, 1, False),
            (False, None, 1, False),
        ],
    )
    def test_status_json(self, monkeypatch, accepted_terms, accepted_version, expected_exit, expected_accepted):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", accepted_terms)
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms_version", accepted_version)
        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "status", "--json"])
        assert result.exit_code == expected_exit
        data = json.loads(result.output)
        assert data["accepted"] is expected_accepted
        assert data["current_version"] == CURRENT_TOS_VERSION

    @pytest.mark.parametrize(
        "accepted_terms,accepted_version,expected_previously",
        [
            (None, None, False),
            (True, CURRENT_TOS_VERSION, True),
        ],
    )
    def test_accept_json(self, monkeypatch, config_toml, accepted_terms, accepted_version, expected_previously):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", accepted_terms)
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms_version", accepted_version)
        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "accept", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["accepted"] is True
        assert data["previously_accepted"] is expected_previously


class TestTermsAcceptConsent:
    def test_accept_with_consent_sends_event(self, config_toml, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", None)
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)
        monkeypatch.setattr("anaconda_mcp.cli.get_auth_token", lambda: "fake-token")

        mock_client_instance = MagicMock()
        mock_client_instance.account = {"user": {"email": "user@example.com", "id": "abc-123"}}
        monkeypatch.setattr("anaconda_mcp.terms.BaseClient", lambda **kw: mock_client_instance)

        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "accept", "--consent"])
        assert result.exit_code == 0
        mock_send.assert_called_once()
        metric_data = mock_send.call_args[0][0]
        assert metric_data.event == "anaconda_mcp_contact_consent"
        assert metric_data.event_params["contact"] is True

    def test_accept_without_consent_does_not_send_event(self, config_toml, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", None)
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)

        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "accept"])
        assert result.exit_code == 0
        mock_send.assert_not_called()

    def test_accept_with_no_consent_flag_does_not_send_event(self, config_toml, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.config.settings.accepted_terms", None)
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)

        runner = CliRunner()
        result = runner.invoke(cli, ["terms", "accept", "--no-consent"])
        assert result.exit_code == 0
        mock_send.assert_not_called()


class TestSendContactConsentEvent:
    def test_sends_telemetry_with_email_and_uuid(self, monkeypatch):
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)

        mock_client_instance = MagicMock()
        mock_client_instance.account = {"user": {"email": "user@example.com", "id": "abc-123"}}
        monkeypatch.setattr("anaconda_mcp.terms.BaseClient", lambda **kw: mock_client_instance)

        send_contact_consent_event("fake-token")

        mock_send.assert_called_once()
        metric_data = mock_send.call_args[0][0]
        assert metric_data.event == "anaconda_mcp_contact_consent"
        assert metric_data.event_params["contact"] is True
        assert metric_data.event_params["email"] == "user@example.com"
        assert metric_data.event_params["uuid"] == "abc-123"
        # bearer_token now comes from the handler's bearer_token_fn (configured by
        # conftest's autouse fixture to MOCKED_TOKEN), NOT from the function arg.
        # The "fake-token" arg is only used for BaseClient(api_key=...).
        assert mock_send.call_args[1]["bearer_token"] == "mocked_token"

    def test_handles_account_fetch_failure(self, monkeypatch):
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)
        monkeypatch.setattr(
            "anaconda_mcp.terms.BaseClient",
            MagicMock(side_effect=Exception("network error")),
        )

        send_contact_consent_event("fake-token")

        mock_send.assert_called_once()
        metric_data = mock_send.call_args[0][0]
        assert metric_data.event_params["contact"] is True
        assert "uuid" not in metric_data.event_params
        assert "email" not in metric_data.event_params


class TestPromptContactConsent:
    def test_consent_yes_with_existing_token_sends_event(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.Confirm.ask", lambda *a, **kw: True)
        monkeypatch.setattr("anaconda_mcp.terms.get_auth_token", lambda: "fake-token")
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)

        mock_client_instance = MagicMock()
        mock_client_instance.account = {"user": {"email": "user@example.com", "id": "abc-123"}}
        monkeypatch.setattr("anaconda_mcp.terms.BaseClient", lambda **kw: mock_client_instance)

        _prompt_contact_consent()

        mock_send.assert_called_once()

    def test_consent_no_does_not_send_event(self, monkeypatch):
        monkeypatch.setattr("anaconda_mcp.terms.Confirm.ask", lambda *a, **kw: False)
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)

        _prompt_contact_consent()

        mock_send.assert_not_called()

    def test_consent_yes_no_token_prompts_login_and_sends(self, monkeypatch):
        ask_responses = iter([True, True])
        monkeypatch.setattr("anaconda_mcp.terms.Confirm.ask", lambda *a, **kw: next(ask_responses))
        token_responses = iter([None, "new-token"])
        monkeypatch.setattr("anaconda_mcp.terms.get_auth_token", lambda: next(token_responses))
        monkeypatch.setattr("anaconda_mcp.terms.login", lambda: None)
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)

        mock_client_instance = MagicMock()
        mock_client_instance.account = {"user": {"email": "user@example.com", "id": "abc-123"}}
        monkeypatch.setattr("anaconda_mcp.terms.BaseClient", lambda **kw: mock_client_instance)

        _prompt_contact_consent()

        mock_send.assert_called_once()

    def test_consent_yes_no_token_declines_login_exits(self, monkeypatch):
        ask_responses = iter([True, False])
        monkeypatch.setattr("anaconda_mcp.terms.Confirm.ask", lambda *a, **kw: next(ask_responses))
        monkeypatch.setattr("anaconda_mcp.terms.get_auth_token", lambda: None)
        mock_send = MagicMock()
        monkeypatch.setattr("anaconda_mcp.telemetry.SnakeEyes.send", mock_send)

        with pytest.raises(SystemExit):
            _prompt_contact_consent()

        mock_send.assert_not_called()

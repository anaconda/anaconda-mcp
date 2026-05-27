import logging
import sys
from collections.abc import Callable
from textwrap import dedent

import click
from anaconda_auth.actions import login
from anaconda_auth.client import BaseClient
from anaconda_cli_base.config import anaconda_config_path
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm
from rich.syntax import Syntax

from anaconda_mcp.auth import get_auth_token
from anaconda_mcp.config import settings
from anaconda_mcp.telemetry import MetricData, MetricNames, SnakeEyes

logger = logging.getLogger(__name__)


class TermsError(Exception):
    """Raised when Terms of Service check fails."""

    def __init__(self, check_name: str, message: str, remediation: str) -> None:
        self.check_name = check_name
        self.message = message
        self.remediation = remediation
        super().__init__(f"{check_name}: {message}")


TERMS_OF_SERVICE = dedent("""\
    # Anaconda MCP Terms of Service
    Anaconda MCP is a beta product covered by Beta Terms

    https://www.anaconda.com/legal/terms/mcpbeta

    By entering 'y' below, I agree to the Beta Terms. To the extent
    these terms differ from any other agreement with Anaconda,
    these Beta Terms control.

    This product is not intended for production use.
    """)

CURRENT_TOS_VERSION = "2026-05-19"


def is_terms_current(accepted_version: str | None) -> bool:
    """Check if the accepted TOS version matches the current version."""
    return accepted_version == CURRENT_TOS_VERSION


def verify_terms_accepted() -> None:
    """Raise TermsError if terms are not accepted. No TTY interaction."""
    if settings.accepted_terms is True and is_terms_current(settings.accepted_terms_version):
        return
    raise TermsError(
        check_name="terms",
        message="You must accept the Anaconda MCP Terms of Service.",
        remediation=f"Run 'anaconda mcp terms accept' or set ANACONDA_MCP_ACCEPTED_TERMS=true ANACONDA_MCP_ACCEPTED_TERMS_VERSION={CURRENT_TOS_VERSION}.",
    )


def check_terms_accepted(ctx: click.Context) -> None:
    if ctx.resilient_parsing:
        return
    if any(flag in sys.argv for flag in ("--help", "-h")):
        return
    if ctx.invoked_subcommand == "terms":
        return

    try:
        verify_terms_accepted()
    except TermsError:
        if not sys.stdout.isatty():
            raise

        console = Console()
        console.print(Markdown(TERMS_OF_SERVICE))
        console.print()
        accepted = Confirm.ask("[bold]Do you accept the Beta Terms?[/bold]")
        persist_acceptance(accepted)

        if not accepted:
            raise TermsError(
                check_name="terms",
                message="Terms of Service declined.",
                remediation="Run 'anaconda mcp terms accept' to accept later.",
            ) from None

        _prompt_contact_consent()


def send_contact_consent_event(token: str) -> None:
    try:
        email = None
        uuid = None
        try:
            client = BaseClient(api_key=token, domain=settings.anaconda_domain)
            user = client.account["user"]
            email = user.get("email")
            uuid = user.get("id")
        except Exception:
            logger.debug("Could not retrieve user account for contact consent", exc_info=True)

        event_params: dict[str, object] = {"contact": True}
        if uuid:
            event_params["uuid"] = uuid
        if email:
            event_params["email"] = email

        SnakeEyes().send(
            MetricData(
                event=MetricNames.CONTACT_CONSENT.value,
                event_params=event_params,
            ),
            bearer_token=token,
        )
    except Exception:
        logger.debug("Failed to send contact consent event", exc_info=True)


def _prompt_contact_consent() -> None:
    console = Console()
    console.print()
    contact = Confirm.ask("[bold]I agree to be contacted directly to share feedback[/bold]")
    if not contact:
        return

    token = get_auth_token()
    if not token:
        token = _ensure_login(console)
    if not token:
        return

    send_contact_consent_event(token)


def _ensure_login(console: Console) -> str | None:
    do_login = Confirm.ask("Continue with interactive login?", choices=["y", "n"])
    if do_login:
        login()
        token: str | None = get_auth_token()
        return token

    console.print(
        dedent("""
        To configure your credentials you can run
          [green]anaconda login --at anaconda.com[/green]

        or set your API key using the [green]ANACONDA_AUTH_API_KEY[/green] env var

        or set
        """)
    )
    console.print(
        Syntax(
            dedent("""\
                [plugin.auth]
                api_key = "<api-key>"
                """),
            "toml",
            background_color=None,
        )
    )
    console.print(f"in {anaconda_config_path()}")
    raise SystemExit(1)


def persist_acceptance(accepted: bool) -> None:
    settings.accepted_terms = accepted
    if accepted:
        settings.accepted_terms_version = CURRENT_TOS_VERSION
    else:
        settings.accepted_terms_version = None
    settings.write_config()


def make_terms_enforcement_hook() -> Callable:
    def hook(original_call_tool: Callable) -> Callable:
        async def _enforced(self, name, arguments, context=None, convert_result=False):
            verify_terms_accepted()
            return await original_call_tool(self, name, arguments, context=context, convert_result=convert_result)

        return _enforced

    return hook

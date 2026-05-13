import sys
from textwrap import dedent

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm

from anaconda_mcp.config import settings


class TermsError(Exception):
    """Raised when Terms of Service check fails."""

    def __init__(self, check_name: str, message: str, remediation: str) -> None:
        self.check_name = check_name
        self.message = message
        self.remediation = remediation
        super().__init__(f"{check_name}: {message}")


TERMS_OF_SERVICE = dedent("""\
    # Anaconda MCP Terms of Service
    This MCP is beta

    """)

CURRENT_TOS_VERSION = "2026-01-01"


def is_terms_current(accepted_version: str | None) -> bool:
    """Check if the accepted TOS version matches the current version."""
    return accepted_version == CURRENT_TOS_VERSION


def check_terms_accepted(ctx: click.Context) -> None:
    if ctx.resilient_parsing:
        return
    if any(flag in sys.argv for flag in ("--help", "-h")):
        return
    if ctx.invoked_subcommand == "terms":
        return

    if settings.accepted_terms is False:
        raise TermsError(
            check_name="terms",
            message="You previously declined the Anaconda MCP Terms of Service.",
            remediation="Run 'anaconda mcp terms accept' or set ANACONDA_MCP_ACCEPTED_TERMS=true.",
        )

    if is_terms_current(settings.accepted_terms_version):
        return

    if settings.accepted_terms is True:
        # Backward compat: accepted under old schema without version tracking.
        # Re-acceptance enforcement happens at the CLI/plugin layer via `needs_reaccept`.
        return

    if not sys.stdout.isatty():
        raise TermsError(
            check_name="terms",
            message="You must accept the Anaconda MCP Terms of Service.",
            remediation="Run 'anaconda mcp terms accept' or set ANACONDA_MCP_ACCEPTED_TERMS=true.",
        )

    console = Console()
    console.print(Markdown(TERMS_OF_SERVICE))
    accepted = Confirm.ask("[bold]Do you accept the Terms of Service?[/bold]")
    persist_acceptance(accepted)

    if not accepted:
        raise TermsError(
            check_name="terms",
            message="Terms of Service declined.",
            remediation="Run 'anaconda mcp terms accept' to accept later.",
        )


def persist_acceptance(accepted: bool) -> None:
    settings.accepted_terms = accepted
    if accepted:
        settings.accepted_terms_version = CURRENT_TOS_VERSION
    else:
        settings.accepted_terms_version = None
    settings.write_config()

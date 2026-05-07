import sys
from textwrap import dedent

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm

from anaconda_mcp.config import settings

TERMS_OF_SERVICE = dedent("""\
    # Anaconda MCP Terms of Service
    This MCP is beta

    """)


def check_terms_accepted(ctx: click.Context) -> None:
    if ctx.resilient_parsing:
        return
    if any(flag in sys.argv for flag in ("--help", "-h")):
        return
    if ctx.invoked_subcommand == "terms":
        return

    if settings.accepted_terms is True:
        return

    if settings.accepted_terms is False:
        click.echo(
            "Error: You previously declined the Anaconda MCP Terms of Service.\n"
            "Run 'anaconda mcp terms accept' or set ANACONDA_MCP_ACCEPTED_TERMS=true.",
            err=True,
        )
        sys.exit(1)

    if not sys.stdout.isatty():
        click.echo(
            "Error: You must accept the Anaconda MCP Terms of Service.\n"
            "Run 'anaconda mcp terms accept' or set ANACONDA_MCP_ACCEPTED_TERMS=true.",
            err=True,
        )
        sys.exit(1)

    console = Console()
    console.print(Markdown(TERMS_OF_SERVICE))
    accepted = Confirm.ask("[bold]Do you accept the Terms of Service?[/bold]")
    persist_acceptance(accepted)

    if not accepted:
        sys.exit(1)


def persist_acceptance(accepted: bool) -> None:
    settings.accepted_terms = accepted
    settings.write_config()

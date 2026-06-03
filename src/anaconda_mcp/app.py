"""Typer-based subcommand for anaconda-cli-base integration.

This module provides a Typer app that wraps the existing Click CLI,
allowing registration as an `anaconda mcp` subcommand.
"""

import io
from textwrap import dedent

import typer
from rich.console import Console
from rich.text import Text

from anaconda_mcp.cli import cli as click_cli


def _render_rich_markup(markup: str) -> str:
    """Pre-render Rich markup to ANSI escape sequences.

    Workaround for anaconda-cli-base not propagating rich_markup_mode
    to child Typer apps. Once anaconda-cli-base sets rich_markup_mode="rich"
    on its root app, this can be reverted to plain markup strings.
    """
    buf = io.StringIO()
    console = Console(file=buf, highlight=False, no_color=False, force_terminal=True)
    text = Text.from_markup(markup)
    console.print(text, end="")
    return buf.getvalue()


# Remove extra \n after https://github.com/fastapi/typer/pull/1405 is released
EPILOG = _render_rich_markup(
    dedent(
        """\
        Full documentation at → [bold green]https://www.anaconda.com/docs/cli-reference/anaconda-mcp/getting-started[/]
        \nSubmit feedback at → [bold green]https://anaconda.canny.io/anaconda-mcp-beta[/]"""
    )
)

app = typer.Typer(
    name="mcp",
    help="Anaconda MCP — Model Context Protocol tools for AI assistants.",
    rich_markup_mode="rich",
    add_completion=False,
    no_args_is_help=True,
    context_settings={
        "help_option_names": ["-h", "--help"],
    },
)


@app.callback(invoke_without_command=True, epilog=EPILOG)
def main(
    ctx: typer.Context,
):
    """Anaconda MCP — Model Context Protocol tools for AI assistants."""
    ctx.ensure_object(dict)


def _forward_to_click(args: list[str]) -> None:
    try:
        click_cli.main(args, standalone_mode=True)
    except SystemExit as e:
        if e.code:
            raise typer.Exit(code=int(e.code)) from e


@app.command(
    "serve",
    add_help_option=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def serve(ctx: typer.Context):
    """Start MCP servers from configuration file."""
    _forward_to_click(["serve"] + ctx.args)


@app.command(
    "clients",
    add_help_option=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def clients(ctx: typer.Context):
    """List supported AI clients and their configuration options."""
    _forward_to_click(["clients"] + ctx.args)


@app.command(
    "setup",
    add_help_option=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def setup(ctx: typer.Context):
    """Configure AI clients to use Anaconda MCP."""
    _forward_to_click(["setup"] + ctx.args)


@app.command(
    "remove",
    add_help_option=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def remove(ctx: typer.Context):
    """Remove Anaconda MCP from AI client configurations."""
    _forward_to_click(["remove"] + ctx.args)


@app.command(
    "terms",
    add_help_option=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def terms(ctx: typer.Context):
    """Manage Terms of Service acceptance."""
    _forward_to_click(["terms"] + ctx.args)


if __name__ == "__main__":
    app()

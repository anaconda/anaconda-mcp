"""Typer-based subcommand for anaconda-cli-base integration.

This module provides a Typer app that wraps the existing Click CLI,
allowing registration as an `anaconda mcp` subcommand.
"""

import typer

from anaconda_mcp.cli import cli as click_cli

app = typer.Typer(
    name="mcp",
    help="Anaconda MCP — Model Context Protocol tools for AI assistants.",
    add_completion=False,
    no_args_is_help=True,
    context_settings={
        "help_option_names": ["-h", "--help"],
    },
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose logging."),
):
    """Anaconda MCP — Model Context Protocol tools for AI assistants."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if ctx.invoked_subcommand is None:
        click_cli.main(["--help"], standalone_mode=False)


def _forward_to_click(args: list[str]) -> None:
    try:
        click_cli.main(args, standalone_mode=True)
    except SystemExit as e:
        if e.code:
            raise typer.Exit(code=e.code) from e


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


if __name__ == "__main__":
    app()

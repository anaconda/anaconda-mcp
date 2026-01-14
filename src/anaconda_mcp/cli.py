import sys
import os
import types
from pathlib import Path

import click

from mcp_compose.cli import (
    setup_logging,
    compose_command as _compose,
    discover_command as _discover,
    serve_command as _serve,
)
from mcp_compose.composer import ConflictResolution


def _ns(**kwargs):
    """Small helper to create an argparse-like namespace."""
    return types.SimpleNamespace(**kwargs)


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging.")
@click.pass_context
def cli(ctx, verbose: bool):
    """Anaconda MCP wrapper — forwards to mcp-compose."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@cli.command(help="Start MCP servers from configuration file.")
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=False, dir_okay=False),
    help="Path to mcp_compose.toml file (default: src/anaconda_mcp/mcp_compose.toml)",
)
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind to.")
@click.option("--port", default=8000, show_default=True, type=int, help="Port to bind to.")
@click.option(
    "--enable-auth-token-fallback/--no-enable-auth-token-fallback",
    default=True,
    show_default=True,
    help="Fallback to the local auth token",
)
@click.pass_context
def serve(ctx, config, host, port, enable_auth_token_fallback):
    if not config:
        default_path = Path(__file__).resolve().parent / "mcp_compose.toml"
        if default_path.exists():
            config = str(default_path)
        else:
            click.echo(
                f"⚠️ No configuration file found. Expected at {default_path} or provide --config.",
                err=True,
            )
            sys.exit(1)
    
    ns = _ns(verbose=ctx.obj["verbose"], config=config, host=host, port=port)
    
    env_var = "MCP_COMPOSE_ANACONDA_TOKEN"
    had_value = env_var in os.environ
    old_value = os.environ.get(env_var)
    
    if enable_auth_token_fallback:
        os.environ[env_var] = "fallback"
    
    try:
        exit_code = _serve(ns)
    finally:
        if enable_auth_token_fallback:
            if had_value:
                os.environ[env_var] = old_value
            else:
                os.environ.pop(env_var, None)
    
    sys.exit(exit_code)


@click.option(
    "-p", "--pyproject",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to pyproject.toml (default: ./pyproject.toml)"
)
@click.option(
    "-n", "--name",
    default="composed-mcp-server",
    show_default=True,
    help="Name for the composed server."
)
@click.option(
    "-c", "--conflict-resolution",
    type=click.Choice([cr.value for cr in ConflictResolution]),
    default=ConflictResolution.PREFIX.value,
    show_default=True,
    help="Naming conflict strategy."
)
@click.option("--include", multiple=True, help="Include only specified servers (repeatable).")
@click.option("--exclude", multiple=True, help="Exclude specified servers (repeatable).")
@click.option("-o", "--output", type=click.Path(dir_okay=False), help="Write composed server metadata to a file.")
@click.option(
    "--output-format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format."
)
@click.pass_context
@cli.command(help="Compose MCP servers from dependencies.")
def compose(ctx, pyproject, name, conflict_resolution, include, exclude, output, output_format):
    ns = _ns(
        verbose=ctx.obj["verbose"],
        pyproject=pyproject,
        name=name,
        conflict_resolution=conflict_resolution,
        include=list(include) if include else None,
        exclude=list(exclude) if exclude else None,
        output=output,
        output_format=output_format,
    )
    code = _compose(ns)
    sys.exit(code)


@cli.command(help="Discover MCP servers from dependencies.")
@click.option(
    "-p", "--pyproject",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to pyproject.toml (default: ./pyproject.toml)"
)
@click.option(
    "--output-format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format."
)
@click.pass_context
def discover(ctx, pyproject, output_format):
    ns = _ns(
        verbose=ctx.obj["verbose"],
        pyproject=pyproject,
        output_format=output_format,
    )
    code = _discover(ns)
    sys.exit(code)


def main():
    cli(obj={})  # entry point

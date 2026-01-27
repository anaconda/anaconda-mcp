import argparse
import json
import sys
from pathlib import Path

import click
from mcp_compose.cli import (
    compose_command as _compose,
)
from mcp_compose.cli import (
    discover_command as _discover,
)
from mcp_compose.cli import (
    serve_command as _serve,
)
from mcp_compose.cli import (
    setup_logging,
)
from mcp_compose.composer import ConflictResolution

from anaconda_mcp.auth import start_login
from anaconda_mcp.claude_desktop import (
    configure_claude_desktop,
    get_claude_desktop_config_path,
    remove_claude_desktop_config,
    show_claude_desktop_config,
)


def _ns(**kwargs):
    """Small helper to create an argparse-like namespace."""
    return argparse.Namespace(**kwargs)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
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
@click.pass_context
def serve(ctx, config, host, port):
    if not config:
        default_path = Path(__file__).resolve().parent / "mcp_compose.toml"
        if default_path.exists():
            config = str(default_path)
        else:
            click.echo(
                f"⚠️  No configuration file found. Expected at {default_path} or provide --config.",
                err=True,
            )
            sys.exit(1)
    start_login(lambda x: x)
    ns = _ns(verbose=ctx.obj["verbose"], config=config, host=host, port=port)
    sys.exit(_serve(ns))


@click.option(
    "-p",
    "--pyproject",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to pyproject.toml (default: ./pyproject.toml)",
)
@click.option("-n", "--name", default="composed-mcp-server", show_default=True, help="Name for the composed server.")
@click.option(
    "-c",
    "--conflict-resolution",
    type=click.Choice([cr.value for cr in ConflictResolution]),
    default=ConflictResolution.PREFIX.value,
    show_default=True,
    help="Naming conflict strategy.",
)
@click.option("--include", multiple=True, help="Include only specified servers (repeatable).")
@click.option("--exclude", multiple=True, help="Exclude specified servers (repeatable).")
@click.option("-o", "--output", type=click.Path(dir_okay=False), help="Write composed server metadata to a file.")
@click.option(
    "--output-format", type=click.Choice(["text", "json"]), default="text", show_default=True, help="Output format."
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
    "-p",
    "--pyproject",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to pyproject.toml (default: ./pyproject.toml)",
)
@click.option(
    "--output-format", type=click.Choice(["text", "json"]), default="text", show_default=True, help="Output format."
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


# ============================================================================
# Claude Desktop Configuration Commands
# ============================================================================


@cli.group(help="Configure Claude Desktop integration.")
def claude():
    """Manage Claude Desktop configuration for Anaconda MCP."""
    pass


@claude.command(name="install", help="Add Anaconda MCP to Claude Desktop configuration.")
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False),
    help="Path to Claude Desktop config file (auto-detected by default).",
)
@click.option(
    "-n",
    "--name",
    "server_name",
    default="anaconda-mcp",
    show_default=True,
    help="Name for the MCP server entry.",
)
@click.option(
    "-t",
    "--transport",
    type=click.Choice(["stdio", "streamable-http"]),
    default="stdio",
    show_default=True,
    help="Transport type for MCP communication.",
)
@click.option(
    "--host",
    default="localhost",
    show_default=True,
    help="Host for streamable-http transport.",
)
@click.option(
    "--port",
    default=8888,
    show_default=True,
    type=int,
    help="Port for streamable-http transport.",
)
@click.option(
    "--no-backup",
    is_flag=True,
    help="Don't create a backup of the existing config file.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrite existing server configuration if present.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output result as JSON.",
)
def claude_install(config_path, server_name, transport, host, port, no_backup, force, output_json):
    """Add Anaconda MCP server configuration to Claude Desktop.

    By default, uses STDIO transport which runs anaconda-mcp as a subprocess.
    For Streamable HTTP, the server must be started separately with `anaconda-mcp serve`.

    \b
    Examples:
        # Add with default STDIO transport
        anaconda-mcp claude install

        # Add with Streamable HTTP transport
        anaconda-mcp claude install --transport streamable-http

        # Use custom config path
        anaconda-mcp claude install --config ~/my-claude-config.json

        # Overwrite existing configuration
        anaconda-mcp claude install --force
    """
    try:
        path = Path(config_path) if config_path else None
        result = configure_claude_desktop(
            config_path=path,
            server_name=server_name,
            transport=transport,
            host=host,
            port=port,
            backup=not no_backup,
            force=force,
        )

        # Convert paths to strings for output
        output = {
            "config_path": str(result["config_path"]),
            "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
            "server_name": result["server_name"],
            "transport": result["transport"],
            "created": result["created"],
            "updated": result["updated"],
        }

        if output_json:
            click.echo(json.dumps(output, indent=2))
        else:
            if result["created"]:
                click.echo(f"✅ Created Claude Desktop config: {result['config_path']}")
            elif result["updated"]:
                click.echo(f"✅ Updated '{server_name}' in: {result['config_path']}")
            else:
                click.echo(f"✅ Added '{server_name}' to: {result['config_path']}")

            if result["backup_path"]:
                click.echo(f"📦 Backup saved to: {result['backup_path']}")

            click.echo(f"\n🔧 Transport: {transport}")
            if transport == "stdio":
                click.echo("   Claude Desktop will start anaconda-mcp automatically.")
            else:
                click.echo(f"   Start the server manually: anaconda-mcp serve --port {port}")

            click.echo("\n🔄 Restart Claude Desktop to apply changes.")

    except FileExistsError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@claude.command(name="uninstall", help="Remove Anaconda MCP from Claude Desktop configuration.")
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False),
    help="Path to Claude Desktop config file (auto-detected by default).",
)
@click.option(
    "-n",
    "--name",
    "server_name",
    default="anaconda-mcp",
    show_default=True,
    help="Name of the MCP server entry to remove.",
)
@click.option(
    "--no-backup",
    is_flag=True,
    help="Don't create a backup of the existing config file.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output result as JSON.",
)
def claude_uninstall(config_path, server_name, no_backup, output_json):
    """Remove Anaconda MCP server configuration from Claude Desktop.

    \b
    Examples:
        # Remove with default name
        anaconda-mcp claude uninstall

        # Remove custom-named server
        anaconda-mcp claude uninstall --name my-anaconda-server
    """
    try:
        path = Path(config_path) if config_path else None
        result = remove_claude_desktop_config(
            config_path=path,
            server_name=server_name,
            backup=not no_backup,
        )

        # Convert paths to strings for output
        output = {
            "config_path": str(result["config_path"]),
            "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
            "server_name": result["server_name"],
            "removed": result["removed"],
        }

        if output_json:
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"✅ Removed '{server_name}' from: {result['config_path']}")
            if result["backup_path"]:
                click.echo(f"📦 Backup saved to: {result['backup_path']}")
            click.echo("\n🔄 Restart Claude Desktop to apply changes.")

    except FileNotFoundError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except KeyError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@claude.command(name="show", help="Show current Claude Desktop configuration.")
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False),
    help="Path to Claude Desktop config file (auto-detected by default).",
)
@click.option(
    "-n",
    "--name",
    "server_name",
    default=None,
    help="Show only this server's configuration.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON.",
)
def claude_show(config_path, server_name, output_json):
    """Show the current Claude Desktop configuration.

    \b
    Examples:
        # Show full configuration
        anaconda-mcp claude show

        # Show specific server
        anaconda-mcp claude show --name anaconda-mcp

        # Output as JSON
        anaconda-mcp claude show --json
    """
    try:
        path = Path(config_path) if config_path else None
        result = show_claude_desktop_config(
            config_path=path,
            server_name=server_name,
        )

        if output_json:
            output = {
                "config_path": str(result["config_path"]),
                "exists": result["exists"],
                "config": result["config"],
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"📁 Config path: {result['config_path']}")
            click.echo(f"📄 Exists: {'Yes' if result['exists'] else 'No'}")

            if result["exists"] and result["config"] is not None:
                click.echo("\n📋 Configuration:")
                click.echo(json.dumps(result["config"], indent=2))
            elif result["exists"] and server_name:
                click.echo(f"\n⚠️  Server '{server_name}' not found in configuration.")
            elif not result["exists"]:
                click.echo("\n💡 Run 'anaconda-mcp claude install' to create the configuration.")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@claude.command(name="path", help="Show the default Claude Desktop config path.")
def claude_path():
    """Show the default Claude Desktop configuration file path for this OS.

    \b
    Examples:
        anaconda-mcp claude path
    """
    try:
        config_path = get_claude_desktop_config_path()
        click.echo(str(config_path))
    except RuntimeError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)


def main():
    cli(obj={})  # entry point


if __name__ == "__main__":
    main()

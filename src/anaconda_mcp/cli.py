import argparse
import json
import logging
import signal
import sys
import time
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

from anaconda_mcp.auth import get_auth_token, start_login
from anaconda_mcp.claude_desktop import (
    configure_claude_desktop,
    get_claude_desktop_config_path,
    remove_claude_desktop_config,
    show_claude_desktop_config,
)
from anaconda_mcp.client_config import (
    SCOPE_GLOBAL,
    SCOPE_PROJECT,
    SUPPORTED_CLIENTS,
    configure_client,
    is_client_installed,
    remove_client,
)
from anaconda_mcp.telemetry import MetricData, MetricNames, SnakeEyes, install_tool_call_tracking
from anaconda_mcp.utils import _render_config_template
from anaconda_mcp.wizard import setup_wizard_page

logger = logging.getLogger(__name__)


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
@click.option("--delay", default=0, show_default=True, type=int, help="Delay in seconds added before serving")
@click.pass_context
def serve(ctx, config, host, port, delay):
    def _handle_sigterm(signum, frame):
        logger.info("Received SIGTERM, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)

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

    rendered_config = _render_config_template(config)
    time.sleep(delay)
    start_login(lambda x: x)
    snake_eyes = SnakeEyes()
    snake_eyes.send(
        MetricData(
            event=MetricNames.START_SERVER.value,
            event_params={},
        ),
        bearer_token=get_auth_token(),
    )
    install_tool_call_tracking(bearer_token_fn=get_auth_token)
    try:
        ns = _ns(verbose=ctx.obj["verbose"], config=rendered_config, host=host, port=port)
        sys.exit(_serve(ns))
    except Exception:
        logger.exception("MCP Composer returned an error. Exiting", exc_info=True)
        sys.exit(1)


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
# Clients Command
# ============================================================================


def _print_clients_table(project_dir: Path | None = None) -> None:
    col_width = max(len(c) for c in SUPPORTED_CLIENTS) + 2
    trans_width = len("stdio, streamable-http") + 2
    click.echo(f"{'CLIENT':<{col_width}}  {'TRANSPORTS':<{trans_width}}  {'SCOPE':<18}  INSTALLED")
    click.echo("-" * (col_width + trans_width + 34))
    for client in sorted(SUPPORTED_CLIENTS):
        supports_project = SUPPORTED_CLIENTS[client]["supports_project_scope"]
        scope_str = "global, project" if supports_project else "global"
        status = is_client_installed(client, project_dir=project_dir)
        parts = []
        if status["global"]:
            parts.append("global")
        if status.get("project"):
            parts.append("project")
        installed_str = ", ".join(parts) if parts else "—"
        click.echo(
            f"{client:<{col_width}}  {'stdio, streamable-http':<{trans_width}}  {scope_str:<18}  {installed_str}"
        )


@cli.command(help="List supported AI clients and their configuration options.")
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Project directory to check for project-scoped installs (defaults to CWD).",
)
def clients(project_dir):
    _print_clients_table(project_dir=project_dir)


# ============================================================================
# Setup Command
# ============================================================================


@cli.command(help="Configure AI clients to use Anaconda MCP.")
@click.option(
    "--client",
    "clients",
    multiple=True,
    type=click.Choice(sorted(SUPPORTED_CLIENTS)),
    help="Client to configure (repeatable). Run 'anaconda-mcp clients' to see options.",
)
@click.option(
    "-t",
    "--transport",
    type=click.Choice(["stdio", "streamable-http"]),
    default="stdio",
    show_default=True,
    help="Transport type.",
)
@click.option("--host", default="localhost", show_default=True, help="Host for streamable-http transport.")
@click.option("--port", default=8888, show_default=True, type=int, help="Port for streamable-http transport.")
@click.option(
    "-n",
    "--name",
    "server_name",
    default="anaconda-mcp",
    show_default=True,
    help="Name for the MCP server entry.",
)
@click.option(
    "--scope",
    type=click.Choice([SCOPE_GLOBAL, SCOPE_PROJECT]),
    default=SCOPE_GLOBAL,
    show_default=True,
    help="Install globally or in the current project.",
)
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Project directory for --scope project (defaults to CWD).",
)
@click.option("--no-backup", is_flag=True, help="Don't create a backup of the existing config file.")
@click.option("-f", "--force", is_flag=True, help="Overwrite existing server configuration if present.")
@click.option("--json", "output_json", is_flag=True, help="Output result as JSON.")
def setup(clients, transport, host, port, server_name, scope, project_dir, no_backup, force, output_json):
    if project_dir is not None and scope != SCOPE_PROJECT:
        raise click.UsageError("--project-dir requires --scope project.")

    if not clients:
        if not sys.stdin.isatty():
            raise click.UsageError("Missing option '--client'. Run 'anaconda-mcp clients' to see available clients.")
        try:
            all_clients = sorted(SUPPORTED_CLIENTS)
            supports_project = [SUPPORTED_CLIENTS[c]["supports_project_scope"] for c in all_clients]
            installed_map = {c: is_client_installed(c, project_dir=project_dir) for c in all_clients}

            initial: set[tuple[int, int]] = set()
            for i, c in enumerate(all_clients):
                if installed_map[c].get("global"):
                    initial.add((i, 0))
                if installed_map[c].get("project"):
                    initial.add((i, 1))

            page = setup_wizard_page(all_clients, supports_project, initial)

            col_for_scope = {"global": 0, "project": 1}
            adds = [
                (c, s) for c, s, checked in page if checked and (all_clients.index(c), col_for_scope[s]) not in initial
            ]
            removes = [
                (c, s) for c, s, checked in page if not checked and (all_clients.index(c), col_for_scope[s]) in initial
            ]

            if not adds and not removes:
                click.echo("No changes.")
                return

        except KeyboardInterrupt as e:
            raise click.Abort() from e

        results = {}
        exit_code = 0

        for client, run_scope in adds:
            key = f"{client}:{run_scope}"
            try:
                result = configure_client(
                    client=client,
                    scope=run_scope,
                    project_dir=project_dir,
                    server_name=server_name,
                    transport=transport,
                    host=host,
                    port=port,
                    backup=not no_backup,
                    force=force,
                )
                results[key] = {
                    "config_path": str(result["config_path"]),
                    "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
                    "server_name": result["server_name"],
                    "transport": transport,
                    "scope": result["scope"],
                    "action": "configured",
                }
            except (FileExistsError, ValueError) as e:
                click.echo(f"[Error] {key}: {e}", err=True)
                exit_code = 1

        for client, run_scope in removes:
            key = f"{client}:{run_scope}"
            try:
                result = remove_client(
                    client=client,
                    scope=run_scope,
                    project_dir=project_dir,
                    server_name=server_name,
                    backup=not no_backup,
                )
                results[key] = {
                    "config_path": str(result["config_path"]),
                    "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
                    "server_name": result["server_name"],
                    "scope": result["scope"],
                    "action": "removed",
                }
            except (FileNotFoundError, KeyError, ValueError) as e:
                click.echo(f"[Error] {key}: {e}", err=True)
                exit_code = 1

        if output_json:
            click.echo(json.dumps(results, indent=2))
        else:
            for key, info in results.items():
                verb = "Removed" if info["action"] == "removed" else "Configured"
                click.echo(f"[OK] {verb} {key} ({info['scope']}): {info['config_path']}")
                if info["backup_path"]:
                    click.echo(f"[Backup] {info['backup_path']}")

        if exit_code != 0:
            raise SystemExit(exit_code)
        return

    results = {}
    exit_code = 0

    scopes_to_run = [SCOPE_GLOBAL, SCOPE_PROJECT] if scope == "both" else [scope]

    for client in clients:
        for run_scope in scopes_to_run:
            key = f"{client}:{run_scope}" if scope == "both" else client
            try:
                result = configure_client(
                    client=client,
                    scope=run_scope,
                    project_dir=project_dir,
                    server_name=server_name,
                    transport=transport,
                    host=host,
                    port=port,
                    backup=not no_backup,
                    force=force,
                )
                results[key] = {
                    "config_path": str(result["config_path"]),
                    "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
                    "server_name": result["server_name"],
                    "transport": transport,
                    "scope": result["scope"],
                    "created": result["created"],
                    "updated": result["updated"],
                }
            except (FileExistsError, ValueError) as e:
                click.echo(f"[Error] {key}: {e}", err=True)
                exit_code = 1

    if output_json:
        click.echo(json.dumps(results, indent=2))
    else:
        for client, info in results.items():
            action = "Created" if info["created"] else ("Updated" if info["updated"] else "Added")
            click.echo(f"[OK] {action} {client} config ({info['scope']}): {info['config_path']}")
            if info["backup_path"]:
                click.echo(f"[Backup] {info['backup_path']}")

    if exit_code != 0:
        raise SystemExit(exit_code)


# ============================================================================
# Remove Command
# ============================================================================


@cli.command(help="Remove Anaconda MCP from AI client configurations.")
@click.option(
    "--client",
    "clients",
    multiple=True,
    type=click.Choice(sorted(SUPPORTED_CLIENTS)),
    help="Client to remove from (repeatable). Required unless --list is used.",
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
    "--scope",
    type=click.Choice([SCOPE_GLOBAL, SCOPE_PROJECT]),
    default=SCOPE_GLOBAL,
    show_default=True,
    help="Remove from global or project config.",
)
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Project directory for --scope project (defaults to CWD).",
)
@click.option("--no-backup", is_flag=True, help="Don't create a backup of the existing config file.")
@click.option("--json", "output_json", is_flag=True, help="Output result as JSON.")
def remove(clients, server_name, scope, project_dir, no_backup, output_json):
    if project_dir is not None and scope != SCOPE_PROJECT:
        raise click.UsageError("--project-dir requires --scope project.")

    if not clients:
        raise click.UsageError("Missing option '--client'. Use 'anaconda-mcp setup' for the interactive wizard.")

    results = {}
    exit_code = 0

    for client in clients:
        try:
            result = remove_client(
                client=client,
                scope=scope,
                project_dir=project_dir,
                server_name=server_name,
                backup=not no_backup,
            )
            results[client] = {
                "config_path": str(result["config_path"]),
                "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
                "server_name": result["server_name"],
                "scope": result["scope"],
                "removed": result["removed"],
            }
        except (FileNotFoundError, KeyError, ValueError) as e:
            click.echo(f"[Error] {client}: {e}", err=True)
            exit_code = 1

    if output_json:
        click.echo(json.dumps(results, indent=2))
    else:
        for client, info in results.items():
            click.echo(
                f"[OK] Removed '{info['server_name']}' from {client} config ({info['scope']}): {info['config_path']}"
            )
            if info["backup_path"]:
                click.echo(f"[Backup] {info['backup_path']}")

    if exit_code != 0:
        raise SystemExit(exit_code)


@cli.group(name="claude-desktop", help="Configure Claude Desktop integration.")
def claude_desktop():
    click.echo(
        "Warning: 'claude-desktop' commands are deprecated. Use 'anaconda-mcp setup --client claude-desktop' instead.",
        err=True,
    )


@claude_desktop.command(name="setup-config", help="Add Anaconda MCP to Claude Desktop configuration.")
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
def claude_configure(config_path, server_name, transport, host, port, no_backup, force, output_json):
    """Add Anaconda MCP server configuration to Claude Desktop.

    By default, uses STDIO transport which runs anaconda-mcp as a subprocess.
    For Streamable HTTP, the server must be started separately with `anaconda-mcp serve`.

    \b
    Examples:
        # Add with default STDIO transport
        anaconda-mcp claude-desktop setup-config

        # Add with Streamable HTTP transport
        anaconda-mcp claude-desktop setup-config --transport streamable-http

        # Use custom config path
        anaconda-mcp claude-desktop setup-config --config ~/my-claude-config.json

        # Overwrite existing configuration
        anaconda-mcp claude-desktop setup-config --force
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
                click.echo(f"[OK] Created Claude Desktop config: {result['config_path']}")
            elif result["updated"]:
                click.echo(f"[OK] Updated '{server_name}' in: {result['config_path']}")
            else:
                click.echo(f"[OK] Added '{server_name}' to: {result['config_path']}")

            if result["backup_path"]:
                click.echo(f"[Backup] Saved to: {result['backup_path']}")

            click.echo("\n[Changes]")
            old_server = result.get("old_config", {}).get("mcpServers", {}).get(server_name)
            new_server = result.get("new_config", {}).get("mcpServers", {}).get(server_name)

            if old_server is None:
                click.echo(f"  + Added server '{server_name}'")
            elif old_server != new_server:
                click.echo(f"  ~ Updated server '{server_name}'")

            click.echo(f"\n[Server Configuration: {server_name}]")
            click.echo(json.dumps(new_server, indent=2))

            click.echo("\n[Complete Configuration File]")
            click.echo(json.dumps(result.get("new_config", {}), indent=2))

            click.echo(f"\n[Transport] {transport}")
            if transport == "stdio":
                click.echo("   Claude Desktop will start anaconda-mcp automatically.")
            else:
                click.echo(f"   Start the server manually: anaconda-mcp serve --port {port}")

            click.echo("\n[Note] Restart Claude Desktop to apply changes.")

    except FileExistsError as e:
        click.echo(f"[Error] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"[Error] {e}", err=True)
        sys.exit(1)


@claude_desktop.command(name="remove-config", help="Remove Anaconda MCP from Claude Desktop configuration.")
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
def claude_remove_config(config_path, server_name, no_backup, output_json):
    """Remove Anaconda MCP server configuration from Claude Desktop.

    \b
    Examples:
        # Remove with default name
        anaconda-mcp claude-desktop remove-config

        # Remove custom-named server
        anaconda-mcp claude-desktop remove-config --name my-anaconda-server
    """
    try:
        path = Path(config_path) if config_path else None
        result = remove_claude_desktop_config(
            config_path=path,
            server_name=server_name,
            backup=not no_backup,
        )

        output = {
            "config_path": str(result["config_path"]),
            "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
            "server_name": result["server_name"],
            "removed": result["removed"],
        }

        if output_json:
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"[OK] Removed '{server_name}' from: {result['config_path']}")
            if result["backup_path"]:
                click.echo(f"[Backup] Saved to: {result['backup_path']}")
            click.echo("\n[Note] Restart Claude Desktop to apply changes.")

    except FileNotFoundError as e:
        click.echo(f"[Error] {e}", err=True)
        sys.exit(1)
    except KeyError as e:
        click.echo(f"[Error] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"[Error] {e}", err=True)
        sys.exit(1)


@claude_desktop.command(name="show", help="Show current Claude Desktop configuration.")
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
        anaconda-mcp claude-desktop show

        # Show specific server
        anaconda-mcp claude-desktop show --name anaconda-mcp

        # Output as JSON
        anaconda-mcp claude-desktop show --json
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
            click.echo(f"[Config path] {result['config_path']}")
            click.echo(f"[Exists] {'Yes' if result['exists'] else 'No'}")

            if result["exists"] and result["config"] is not None:
                click.echo("\n[Configuration]")
                click.echo(json.dumps(result["config"], indent=2))
            elif result["exists"] and server_name:
                click.echo(f"\n[Warning] Server '{server_name}' not found in configuration.")
            elif not result["exists"]:
                click.echo("\n[Tip] Run 'anaconda-mcp claude-desktop setup-config' to create the configuration.")

    except Exception as e:
        click.echo(f"[Error] {e}", err=True)
        sys.exit(1)


@claude_desktop.command(name="path", help="Show the default Claude Desktop config path.")
def claude_path():
    """Show the default Claude Desktop configuration file path for this OS.

    \b
    Examples:
        anaconda-mcp claude-desktop path
    """
    try:
        config_path = get_claude_desktop_config_path()
        click.echo(str(config_path))
    except RuntimeError as e:
        click.echo(f"[Error] {e}", err=True)
        sys.exit(1)


def main():
    cli(obj={})  # entry point


if __name__ == "__main__":
    main()

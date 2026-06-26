import argparse
import functools
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import click
from anaconda_anon_usage.tokens import client_token
from anaconda_auth.client import BaseClient
from anaconda_auth.exceptions import TokenNotFoundError
from anaconda_cli_base.lifecycle import long_running
from anaconda_cli_base.telemetry import get_otel_handler, shutdown_telemetry
from mcp_compose.cli import (
    compose_command as _compose,
)
from mcp_compose.cli import (
    discover_command as _discover,
)
from mcp_compose.composer import ConflictResolution
from rich import print_json as rich_print_json
from rich.console import Console
from rich.table import Table

from anaconda_mcp._shutdown import install_shutdown_handlers
from anaconda_mcp.auth import (
    get_auth_token,
    validate_auth_token,
)
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
from anaconda_mcp.composition import build_composed_server
from anaconda_mcp.config import settings
from anaconda_mcp.mcp_state import is_new_install, mark_installed
from anaconda_mcp.telemetry import (
    NEW_USER_THRESHOLD_DAYS,
    PII_KEY_AAU_CLIENT_ID,
    MetricNames,
    emit_event,
)
from anaconda_mcp.terms import (
    CURRENT_TOS_VERSION,
    TERMS_OF_SERVICE,
    TermsError,
    check_terms_accepted,
    is_terms_current,
    persist_acceptance,
    send_contact_consent_event,
)
from anaconda_mcp.wizard import setup_wizard_page

logger = logging.getLogger(__name__)


_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
_NOISY_LOGGERS = ("httpx", "httpcore")


@functools.cache
def _attach_application_otel_handler() -> None:
    """Attach the OTel log handler to the ``anaconda_mcp`` logger exactly once."""
    logging.getLogger("anaconda_mcp").addHandler(get_otel_handler())


def _configure_logging(level: int) -> None:
    logging.basicConfig(level=level, format=_LOG_FORMAT, datefmt=_LOG_DATEFMT)
    # basicConfig ignores level= once the root logger has handlers, so apply it explicitly.
    logging.getLogger().setLevel(level)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    _attach_application_otel_handler()


def _send_install_event():
    try:
        new_install = is_new_install()
        mark_installed()
        emit_event(
            MetricNames.INSTALL_COMPLETED.value,
            {"new_install": new_install},
            blocking=True,
        )
    except Exception:
        logger.debug("Failed to send install event", exc_info=True)


def _ns(**kwargs):
    """Small helper to create an argparse-like namespace."""
    return argparse.Namespace(**kwargs)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli(ctx):
    """Anaconda MCP wrapper — forwards to mcp-compose."""
    ctx.ensure_object(dict)
    _configure_logging(getattr(logging, settings.log_level.upper(), logging.INFO))
    if ctx.info_name == "anaconda-mcp":
        click.echo(
            "Warning: 'anaconda-mcp' is deprecated. Use 'anaconda mcp' instead.",
            err=True,
        )
    try:
        check_terms_accepted(ctx)
    except TermsError as e:
        if ctx.invoked_subcommand == "serve":
            click.echo(
                f"⚠️  Anaconda MCP cannot start: {e.message}\n\n"
                f"To resolve, run one of:\n"
                f"  anaconda mcp terms accept          (interactive)\n"
                f"  ANACONDA_MCP_ACCEPTED_TERMS=true ANACONDA_MCP_ACCEPTED_TERMS_VERSION={CURRENT_TOS_VERSION}   (environment variables)\n\n"
                f"For more information: anaconda mcp terms status",
                err=True,
            )
            sys.exit(78)
        click.echo(f"Error: {e.message}\n{e.remediation}", err=True)
        sys.exit(1)

    if ctx.invoked_subcommand and ctx.invoked_subcommand != "serve":
        token = get_auth_token()
        if not token:
            raise TokenNotFoundError("Login is required to complete this action.")
        if not validate_auth_token(token):
            raise TokenNotFoundError(
                "Authentication token is invalid or expired. Please run 'anaconda login' to re-authenticate."
            )


@cli.command(help="Run the Anaconda MCP server over stdio (native FastMCP composition).", hidden=True)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=False, dir_okay=False),
    help="Deprecated; ignored. Path to mcp_compose.toml file.",
)
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind to.")
@click.option("--port", default=8000, show_default=True, type=int, help="Port to bind to.")
@click.option("--delay", default=0, show_default=True, type=int, help="Delay in seconds added before serving")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging.")
@click.pass_context
@long_running
def serve(ctx, config, host, port, delay, verbose):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if config or host != "0.0.0.0" or port != 8000:
        click.echo("Warning: --config/--host/--port are ignored; 'serve' runs stdio-only.", err=True)

    time.sleep(delay)
    token = get_auth_token()
    if not token:
        Console(stderr=True).print(
            "[red]❌ Not authenticated. Run [green]anaconda login[/green] to authenticate before starting the server.[/red]"
        )
        sys.exit(1)
    if not validate_auth_token(token):
        Console(stderr=True).print(
            "[red]❌ Token is invalid or expired. Run [green]anaconda login[/green] to re-authenticate.[/red]"
        )
        sys.exit(1)

    login_event_params: dict[str, object] = {}
    try:
        client = BaseClient(api_key=token, domain=settings.anaconda_domain)
        created_at_str = client.account["user"]["created_at"]
        if created_at_str.endswith("Z"):
            created_at_str = created_at_str[:-1] + "+00:00"
        created_at = datetime.fromisoformat(created_at_str)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        account_age_days = (datetime.now(timezone.utc) - created_at).days
        login_event_params["is_new_user"] = account_age_days < NEW_USER_THRESHOLD_DAYS
    except Exception:
        logger.debug("Could not determine new user status", exc_info=True)

    emit_event(MetricNames.LOGIN_COMPLETED.value, login_event_params)
    aau = client_token()
    if aau:
        emit_event(MetricNames.ACTIVE_USER_PING.value, {PII_KEY_AAU_CLIENT_ID: aau})
    emit_event(MetricNames.START_SERVER.value)

    install_shutdown_handlers()
    try:
        build_composed_server().run(transport="stdio")
    except Exception:
        logger.exception("MCP server returned an error. Exiting", exc_info=True)
        sys.exit(1)


@cli.command(help="Compose MCP servers from dependencies.", hidden=True)
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
def compose(ctx, pyproject, name, conflict_resolution, include, exclude, output, output_format):
    ns = _ns(
        verbose=ctx.obj.get("verbose", False),
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


@cli.command(help="Discover MCP servers from dependencies.", hidden=True)
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
        verbose=ctx.obj.get("verbose", False),
        pyproject=pyproject,
        output_format=output_format,
    )
    code = _discover(ns)
    sys.exit(code)


# ============================================================================
# Clients Command
# ============================================================================


def _build_clients_data(project_dir: Path | None = None) -> dict:
    result = {}
    for client in sorted(SUPPORTED_CLIENTS):
        supports_project = SUPPORTED_CLIENTS[client]["supports_project_scope"]
        status = is_client_installed(client, project_dir=project_dir)
        result[client] = {
            "transports": ["stdio"],
            "supports_global_scope": True,
            "supports_project_scope": supports_project,
            "config_key": SUPPORTED_CLIENTS[client]["config_key"],
            "installed_global": status["global"],
            "installed_project": status.get("project", None),
        }
    return result


def _print_clients_table(project_dir: Path | None = None) -> None:
    data = _build_clients_data(project_dir=project_dir)
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("CLIENT", style="cyan", no_wrap=True)
    table.add_column("TRANSPORTS")
    table.add_column("SCOPE")
    table.add_column("INSTALLED")

    for client, info in data.items():
        scope_str = "global, project" if info["supports_project_scope"] else "global"
        parts = []
        if info["installed_global"]:
            parts.append("global")
        if info["installed_project"]:
            parts.append("project")
        installed_str = ", ".join(parts) if parts else "—"
        table.add_row(client, "stdio", scope_str, installed_str)

    console.print(table)


@cli.command(help="List supported AI clients and their configuration options.")
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Project directory to check for project-scoped installs (defaults to CWD).",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
def clients(project_dir, output_json):
    data = _build_clients_data(project_dir=project_dir)
    if output_json:
        rich_print_json(json.dumps(data))
    else:
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
def setup(clients, server_name, scope, project_dir, no_backup, force, output_json):
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
                    backup=not no_backup,
                    force=force,
                )
                results[key] = {
                    "config_path": str(result["config_path"]),
                    "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
                    "server_name": result["server_name"],
                    "transport": "stdio",
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

        if adds:
            _send_install_event()
            shutdown_telemetry()
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
                    backup=not no_backup,
                    force=force,
                )
                results[key] = {
                    "config_path": str(result["config_path"]),
                    "backup_path": str(result["backup_path"]) if result["backup_path"] else None,
                    "server_name": result["server_name"],
                    "transport": "stdio",
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

    _send_install_event()
    shutdown_telemetry()


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
def claude_configure(config_path, server_name, no_backup, force, output_json):
    """Add Anaconda MCP server configuration to Claude Desktop.

    Uses stdio transport, which runs anaconda-mcp as a subprocess.

    \b
    Examples:
        anaconda-mcp claude-desktop setup-config

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

            click.echo("\n[Transport] stdio")
            click.echo("   Claude Desktop will start anaconda-mcp automatically.")

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


@cli.group(name="terms", invoke_without_command=True, help="Manage Terms of Service acceptance.")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
@click.pass_context
def terms(ctx, output_json):
    if ctx.invoked_subcommand is None:
        if output_json:
            click.echo(json.dumps({"terms": TERMS_OF_SERVICE, "version": CURRENT_TOS_VERSION}, indent=2))
        else:
            click.echo(TERMS_OF_SERVICE)
            click.echo(ctx.get_help())


@terms.command(name="status", help="Check whether the Terms of Service have been accepted.")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
def terms_status(output_json):
    accepted = settings.accepted_terms is True
    needs_reaccept = accepted and not is_terms_current(settings.accepted_terms_version)

    if output_json:
        data = {
            "accepted": accepted,
            "accepted_version": settings.accepted_terms_version,
            "current_version": CURRENT_TOS_VERSION,
            "needs_reaccept": needs_reaccept,
        }
        click.echo(json.dumps(data, indent=2))
        if not accepted or needs_reaccept:
            sys.exit(1)
        return

    if not accepted:
        status = "declined" if settings.accepted_terms is False else "not yet responded"
        click.echo(f"Terms of Service: {status}")
        sys.exit(1)

    if needs_reaccept:
        click.echo(
            f"Terms of Service: accepted (version {settings.accepted_terms_version}), "
            f"but current version is {CURRENT_TOS_VERSION}. Please re-accept."
        )
        sys.exit(1)

    click.echo("Terms of Service: accepted")


@terms.command(name="accept", help="Accept the Terms of Service.")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format.")
@click.option("--consent/--no-consent", default=False, help="Consent to be contacted for feedback.")
def terms_accept(output_json, consent):
    already_current = settings.accepted_terms is True and is_terms_current(settings.accepted_terms_version)

    if not already_current:
        persist_acceptance(True)

    if consent:
        token = get_auth_token()
        if token:
            send_contact_consent_event(token)

    if output_json:
        click.echo(
            json.dumps(
                {
                    "accepted": True,
                    "accepted_version": settings.accepted_terms_version or CURRENT_TOS_VERSION,
                    "previously_accepted": already_current,
                },
                indent=2,
            )
        )
        return

    if already_current:
        click.echo("Terms of Service have already been accepted.")
    else:
        click.echo("Terms of Service accepted.")


def main():
    try:
        cli(obj={})  # entry point
    except TokenNotFoundError:
        click.echo(
            "Error: Not authenticated. Please run 'anaconda login' to log in.",
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

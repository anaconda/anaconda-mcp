"""
EULA acceptance management for Anaconda MCP.

To force users to re-accept after a EULA update, set FORCE_NEW_CONSENT = True
before releasing the new package version. Users will only be re-prompted if they
are running a different package version than the one they last accepted under.
If the version is the same, consent is not requested again even if FORCE_NEW_CONSENT
is True — this prevents re-prompting on reinstalls of the same version.

Note: When anaconda-mcp is started by a non-interactive process (e.g. Claude Code,
a shell script, or any other automated process), consent is assumed automatically
and the EULA is accepted on the user's behalf. The user is responsible for ensuring
that all users and systems that invoke this software have reviewed and agreed to
these terms.
"""

import sys
from pathlib import Path

import click

from anaconda_mcp import __version__

# Set to True when shipping a release that contains an updated EULA.
# Users who accepted on a previous package version will be re-prompted.
# Users on the same version are never re-prompted.
FORCE_NEW_CONSENT = False

EULA_TEXT = """
============================================================
  ANACONDA MCP — END USER LICENSE AGREEMENT
============================================================
An AI assistant is requesting permission to manage your conda environments.
By proceeding — or by having configured this connection without executing a command — you acknowledge that:
The AI is an independent third-party model, not affiliated with Anaconda
Anaconda is not responsible for actions the AI takes within your environment
The AI may create, modify, or delete environments and packages autonomously
If you did not intend to grant this access, stop the MCP server now.
============================================================
"""

_FLAG_SEPARATOR = "::"


def _get_eula_flag_path() -> Path:
    """Return the path to the EULA acceptance flag file."""
    return Path.home() / ".anaconda" / "anaconda-mcp" / ".eula_accepted"


def _read_flag() -> tuple[str, str] | tuple[None, None]:
    """Return (version, state) stored in the flag file, or (None, None) if absent."""
    flag = _get_eula_flag_path()
    if not flag.exists():
        return None, None
    parts = flag.read_text().strip().split(_FLAG_SEPARATOR, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def _eula_accepted() -> bool:
    """Return True if the user has accepted the EULA under the current consent requirements.

    Re-consent is required when FORCE_NEW_CONSENT is True and the stored acceptance
    was for a different package version than the one currently running.
    """
    stored_version, state = _read_flag()
    if stored_version is None:
        return False
    if FORCE_NEW_CONSENT and stored_version != __version__:
        return False
    return state in ("accepted", "accepted-forced")


def _mark_eula_accepted() -> None:
    flag = _get_eula_flag_path()
    flag.parent.mkdir(parents=True, exist_ok=True)
    state = "accepted-forced" if FORCE_NEW_CONSENT else "accepted"
    flag.write_text(f"{__version__}{_FLAG_SEPARATOR}{state}")


def _is_interactive() -> bool:
    """Return True if the process is running in an interactive terminal."""
    return sys.stdin.isatty()


def check_eula() -> None:
    """Display EULA and prompt for acceptance on first run or when consent is required.

    If the process is started by a non-interactive process (e.g. Claude Code or any
    other automated caller), consent is assumed automatically and the user is notified
    via stderr.

    Exits if the user explicitly declines in an interactive session.
    """
    if _eula_accepted():
        return

    if not _is_interactive():
        click.echo(
            "\n[Anaconda MCP] This process was started by a non-interactive caller "
            "(e.g. Claude Code or an automated process).\n"
            "Consent to the Anaconda MCP End User License Agreement is assumed on your behalf.\n"
            "Please review the full license at: https://docs.anaconda.com/anaconda-mcp/eula\n",
            err=True,
        )
        _mark_eula_accepted()
        return

    stored_version, _ = _read_flag()
    if FORCE_NEW_CONSENT and stored_version is not None and stored_version != __version__:
        click.echo("\n[Anaconda MCP] The End User License Agreement has been updated.")
        click.echo("Please review and accept the new terms to continue.\n")

    click.echo(EULA_TEXT)
    reply = click.prompt(
        "Do you accept the terms of this End User License Agreement?",
        type=click.Choice(["yes", "no"], case_sensitive=False),
        default="no",
        show_choices=True,
    )

    if reply.lower() == "yes":
        _mark_eula_accepted()
        click.echo("\n[OK] EULA accepted. Welcome to Anaconda MCP.\n")
    else:
        click.echo("\n[Aborted] You must accept the EULA to use Anaconda MCP.")
        click.echo("To uninstall: conda remove anaconda-mcp\n")
        sys.exit(1)

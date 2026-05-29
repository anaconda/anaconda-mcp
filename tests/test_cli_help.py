"""Regression tests for AIC-3389: compose/discover hidden from --help.

The deprecated `compose` and `discover` commands must not appear in the legacy
`anaconda-mcp` help output, but must remain invokable (hidden, not removed).
"""

from click.testing import CliRunner

from anaconda_mcp.cli import cli

# Help text strings unique to each command's listing entry. Using these (rather
# than the bare word "compose") avoids a false match on the group docstring,
# which reads "forwards to mcp-compose".
COMPOSE_LISTING = "Compose MCP servers from dependencies."
DISCOVER_LISTING = "Discover MCP servers from dependencies."


def test_legacy_help_hides_compose_and_discover():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert COMPOSE_LISTING not in result.output
    assert DISCOVER_LISTING not in result.output


def test_compose_remains_invokable():
    result = CliRunner().invoke(cli, ["compose", "--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output and "compose" in result.output


def test_discover_remains_invokable():
    result = CliRunner().invoke(cli, ["discover", "--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output and "discover" in result.output

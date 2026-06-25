"""Transport profile labels for the unified ``mcp_tools`` QA suite.

``anaconda-mcp serve`` now composes natively on FastMCP (conda tools mounted
in-process, the remote ``search`` server proxied) and is **stdio-only** -- there
is no mcp-compose config to generate and no HTTP transport. These profiles are
retained only as labels for pytest / CI reports; both slugs map to the same
native stdio server.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClientEdge(str, Enum):
    """How the automated test connects to the server (stdio for native serve)."""

    HTTP = "http"
    STDIO = "stdio"


@dataclass(frozen=True)
class ComposeTransportProfile:
    """A label for matrix / pytest reports."""

    slug: str
    client: ClientEdge


# Native serve is stdio-only. ``stdio-stdio`` is kept as the canonical slug for
# CI/report continuity; ``stdio`` is a shorter alias. Both are identical now.
PROFILE_STDIO_STDIO = ComposeTransportProfile("stdio-stdio", ClientEdge.STDIO)
PROFILE_STDIO = ComposeTransportProfile("stdio", ClientEdge.STDIO)

PROFILES_BY_SLUG: dict[str, ComposeTransportProfile] = {
    PROFILE_STDIO_STDIO.slug: PROFILE_STDIO_STDIO,
    PROFILE_STDIO.slug: PROFILE_STDIO,
}

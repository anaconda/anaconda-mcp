"""
Canonical mcp-compose TOML snippets for QA transport-matrix testing.

The conda sub-server is the vendored, STDIO-only module ``anaconda_mcp.conda_mcp_lite``,
so mcp-compose always reaches it over a stdio subprocess. The historical
"streamable-http upstream" variants no longer apply; profiles now differ only by the
*client edge* (how the test harness reaches mcp-compose):

  http-http     HTTP client  -> composer streamable-http  (conda stdio subprocess)
  stdio-http    STDIO client -> composer stdio            (conda stdio subprocess)
  stdio-stdio   STDIO client -> composer stdio            (conda stdio subprocess)

``stdio-http`` and ``stdio-stdio`` are equivalent now; both slugs are retained for
CI/report compatibility. The second slug token is historical.

All generators return deterministic text given the same inputs (port, python path).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClientEdge(str, Enum):
    """How the automated test connects to mcp-compose."""

    HTTP = "http"
    STDIO = "stdio"


class UpstreamEdge(str, Enum):
    """How mcp-compose reaches the conda MCP server (always STDIO since the migration)."""

    STREAMABLE_HTTP = "streamable-http"
    STDIO = "stdio"


@dataclass(frozen=True)
class ComposeTransportProfile:
    """A label for matrix / pytest reports."""

    slug: str
    client: ClientEdge
    upstream: UpstreamEdge


# Slugs retained for CI/report compatibility; conda upstream is always STDIO now.
PROFILE_HTTP_HTTP = ComposeTransportProfile("http-http", ClientEdge.HTTP, UpstreamEdge.STDIO)
PROFILE_STDIO_HTTP = ComposeTransportProfile("stdio-http", ClientEdge.STDIO, UpstreamEdge.STDIO)
PROFILE_STDIO_STDIO = ComposeTransportProfile("stdio-stdio", ClientEdge.STDIO, UpstreamEdge.STDIO)

PROFILES_BY_SLUG: dict[str, ComposeTransportProfile] = {
    PROFILE_HTTP_HTTP.slug: PROFILE_HTTP_HTTP,
    PROFILE_STDIO_HTTP.slug: PROFILE_STDIO_HTTP,
    PROFILE_STDIO_STDIO.slug: PROFILE_STDIO_STDIO,
}


_CONDA_STDIO_BLOCK = """\
[[servers.proxied.stdio]]
name = "conda"
command = ["{python_executable}", "-m", "anaconda_mcp.conda_mcp_lite"]
restart_policy = "on-failure"
max_restarts = 3
"""


def render_http_http_toml(*, compose_port: int, python_executable: str) -> str:
    """HTTP client -> mcp-compose (streamable HTTP) -> stdio subprocess -> conda MCP."""
    conda_block = _CONDA_STDIO_BLOCK.format(python_executable=python_executable)
    return f"""\
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"
port = {compose_port}

[transport]
stdio_enabled = false
streamable_http_enabled = true
sse_enabled = false

{conda_block}
[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = true
path_prefix = "/api/v1"
host = "0.0.0.0"
port = {compose_port}
"""


def render_stdio_http_toml(*, python_executable: str) -> str:
    """STDIO client -> mcp-compose (stdio MCP) -> stdio subprocess -> conda MCP."""
    return render_stdio_stdio_toml(python_executable=python_executable)


def render_stdio_stdio_toml(*, python_executable: str) -> str:
    """STDIO client -> mcp-compose (stdio MCP) -> stdio subprocess -> conda MCP."""
    conda_block = _CONDA_STDIO_BLOCK.format(python_executable=python_executable)
    return f"""\
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"

[transport]
stdio_enabled = true
streamable_http_enabled = false
sse_enabled = false

{conda_block}
[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = false
"""


def render_for_profile(
    profile: ComposeTransportProfile,
    *,
    compose_port: int,
    python_executable: str,
) -> str:
    """Dispatch by profile. ``compose_port`` is used only for the HTTP client edge."""
    if profile.client == ClientEdge.HTTP:
        return render_http_http_toml(compose_port=compose_port, python_executable=python_executable)
    return render_stdio_stdio_toml(python_executable=python_executable)

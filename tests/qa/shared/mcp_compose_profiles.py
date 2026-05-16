"""
Canonical mcp-compose TOML snippets for QA transport-matrix testing.

Profiles describe two independent hops:

  (test harness) --client_edge--> (mcp-compose) --upstream_edge--> (conda MCP)

- *client_edge*: how the test talks to anaconda-mcp / mcp-compose (HTTP vs STDIO).
- *upstream_edge*: how mcp-compose talks to ``environments_mcp_server`` (streamable HTTP vs STDIO).

Named combinations used in CI and docs:

  http-http     HTTP  + streamable-http proxy to conda (see start-http-server.sh)
  stdio-http    STDIO + streamable-http proxy to conda
  stdio-stdio   STDIO + STDIO subprocess to conda

``http-stdio`` (HTTP client, STDIO upstream) is valid for mcp-compose but not a
default QA profile; add it here if product needs explicit coverage.

All generators return deterministic text given the same inputs (ports, python path).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class ClientEdge(str, Enum):
    """How the automated test connects to mcp-compose."""

    HTTP = "http"
    STDIO = "stdio"


class UpstreamEdge(str, Enum):
    """How mcp-compose reaches the conda MCP server."""

    STREAMABLE_HTTP = "streamable-http"
    STDIO = "stdio"


@dataclass(frozen=True)
class ComposeTransportProfile:
    """A label for matrix / pytest reports."""

    slug: str
    client: ClientEdge
    upstream: UpstreamEdge


# --- Canonical profiles (same names as TESTS_API_TOOLS.md) ---

PROFILE_HTTP_HTTP = ComposeTransportProfile("http-http", ClientEdge.HTTP, UpstreamEdge.STREAMABLE_HTTP)
PROFILE_STDIO_HTTP = ComposeTransportProfile("stdio-http", ClientEdge.STDIO, UpstreamEdge.STREAMABLE_HTTP)
PROFILE_STDIO_STDIO = ComposeTransportProfile("stdio-stdio", ClientEdge.STDIO, UpstreamEdge.STDIO)

PROFILES_BY_SLUG: dict[str, ComposeTransportProfile] = {
    PROFILE_HTTP_HTTP.slug: PROFILE_HTTP_HTTP,
    PROFILE_STDIO_HTTP.slug: PROFILE_STDIO_HTTP,
    PROFILE_STDIO_STDIO.slug: PROFILE_STDIO_STDIO,
}


def render_http_http_toml(
    *,
    compose_port: int,
    downstream_port: int,
    python_executable: str,
) -> str:
    """
    HTTP client → mcp-compose (streamable HTTP) → streamable HTTP → conda MCP.

    Mirrors ``start-http-server.sh`` (minus process management).

    Includes all 3 MCP servers:
    - environments-mcp (conda): downstream_port
    - conda-meta-mcp: downstream_port + 1
    - search-mcp: remote (anaconda.com)
    """
    anaconda_domain = os.environ.get("ANACONDA_MCP_ANACONDA_DOMAIN", "anaconda.com")
    anaconda_token = _get_auth_token_for_tests()
    conda_meta_port = downstream_port + 1

    if anaconda_token:
        search_auth_config = f'auth_token = "{anaconda_token}"\nauth_type = "bearer"'
    else:
        search_auth_config = "# No auth token - unauthenticated mode"

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

[[servers.proxied.streamable-http]]
name = "conda"
url = "http://localhost:{downstream_port}/mcp"
timeout = 60
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["{python_executable}", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "{downstream_port}"]
startup_delay = 5

[[servers.proxied.streamable-http]]
name = "search"
url = "https://{anaconda_domain}/api/search/mcp"
{search_auth_config}
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"

[[servers.proxied.streamable-http]]
name = "conda-meta"
url = "http://localhost:{conda_meta_port}/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["{python_executable}", "-m", "conda_meta_mcp.cli", "run", "--transport", "streamable-http", "--port", "{conda_meta_port}"]
startup_delay = 5

[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = true
path_prefix = "/api/v1"
host = "0.0.0.0"
port = {compose_port}
"""


def _get_auth_token_for_tests() -> str | None:
    """
    Retrieve the Anaconda API token for QA tests.

    Mirrors the logic from anaconda_mcp.auth.get_auth_token() without importing
    from anaconda_mcp (which is only installed in the server env, not the test runner env).

    Resolution order:
    1. ANACONDA_AUTH_API_KEY env var
    2. Keyring token from 'anaconda login' (via anaconda_auth)
    """
    env_token = os.environ.get("ANACONDA_AUTH_API_KEY")
    if env_token:
        return env_token
    try:
        from anaconda_auth.token import TokenInfo

        token: str = TokenInfo.load().api_key
        return token
    except Exception:
        return None


def render_stdio_http_toml(
    *,
    downstream_port: int,
    python_executable: str,
) -> str:
    """
    STDIO client → mcp-compose (stdio MCP) → streamable HTTP → conda MCP.

    Outer ``[transport]`` is STDIO-only; upstream uses the same streamable-http
    block as ``render_http_http_toml`` (different outer port / API block omitted
    where not needed).

    Includes all 3 MCP servers:
    - environments-mcp (conda): downstream_port
    - search-mcp: remote (anaconda.com)
    - conda-meta-mcp: downstream_port + 1

    Token resolution mirrors real user flow (anaconda_mcp.auth.get_auth_token):
    1. ANACONDA_AUTH_API_KEY env var
    2. Keyring token from 'anaconda login'

    Note: anaconda-mcp server requires authentication to start. If no token is
    available, the config is still generated but server startup will fail with
    a clear error message directing users to authenticate.
    """
    anaconda_domain = os.environ.get("ANACONDA_MCP_ANACONDA_DOMAIN", "anaconda.com")
    anaconda_token = _get_auth_token_for_tests()
    conda_meta_port = downstream_port + 1

    # Auth config for search-mcp: only include if token available
    if anaconda_token:
        search_auth_config = f'auth_token = "{anaconda_token}"\nauth_type = "bearer"'
    else:
        search_auth_config = "# No auth token - unauthenticated mode"

    return f"""\
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"

[transport]
stdio_enabled = true
streamable_http_enabled = false
sse_enabled = false

[[servers.proxied.streamable-http]]
name = "conda"
url = "http://localhost:{downstream_port}/mcp"
timeout = 60
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["{python_executable}", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "{downstream_port}"]
startup_delay = 5

[[servers.proxied.streamable-http]]
name = "search"
url = "https://{anaconda_domain}/api/search/mcp"
{search_auth_config}
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"

[[servers.proxied.streamable-http]]
name = "conda-meta"
url = "http://localhost:{conda_meta_port}/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["{python_executable}", "-m", "conda_meta_mcp.cli", "run", "--transport", "streamable-http", "--port", "{conda_meta_port}"]
startup_delay = 5

[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = false
"""


def render_stdio_stdio_toml(*, python_executable: str) -> str:
    """
    STDIO client → mcp-compose (stdio MCP) → STDIO → conda MCP.

    Matches the historical stdio_tools suite (DESK-1409): avoids HTTP connection
    exhaustion on the upstream hop during heavy regression tests.

    Includes all 3 MCP servers:
    - environments-mcp (conda): STDIO subprocess
    - conda-meta-mcp: STDIO subprocess
    - search-mcp: remote (anaconda.com) via streamable-http (no STDIO option)

    Note: search-mcp is remote-only, so it uses streamable-http even in stdio-stdio profile.
    This is a hybrid config - STDIO for local servers, HTTP for remote.

    Known issue: mcp-compose STDIO proxy has response desync bug when multiple
    STDIO servers are configured. See DESK-1409 and proposed fix:
    https://github.com/j-iliukhina-anaconda/mcp-compose/pull/1
    """
    anaconda_domain = os.environ.get("ANACONDA_MCP_ANACONDA_DOMAIN", "anaconda.com")
    anaconda_token = _get_auth_token_for_tests()

    if anaconda_token:
        search_auth_config = f'auth_token = "{anaconda_token}"\nauth_type = "bearer"'
    else:
        search_auth_config = "# No auth token - unauthenticated mode"

    return f"""\
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"

[transport]
stdio_enabled = true
streamable_http_enabled = false
sse_enabled = false

[[servers.proxied.stdio]]
name = "conda"
command = ["{python_executable}", "-m", "environments_mcp_server", "start", "--transport", "stdio"]
restart_policy = "on-failure"
max_restarts = 3

[[servers.proxied.stdio]]
name = "conda-meta"
command = ["{python_executable}", "-m", "conda_meta_mcp.cli", "run", "--transport", "stdio"]
restart_policy = "on-failure"
max_restarts = 3

[[servers.proxied.streamable-http]]
name = "search"
url = "https://{anaconda_domain}/api/search/mcp"
{search_auth_config}
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"

[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = false
"""


def render_for_profile(
    profile: ComposeTransportProfile,
    *,
    compose_port: int,
    downstream_port: int,
    python_executable: str,
) -> str:
    """
    Dispatch by profile. ``compose_port`` / ``downstream_port`` are ignored for
    pure-STDIO upstream (stdio-stdio).
    """
    if profile == PROFILE_HTTP_HTTP:
        return render_http_http_toml(
            compose_port=compose_port,
            downstream_port=downstream_port,
            python_executable=python_executable,
        )
    if profile == PROFILE_STDIO_HTTP:
        return render_stdio_http_toml(
            downstream_port=downstream_port,
            python_executable=python_executable,
        )
    if profile == PROFILE_STDIO_STDIO:
        return render_stdio_stdio_toml(python_executable=python_executable)
    raise ValueError(f"Unsupported profile: {profile!r}")

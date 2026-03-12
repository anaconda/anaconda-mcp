"""
MCP server providing authentication status and channel access tools.

This module exposes three tools via the MCP protocol (STDIO transport):
  - auth_status: Returns current Anaconda session state and subscriptions.
  - auth_check_channel: Verifies whether the current session can access a given channel URL.
  - conda_list_channels: Lists all configured conda channels with their resolved URLs and
                         whether each requires authentication.

Run as: python -m anaconda_mcp.auth_server

Architectural note
------------------
`auth_status` is a gateway-level tool: it inspects identity and credentials managed by
`anaconda-auth` and belongs in this package.

`auth_check_channel` and `conda_list_channels` are channel-operation tools temporarily
hosted here to unblock auth-related agent workflows (DESK-1358). Per the anaconda-mcp
architecture, channel management belongs in a dedicated downstream MCP server.

TODO(channels-mcp-server): migrate `auth_check_channel`, `conda_list_channels`, and any
future channel write tools (add/remove/configure default channels) to a standalone
`channels-mcp-server` package and proxy it from anaconda-mcp the same way
`environments-mcp-server` is proxied today.

Channel URL resolution
----------------------
conda uses two distinct hosting backends:

  repo.anaconda.cloud  — subscription-gated Anaconda channels (main, r, msys2, security…).
                         Authenticated via a repo token loaded from the keyring by the
                         anaconda-auth conda plugin (AnacondaAuthHandler).

  conda.anaconda.org   — community / org channels (conda-forge, bioconda, custom orgs…).
                         Publicly accessible; no authentication required for reads.

Short-form channel names (no scheme) are normalised:
  - "defaults"         → first URL from `conda config --show default_channels`
                         (typically https://repo.anaconda.cloud/repo/main)
  - everything else    → https://conda.anaconda.org/{name}
"""

import logging
import subprocess
import sys
from urllib.parse import urlparse

import requests
from anaconda_auth.client import BaseClient
from anaconda_auth.exceptions import TokenNotFoundError
from anaconda_auth.token import TokenInfo
from conda.base.context import context as conda_context  # type: ignore[import]
from conda.base.context import reset_context  # type: ignore[import]
from conda.models.channel import Channel  # type: ignore[import]
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("anaconda-auth")

_REPO_ANACONDA_CLOUD = "repo.anaconda.cloud"
_CONDA_ANACONDA_ORG = "conda.anaconda.org"

# repo.anaconda.cloud maps to the "anaconda.com" token domain in anaconda-auth
_REPO_TOKEN_DOMAIN = "anaconda.com"
# Path prefix stripped before extracting the org segment from the URL path
_REPO_URI_PREFIX = "/repo/"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_authenticated_client() -> BaseClient | None:
    """Return an authenticated BaseClient (API key Bearer), or None when unauthenticated."""
    try:
        TokenInfo.load()
    except TokenNotFoundError:
        return None
    return BaseClient()


def _resolve_channel_url(channel_url: str) -> str:
    """Normalise a channel name or URL to a full https:// URL.

    Short-form names (no scheme) are resolved:
      - "defaults" → first entry from ``conda config --show default_channels``
        (falls back to https://repo.anaconda.cloud/repo/main when conda is unavailable)
      - anything else → https://conda.anaconda.org/{name}

    Full URLs are returned unchanged.
    """
    if "://" in channel_url:
        return channel_url

    if channel_url.strip() == "defaults":
        try:
            result = subprocess.run(
                ["conda", "config", "--show", "default_channels"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                stripped = line.strip().lstrip("- ").strip()
                if stripped.startswith("http"):
                    return stripped
        except Exception:
            logger.debug("conda config lookup failed; falling back to default URL")
        return "https://repo.anaconda.cloud/repo/main"

    return f"https://conda.anaconda.org/{channel_url}"


def _get_repo_cloud_token(channel_url: str) -> str | None:
    """Return the repo token that anaconda-auth would use for a repo.anaconda.cloud channel.

    Mirrors the token-selection logic in AnacondaAuthHandler._load_token_from_keyring:
      1. Try an org-specific repo token (org name extracted from the URL path).
      2. Fall back to the first available repo token for the anaconda.com domain.
      3. Return None if no token is found (unauthenticated).
    """
    try:
        token_info = TokenInfo.load(_REPO_TOKEN_DOMAIN)
    except TokenNotFoundError:
        return None

    path = urlparse(channel_url).path
    if path.startswith(_REPO_URI_PREFIX):
        path = path[len(_REPO_URI_PREFIX) :]
    maybe_org, _, _ = path.partition("/")

    try:
        return str(token_info.get_repo_token(maybe_org))
    except TokenNotFoundError:
        pass

    if token_info.repo_tokens:
        return str(token_info.repo_tokens[0].token)

    # No repo token; fall back to the API key if present
    if token_info.api_key:
        return str(token_info.api_key)

    return None


def _build_session_for_url(resolved_url: str) -> tuple[requests.Session, bool]:
    """Return (session, authenticated) with the right credentials for the given channel URL.

    repo.anaconda.cloud — uses a repo token as Bearer header, matching the
                          AnacondaAuthHandler conda plugin behaviour.
    conda.anaconda.org  — community channels are public; no auth is injected.
    everything else     — falls back to BaseClient (API key Bearer).
    """
    hostname = urlparse(resolved_url).netloc

    if hostname == _REPO_ANACONDA_CLOUD:
        token = _get_repo_cloud_token(resolved_url)
        if token is None:
            return requests.Session(), False
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {token}"
        return session, True

    if hostname == _CONDA_ANACONDA_ORG:
        return requests.Session(), False

    client = _get_authenticated_client()
    return (client if client is not None else requests.Session()), client is not None


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool(name="status")
def auth_status() -> dict:
    """
    Returns the current Anaconda authentication state including username, email, and active
    subscriptions. Use before attempting private channel operations to verify the user is logged
    in and has the required access. Equivalent to running 'anaconda whoami' in the terminal.
    """
    client = _get_authenticated_client()
    if client is None:
        return {"is_authenticated": False, "user": None, "subscriptions": [], "is_error": False}

    try:
        account = client.account
    except Exception as exc:
        logger.warning("Failed to fetch account info: %s", exc)
        return {"is_authenticated": False, "user": None, "subscriptions": [], "is_error": False}

    user_data = account.get("user", {})
    raw_subscriptions = account.get("subscriptions", [])
    subscriptions = [
        {
            "product_code": sub.get("product_code"),
            "expires_at": sub.get("expires_at"),
        }
        for sub in raw_subscriptions
    ]

    return {
        "is_authenticated": True,
        "user": {
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
        },
        "subscriptions": subscriptions,
        "is_error": False,
    }


# TODO(channels-mcp-server): move to channels-mcp-server; keep here temporarily to unblock DESK-1358
@mcp.tool(name="check_channel")
def auth_check_channel(channel_url: str) -> dict:
    """
    Checks whether the current authenticated session has access to a given conda channel URL.
    Use before installing from a private or org-scoped channel to verify access without
    triggering a full install attempt. Returns whether the channel is reachable and whether
    credentials are accepted.

    Accepts both full URLs (https://repo.anaconda.cloud/repo/main) and short-form channel
    names (main, conda-forge, defaults). Short-form names are resolved using conda's channel
    configuration: "defaults" resolves via `conda config --show default_channels`; all other
    short names resolve to https://conda.anaconda.org/{name}.
    """
    resolved_url = _resolve_channel_url(channel_url)
    session, authenticated = _build_session_for_url(resolved_url)

    probe_url = resolved_url.rstrip("/")
    if not probe_url.endswith(".json"):
        probe_url = f"{probe_url}/noarch/repodata.json"

    try:
        response = session.head(probe_url, timeout=10, allow_redirects=True)
    except requests.RequestException as exc:
        return {
            "accessible": False,
            "channel_url": channel_url,
            "authenticated": authenticated,
            "error": f"Network error while checking channel: {exc}",
            "is_error": False,
        }

    if response.status_code < 400:
        return {
            "accessible": True,
            "channel_url": channel_url,
            "authenticated": authenticated,
            "is_error": False,
        }

    if response.status_code == 401:
        return {
            "accessible": False,
            "channel_url": channel_url,
            "authenticated": False,
            "error": "HTTP 401 Unauthorized — no active session. Run 'anaconda login' to authenticate.",
            "is_error": False,
        }

    if response.status_code == 403:
        return {
            "accessible": False,
            "channel_url": channel_url,
            "authenticated": authenticated,
            "error": "HTTP 403 Forbidden — credentials accepted but subscription does not grant access to this channel",
            "is_error": False,
        }

    return {
        "accessible": False,
        "channel_url": channel_url,
        "authenticated": authenticated,
        "error": f"HTTP {response.status_code} — channel returned an unexpected status",
        "is_error": False,
    }


def _read_conda_channels() -> tuple[list[str], list[str]]:
    """Return (channels, default_channels) as raw strings from conda config.

    Uses the conda Python API directly — the same approach used by
    environments-mcp-server via anaconda-connector-conda. This avoids any
    dependency on conda being present on PATH and works correctly regardless
    of how the MCP server subprocess was started.

    Each list may contain full URLs or short-form names exactly as conda stores them.
    Raises ImportError when conda is not installed in the current environment.
    """
    reset_context()
    channels = [str(c) if isinstance(c, Channel) else c for c in conda_context.channels]
    default_channels = [str(c) if isinstance(c, Channel) else c for c in conda_context.default_channels]
    return channels, default_channels


def _channel_requires_auth(resolved_url: str) -> bool:
    """Return True when a channel URL is subscription-gated (repo.anaconda.cloud)
    or carries an embedded token (/t/<token>/ path segment)."""
    hostname = urlparse(resolved_url).netloc
    if hostname == _REPO_ANACONDA_CLOUD:
        return True
    # Token embedded in URL: https://conda.anaconda.org/t/<token>/...
    path = urlparse(resolved_url).path
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "t":
        return True
    return False


# TODO(channels-mcp-server): move to channels-mcp-server; keep here temporarily to unblock DESK-1358
@mcp.tool(name="list_channels")
def conda_list_channels() -> dict:
    """
    Lists all conda channels currently configured on this machine, including both the
    user-defined channels and the default_channels. Each entry shows the resolved full URL,
    the source (channels or default_channels), and whether the channel requires authentication
    (i.e. is subscription-gated on repo.anaconda.cloud or carries an embedded token).

    Use this tool to understand what channels are available before calling auth_check_channel
    or conda_install_packages. Equivalent to running 'conda config --show channels' and
    'conda config --show default_channels' in the terminal.
    """
    try:
        raw_channels, raw_default_channels = _read_conda_channels()
    except ImportError:
        return {"channels": [], "is_error": True, "error": "conda is not installed in this environment"}
    except Exception as exc:
        return {"channels": [], "is_error": True, "error": f"Failed to read conda config: {exc}"}

    entries = []
    for name in raw_channels:
        resolved = _resolve_channel_url(name)
        entries.append(
            {
                "name": name,
                "url": resolved,
                "source": "channels",
                "requires_auth": _channel_requires_auth(resolved),
            }
        )
    for name in raw_default_channels:
        resolved = _resolve_channel_url(name)
        entries.append(
            {
                "name": name,
                "url": resolved,
                "source": "default_channels",
                "requires_auth": _channel_requires_auth(resolved),
            }
        )

    return {"channels": entries, "is_error": False}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    main()

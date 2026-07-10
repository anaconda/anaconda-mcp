import base64
import json
import logging
import os
import uuid

from anaconda_auth.client import BaseClient
from anaconda_auth.exceptions import TokenNotFoundError
from anaconda_auth.token import TokenInfo

from anaconda_mcp.config import settings

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    pass


def get_auth_token() -> str | None:
    """
    Retrieve the Anaconda API token if the user is authenticated.

    Returns:
        Optional[str]: The API token if found, otherwise None.

    Notes:
        This function is safe to call repeatedly and is used as the
        single source of truth for authentication state.
    """
    env_token = os.environ.get("ANACONDA_AUTH_API_KEY")
    if env_token:
        return env_token
    try:
        token_info = TokenInfo.load(domain=settings.anaconda_domain)
        api_key: str | None = token_info.api_key
        return api_key
    except TokenNotFoundError:
        return None


def validate_auth_token(token: str) -> bool:
    try:
        _ = BaseClient(api_key=token, domain=settings.anaconda_domain).account
        return True
    except Exception:
        return False


def _decode_jwt_sub(token: str) -> str | None:
    try:
        seg = token.split(".")[1]
        seg += "=" * (-len(seg) % 4)
        claims = json.loads(base64.urlsafe_b64decode(seg))
        sub = claims.get("sub")
        if not isinstance(sub, str):
            return None
        uuid.UUID(sub)  # reject crafted/non-UUID subs (and "") — fails safe to None
        return sub
    except Exception:
        logger.debug("failed to decode JWT sub", exc_info=True)
        return None


_resolved_user_id: str | None = None
_user_id_resolved: bool = False  # lockless racy-init is benign under the GIL; worst case is a redundant recompute


def _reset_user_id_cache() -> None:
    """Test/lifecycle hook: clear the memoized user id."""
    global _resolved_user_id, _user_id_resolved
    _resolved_user_id = None
    _user_id_resolved = False


def resolve_user_id() -> str | None:
    """Return the authenticated account UUID (JWT ``sub``), or None if unauthenticated/undecodable.

    Total: never raises. Memoized for the process lifetime (call
    ``_reset_user_id_cache()`` to clear). The anonymous (None) result is cached
    too — this eliminates per-log-record keyring reads. ``serve`` authenticates
    before any telemetry fires, so it never caches a stale None; short-lived
    unauthenticated processes (e.g. ``setup``) exit before it matters.
    """
    global _resolved_user_id, _user_id_resolved
    if _user_id_resolved:
        return _resolved_user_id
    # Set the memo (default None) BEFORE any logging/decoding so a DEBUG record that
    # re-enters via the OTel log filter returns the cached value instead of recursing.
    _resolved_user_id = None
    _user_id_resolved = True
    try:
        token = get_auth_token()
    except Exception:
        logger.debug("get_auth_token failed while resolving user id", exc_info=True)
        return None
    if token:
        _resolved_user_id = _decode_jwt_sub(token)
    return _resolved_user_id

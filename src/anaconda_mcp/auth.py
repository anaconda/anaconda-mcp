import base64
import json
import logging
import os

from anaconda_auth.client import BaseClient
from anaconda_auth.exceptions import TokenNotFoundError
from anaconda_auth.token import TokenInfo

from anaconda_mcp.config import settings

logger = logging.getLogger(__name__)

ANONYMOUS_USER_ID = "<anonymous-user>"
USER_ID_STATUS_AUTHENTICATED = "authenticated"
USER_ID_STATUS_NO_TOKEN = "no-local-token"
USER_ID_STATUS_BAD_TOKEN = "bad-token"


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
        return sub if isinstance(sub, str) else None
    except Exception:
        return None


_resolved_user_id: tuple[str, str] | None = None


def _reset_user_id_cache() -> None:
    """Test/lifecycle hook: clear the memoized authenticated user id."""
    global _resolved_user_id
    _resolved_user_id = None


def resolve_user_id() -> tuple[str | None, str]:
    global _resolved_user_id
    if _resolved_user_id is not None:
        return _resolved_user_id
    token = get_auth_token()
    if not token:
        return (None, USER_ID_STATUS_NO_TOKEN)
    sub = _decode_jwt_sub(token)
    if sub:
        _resolved_user_id = (sub, USER_ID_STATUS_AUTHENTICATED)
        return _resolved_user_id
    return (None, USER_ID_STATUS_BAD_TOKEN)

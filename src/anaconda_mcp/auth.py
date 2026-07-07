import logging
import os

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

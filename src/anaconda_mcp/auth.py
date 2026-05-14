import logging
import os
from collections.abc import Callable

from anaconda_auth.client import BaseClient
from anaconda_auth.exceptions import TokenNotFoundError
from anaconda_auth.token import TokenInfo

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
        token: str = TokenInfo.load().api_key
        return token
    except TokenNotFoundError:
        return None


def validate_auth_token(token: str) -> bool:
    if os.environ.get("ANACONDA_AUTH_SKIP_VALIDATION"):
        return True
    try:
        _ = BaseClient(api_key=token).account
        return True
    except Exception:
        return False


def make_auth_enforcement_hook(auth_token_fn: Callable[[], str | None]) -> Callable:
    def hook(original_call_tool: Callable) -> Callable:
        async def _enforced(self, name, arguments, context=None, convert_result=False):
            token = auth_token_fn()
            if token is None:
                raise AuthenticationError("Not authenticated. Please run 'anaconda login' to re-authenticate.")
            if not validate_auth_token(token):
                raise AuthenticationError(
                    "Authentication token is invalid or expired. Please run 'anaconda login' to re-authenticate."
                )
            return await original_call_tool(self, name, arguments, context=context, convert_result=convert_result)

        return _enforced

    return hook

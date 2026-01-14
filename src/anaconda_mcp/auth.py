import logging

from anaconda_auth.exceptions import TokenNotFoundError
from anaconda_auth.token import TokenInfo
from anaconda_auth import login as anaconda_login

logger = logging.getLogger(__name__)

def get_auth_token() -> str | None:
    try:
        return TokenInfo.load().api_key
    except TokenNotFoundError:
        logger.info("User not authenticated")


def login() -> str | None:
    try:
        if api_key := get_auth_token():
            return api_key
        anaconda_login()
        return get_auth_token()
    except Exception:
        logger.error("Failed to login to Anaconda")
    
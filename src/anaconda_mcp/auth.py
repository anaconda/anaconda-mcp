import logging
import threading
import time
from collections.abc import Callable

import jwt
from anaconda_auth import login as anaconda_login
from anaconda_auth.exceptions import TokenNotFoundError
from anaconda_auth.token import TokenInfo

from anaconda_mcp.telemetry import MetricData, MetricNames, SnakeEyes

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()
_initialized = False


def get_auth_token() -> str | None:
    """
    Retrieve the Anaconda API token if the user is authenticated.

    Returns:
        Optional[str]: The API token if found, otherwise None.

    Notes:
        This function is safe to call repeatedly and is used as the
        single source of truth for authentication state.
    """
    try:
        token: str = TokenInfo.load().api_key
        return token
    except TokenNotFoundError:
        return None


def get_user_id_from_token(bearer_token: str | None) -> str | None:
    """
    Extract the user ID from a JWT bearer token.

    Args:
        bearer_token (str | None): The JWT bearer token to decode.

    Returns:
        Optional[str]: The user ID (sub claim) if found, otherwise None.

    Notes:
        This function never raises exceptions. It safely handles invalid tokens,
        expired tokens, and None inputs by returning None.
    """
    if bearer_token is None:
        return None
    try:
        decoded = jwt.decode(
            bearer_token,
            algorithms=["RS256"],
            options={"verify_signature": False, "verify_exp": False},
        )
        sub = decoded.get("sub")
        return sub if isinstance(sub, str) else None
    except Exception:
        return None


def start_login(
    init_telemetry: Callable[[str], None], poll_interval: float = 1.0, max_wait_sec: float | None = 60
) -> None:
    """
    Start a non-blocking Anaconda login flow and initialize telemetry if login succeeds.

    This function never blocks the caller. It performs the following steps:
    1. If an authentication token already exists, telemetry is initialized immediately.
    2. Otherwise, an interactive browser-based login is started in a background thread.
    3. A watcher thread polls for token availability.
    4. When a token is detected, `init_telemetry(api_key)` is called exactly once.
    5. If the token does not appear within `max_wait_sec`, telemetry is skipped.

    Args:
        init_telemetry (Callable[[str], None]):
            A function that initializes telemetry using the Anaconda API key.
            This function is guaranteed to be called at most once.
        poll_interval (float, optional):
            Number of seconds between authentication token checks.
            Defaults to 1.0.
        max_wait_sec (float | None, optional):
            Maximum number of seconds to wait for authentication before giving up.
            If None, the watcher will wait indefinitely.
            Defaults to 60.

    Notes:
        - Authentication is optional; server startup is never blocked.
        - Telemetry initialization occurs in the same process (but not necessarily
          the main thread).
        - Background threads are daemonized and will not prevent process exit.
    """

    def init_once(api_key: str) -> None:
        global _initialized
        with _init_lock:
            if _initialized:
                return
            logger.info("Initializing telemetry")
            init_telemetry(api_key)
            _initialized = True
            SnakeEyes().send(MetricData(event=MetricNames.LOGIN_COMPLETED.value, event_params={}), bearer_token=api_key)

    if api_key := get_auth_token():
        init_once(api_key)
        return

    def _login():
        try:
            logger.info("Starting Anaconda login in background")
            anaconda_login()
            logger.info("Login flow finished (token may be available)")
        except Exception:
            logger.exception("Login failed")

    threading.Thread(target=_login, name="anaconda_login", daemon=True).start()

    def _watch():
        start = time.time()
        while True:
            if api_key := get_auth_token():
                logger.info("Token detected; initializing telemetry")
                init_once(api_key)
                return

            if max_wait_sec is not None and (time.time() - start) >= max_wait_sec:
                logger.info("Timed out waiting for login; telemetry not initialized")
                return

            time.sleep(poll_interval)

    threading.Thread(target=_watch, name="telemetry_watcher", daemon=True).start()

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from anaconda_auth import login as anaconda_login
from anaconda_auth.client import BaseClient
from anaconda_auth.exceptions import TokenNotFoundError
from anaconda_auth.token import TokenInfo

from anaconda_mcp.config import settings
from anaconda_mcp.telemetry import NEW_USER_THRESHOLD_DAYS, MetricData, MetricNames, SnakeEyes

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

        # Account fetch outside lock to avoid blocking other threads on HTTP I/O
        event_params: dict[str, Any] = {}
        try:
            client = BaseClient(domain=settings.anaconda_domain, api_key=api_key)
            account = client.account
            created_at_str = account["user"]["created_at"]
            # Python 3.10 fromisoformat() doesn't handle the Z suffix
            if created_at_str.endswith("Z"):
                created_at_str = created_at_str[:-1] + "+00:00"
            created_at = datetime.fromisoformat(created_at_str)
            now = datetime.now(timezone.utc)
            # If created_at is naive (no timezone), assume UTC
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            account_age_days = (now - created_at).days
            event_params["is_new_user"] = account_age_days < NEW_USER_THRESHOLD_DAYS
        except Exception:
            logger.debug("Could not determine new user status", exc_info=True)

        SnakeEyes().send(
            MetricData(event=MetricNames.LOGIN_COMPLETED.value, event_params=event_params), bearer_token=api_key
        )

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

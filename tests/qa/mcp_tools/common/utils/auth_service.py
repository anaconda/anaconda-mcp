"""
Programmatic OAuth authentication service for Anaconda API.

Implements 2-step OAuth flow to obtain session tokens at runtime,
enabling search-mcp tests to run in CI without pre-stored static tokens.

Usage:
    # From environment credentials (.env or GitHub secrets)
    auth = AuthService()
    token = auth.login(email, password)

    # Or use the high-level auth_state fixture in conftest.py
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

AuthSource = Literal["env_credentials", "keyring", "no_auth", "env_credentials_failed"]


class AuthError(Exception):
    """Authentication failed."""

    pass


@dataclass
class AuthState:
    """Authentication state for the test session."""

    logged_in: bool
    token: str | None = None
    source: AuthSource = "no_auth"

    def __str__(self) -> str:
        if self.logged_in:
            return f"logged_in=True, source={self.source}"
        return f"logged_in=False, source={self.source}"


class AuthService:
    """Programmatic OAuth authentication service for Anaconda API."""

    DEFAULT_BASE_URL = "https://api.anaconda.com"

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize auth service with API base URL."""
        self.base_url = base_url or os.environ.get("ANACONDA_API_URL", self.DEFAULT_BASE_URL)
        self.client = httpx.Client(timeout=30.0)

    def _authorize(self) -> str:
        """Step 1: Get state token for OAuth flow."""
        try:
            response = self.client.post(f"{self.base_url}/api/auth/authorize")
            response.raise_for_status()
            data = response.json()
            state: str | None = data.get("state")
            if not state:
                raise AuthError(f"No state token in authorize response: {data}")
            return state
        except httpx.HTTPStatusError as e:
            raise AuthError(f"Authorization request failed: {e}") from e
        except Exception as e:
            raise AuthError(f"Authorization error: {e}") from e

    def login(self, email: str, password: str) -> str:
        """
        Complete OAuth 2-step flow and return session token.

        Args:
            email: Anaconda account email
            password: Anaconda account password

        Returns:
            Session token string

        Raises:
            AuthError: If authentication fails
        """
        state = self._authorize()

        try:
            response = self.client.post(
                f"{self.base_url}/api/auth/login",
                json={"state": state, "email": email, "password": password},
            )
            response.raise_for_status()
            data = response.json()

            token: str | None = data.get("token") or data.get("access_token")
            if not token:
                raise AuthError(f"No token in login response: {data}")

            logger.info("Successfully obtained auth token via OAuth flow")
            return token

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthError("Invalid credentials") from e
            raise AuthError(f"Login request failed: {e}") from e
        except Exception as e:
            raise AuthError(f"Login error: {e}") from e

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> AuthService:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def get_keyring_token() -> str | None:
    """
    Get token from keyring (fallback from `anaconda login`).

    Returns:
        Token string if available, None otherwise
    """
    try:
        from anaconda_auth import login

        token: str | None = login.get_auth_token()
        if token:
            logger.info("Found auth token in keyring")
        return token
    except ImportError:
        logger.debug("anaconda-auth not available for keyring lookup")
        return None
    except Exception as e:
        logger.debug(f"Keyring token lookup failed: {e}")
        return None


def detect_auth_state() -> AuthState:
    """
    Detect current authentication state.

    Priority order:
    1. Environment credentials (ANACONDA_USER_EMAIL + ANACONDA_USER_PASSWORD)
    2. Keyring token (from `anaconda login`)
    3. No authentication available

    Returns:
        AuthState with logged_in status and source information
    """
    email = os.environ.get("ANACONDA_USER_EMAIL")
    password = os.environ.get("ANACONDA_USER_PASSWORD")

    if email and password:
        try:
            with AuthService() as auth:
                token = auth.login(email, password)
                return AuthState(logged_in=True, token=token, source="env_credentials")
        except AuthError as e:
            logger.warning(f"Environment credentials failed: {e}")
            return AuthState(logged_in=False, source="env_credentials_failed")

    keyring_token = get_keyring_token()
    if keyring_token:
        return AuthState(logged_in=True, token=keyring_token, source="keyring")

    logger.info("No authentication available - running in logged-out mode")
    return AuthState(logged_in=False, source="no_auth")

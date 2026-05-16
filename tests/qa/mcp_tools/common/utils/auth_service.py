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

AuthSource = Literal["env_credentials", "no_auth"]


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

    DEFAULT_BASE_URL = "https://anaconda.com"
    DEFAULT_RETURN_TO = "https://anaconda.com"

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize auth service with API base URL."""
        self.base_url = base_url or os.environ.get("ANACONDA_API_URL", self.DEFAULT_BASE_URL)
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def _authorize(self) -> str:
        """Step 1: Get state token for OAuth flow via POST /api/auth/authorize."""
        return_to = os.environ.get("ANACONDA_AUTH_RETURN_TO", self.DEFAULT_RETURN_TO)
        try:
            response = self.client.post(f"{self.base_url}/api/auth/authorize?return_to={return_to}")
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

        Step 1: POST /api/auth/authorize?return_to=... → {state}
        Step 2: POST /api/auth/login/password/{state} → {redirect} → follow for token

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
                f"{self.base_url}/api/auth/login/password/{state}",
                json={"email": email, "password": password},
            )
            response.raise_for_status()
            data = response.json()

            # The login endpoint returns a redirect URL; follow it to get the session
            redirect_url: str | None = data.get("redirect")
            if redirect_url:
                # Following the redirect sets the session cookie
                redirect_response = self.client.get(redirect_url)
                redirect_response.raise_for_status()

            # Get token via whoami endpoint after session is established
            whoami_response = self.client.get(f"{self.base_url}/api/auth/sessions/whoami")
            if whoami_response.status_code == 200:
                whoami_data = whoami_response.json()
                token: str | None = whoami_data.get("tokenized")
                if token:
                    logger.info("Successfully obtained auth token via OAuth flow")
                    return token

            raise AuthError(f"Could not obtain token after login. Response: {data}")

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


def detect_auth_state() -> AuthState:
    """
    Detect current authentication state from ANACONDA_AUTH_API_KEY env var.

    Returns:
        AuthState with logged_in status and source information
    """
    api_key = os.environ.get("ANACONDA_AUTH_API_KEY")
    if api_key:
        logger.info("Using ANACONDA_AUTH_API_KEY from environment")
        return AuthState(logged_in=True, token=api_key, source="env_credentials")

    logger.info("No API key in env - running in logged-out mode")
    return AuthState(logged_in=False, source="no_auth")

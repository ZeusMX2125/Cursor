"""Authentication manager for TopstepX API."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
from loguru import logger
from pydantic import BaseModel

from config.settings import Settings


class TokenResponse(BaseModel):
    """Token response model from ProjectX Gateway API."""

    token: str
    success: bool
    errorCode: int
    errorMessage: Optional[str] = None


class AuthManager:
    """Manages TopstepX API authentication and token refresh."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize authentication by getting initial token."""
        await self.get_token()

    async def get_token(self, force_refresh: bool = False) -> str:
        """Get valid access token, refreshing if necessary."""
        async with self._lock:
            # Check if token is still valid (with 5 minute buffer)
            if (
                not force_refresh
                and self.access_token
                and self.token_expires_at
                and datetime.now() < self.token_expires_at - timedelta(minutes=5)
            ):
                return self.access_token

            # Get new token using ProjectX Gateway API
            auth_mode = self.settings.topstepx_auth_mode.lower()
            logger.info(f"Authenticating with ProjectX Gateway API via {auth_mode}...")
            async with aiohttp.ClientSession() as session:
                try:
                    if auth_mode == "login_app":
                        token = await self._login_with_app_credentials(session)
                    else:
                        token = await self._login_with_api_key(session)

                    if self.settings.topstepx_validate_tokens:
                        await self._validate_token(session, token)

                    self.access_token = token
                    # ProjectX Gateway tokens are valid for ~24h; refresh proactively
                    self.token_expires_at = datetime.now() + timedelta(hours=24)

                    logger.info("Authentication successful - token obtained")
                    return self.access_token
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error during authentication: {error_msg}")
                    logger.debug("Full error details:", exc_info=True)
                    raise RuntimeError(
                        "Unable to authenticate with TopstepX ProjectX gateway. "
                        "Check credentials and network connectivity."
                    ) from e

    async def get_headers(self) -> dict:
        """Get HTTP headers with authentication token."""
        token = await self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _login_with_api_key(self, session: aiohttp.ClientSession) -> str:
        """Authenticate using loginKey flow (username + API key)."""
        payload = {
            "userName": self.settings.topstepx_username,
            "apiKey": self.settings.topstepx_api_key,
        }
        return await self._request_token(
            session=session,
            endpoint="/Auth/loginKey",
            payload=payload,
            mode_label="loginKey",
        )

    async def _login_with_app_credentials(self, session: aiohttp.ClientSession) -> str:
        """Authenticate using loginApp flow (admin credentials)."""
        payload = {
            "userName": self.settings.topstepx_app_username,
            "password": self.settings.topstepx_app_password,
            "deviceId": self.settings.topstepx_app_device_id,
            "appId": self.settings.topstepx_app_id,
            "verifyKey": self.settings.topstepx_app_verify_key,
        }
        return await self._request_token(
            session=session,
            endpoint="/Auth/loginApp",
            payload=payload,
            mode_label="loginApp",
        )

    async def _request_token(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        payload: dict,
        mode_label: str,
    ) -> str:
        """Post a login request and return the bearer token."""
        base_url = self.settings.topstepx_base_url
        # Ensure base_url doesn't have trailing slash, endpoint should start with /
        if base_url.endswith("/"):
            base_url = base_url.rstrip("/")
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = f"{base_url}{endpoint}"
        
        logger.info(f"Attempting authentication to: {url}")
        logger.debug(f"Base URL from settings: {self.settings.topstepx_base_url}")
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }

        async with session.post(url, json=payload, headers=headers) as response:
            response_text = await response.text()
            logger.debug(
                f"{mode_label} auth response status: {response.status}, body: {response_text}"
            )

            if response.status != 200:
                raise RuntimeError(
                    f"{mode_label} authentication failed with HTTP {response.status}: {response_text}"
                )

            try:
                data = await response.json()
            except Exception as json_error:
                raise RuntimeError(
                    f"Failed to parse {mode_label} response: {json_error}"
                ) from json_error

            success = data.get("success", False)
            error_code = data.get("errorCode", -1)
            token = data.get("token")

            if success and error_code == 0 and token:
                return token

            error_messages = {
                0: "Unknown error",
                1: "Invalid credentials",
                2: "Account locked or disabled",
                3: "Invalid API key or username",
                4: "Rate limit exceeded",
            }
            error_msg = data.get("errorMessage") or error_messages.get(
                error_code, f"ErrorCode {error_code}"
            )
            raise RuntimeError(
                f"{mode_label} authentication failed (code={error_code}): {error_msg}"
            )

    async def _validate_token(
        self, session: aiohttp.ClientSession, token: str
    ) -> None:
        """Optionally validate token with ProjectX validate endpoint."""
        url = f"{self.settings.topstepx_base_url}/Auth/validate"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with session.post(url, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(
                        f"Token validation failed with HTTP {response.status}: {text}"
                    )
                logger.debug("ProjectX token validation succeeded")
        except Exception as exc:
            raise RuntimeError(f"Token validation failed: {exc}") from exc


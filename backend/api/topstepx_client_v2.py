"""Refactored TopstepX REST API client with Result-based error handling.

NOTE: This is the V2 client using Result-based error handling (no exceptions).
V1 client (topstepx_client.py) uses exception-based error handling.
Both are currently active - prefer V2 for new code as it provides better error handling.
"""

import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from loguru import logger

from api.auth_manager import AuthManager
from api.result import Result, Success, Error, success, error, auth_error, upstream_error
from config.settings import Settings


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.time()

            # Remove old requests outside the time window
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()

            # If at limit, wait until oldest request expires
            if len(self.requests) >= self.max_requests:
                wait_time = self.time_window - (now - self.requests[0])
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached, waiting {wait_time:.2f} seconds"
                    )
                    await asyncio.sleep(wait_time)
                    # Clean up again after waiting
                    while self.requests and self.requests[0] < time.time() - self.time_window:
                        self.requests.popleft()

            self.requests.append(time.time())


class TopstepXClientV2:
    """TopstepX REST API client with Result-based error handling (no exceptions)."""

    def __init__(self, settings: Settings, auth_manager: AuthManager):
        self.settings = settings
        self.auth_manager = auth_manager
        self.session: Optional[aiohttp.ClientSession] = None

        # Rate limiters
        self.historical_limiter = RateLimiter(50, 30)  # 50 req/30s
        self.general_limiter = RateLimiter(200, 60)  # 200 req/60s
        self._instrument_cache: Dict[str, Dict[str, Any]] = {}
        self._default_account_id: Optional[int] = None

    async def initialize(self) -> None:
        """Initialize the HTTP session."""
        self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        use_historical_limiter: bool = False,
        max_retries: int = 3,
        **kwargs,
    ) -> Result[Dict[str, Any]]:
        """Make an HTTP request with rate limiting and retry logic. Returns Result instead of raising."""
        if not self.session:
            return error("Client not initialized", status_code=503)

        # Apply rate limiting
        if use_historical_limiter:
            await self.historical_limiter.acquire()
        else:
            await self.general_limiter.acquire()

        url = f"{self.settings.topstepx_base_url}{endpoint}"
        
        # Get auth headers - catch auth failures
        try:
            headers = await self.auth_manager.get_headers()
        except Exception as auth_exc:
            logger.error(f"Authentication failed when requesting {endpoint}: {auth_exc}")
            return auth_error(f"Authentication failed: {str(auth_exc)[:200]}")

        logger.debug(f"API Request: {method} {endpoint}")
        
        for attempt in range(max_retries):
            try:
                async with self.session.request(
                    method, url, headers=headers, **kwargs
                ) as response:
                    logger.debug(f"API Response: {response.status} for {method} {endpoint}")
                    
                    # Rate limited - retry
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    # Server error - retry with backoff
                    if response.status >= 500:
                        error_text = await response.text()
                        logger.warning(
                            f"Server error {response.status} on {method} {endpoint}, "
                            f"retry {attempt + 1}/{max_retries}"
                        )
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            await asyncio.sleep(wait_time)
                            continue
                        # Final attempt failed
                        return upstream_error(
                            f"ProjectX API error {response.status}: {error_text[:200]}", 
                            status=502
                        )
                    
                    # Client error (4xx) - don't retry
                    if 400 <= response.status < 500:
                        error_text = await response.text()
                        logger.error(
                            f"Client error {response.status} on {method} {endpoint}. "
                            f"Response: {error_text[:300]}"
                        )
                        
                        # Try to parse JSON error
                        try:
                            error_json = await response.json()
                            error_msg = (
                                error_json.get("errorMessage") or
                                error_json.get("message") or
                                error_text[:200]
                            )
                            return error(
                                error_msg,
                                status_code=response.status,
                                error_code=error_json.get("errorCode"),
                                details=error_json
                            )
                        except:
                            return error(
                                f"HTTP {response.status}: {error_text[:200]}",
                                status_code=response.status
                            )
                    
                    # Success (2xx)
                    try:
                        result = await response.json()
                        logger.debug(f"API Response data: {str(result)[:200]}...")
                        return success(result, status_code=response.status)
                    except Exception as json_err:
                        logger.error(f"Failed to parse JSON response: {json_err}")
                        return error(f"Invalid JSON response from ProjectX API", status_code=502)

            except aiohttp.ClientError as e:
                logger.error(
                    f"Request error on attempt {attempt + 1}/{max_retries} for {method} {endpoint}: {e}",
                    exc_info=True
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                return upstream_error(
                    f"API request failed after {max_retries} attempts: {str(e)[:200]}",
                    status=503
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error on attempt {attempt + 1}/{max_retries} for {method} {endpoint}: {e}",
                    exc_info=True
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                return error(f"Unexpected error: {str(e)[:200]}", status_code=500)

        return error(f"Max retries ({max_retries}) exceeded for {method} {endpoint}", status_code=503)

    # Account methods returning Result
    async def list_accounts(self) -> Result[List[Dict[str, Any]]]:
        """Return list of ProjectX accounts."""
        result = await self._request("GET", "/Account")
        if result.is_error():
            return result
        
        data = result.unwrap()
        if isinstance(data, dict) and data.get("success"):
            return success(data.get("accounts", []))
        return success([])

    async def get_account_info(self, account_id: Optional[int] = None) -> Result[Dict[str, Any]]:
        """Get account information by ID."""
        if account_id:
            result = await self._request("GET", f"/Account/{account_id}")
        else:
            result = await self._request("GET", "/Account")
        
        if result.is_error():
            return result
        
        data = result.unwrap()
        if isinstance(data, dict):
            return success(data)
        return error("Invalid account data format", status_code=500)

    # Market data methods returning Result
    async def list_available_contracts(self, live: bool = True) -> Result[List[Dict[str, Any]]]:
        """Return the list of tradable contracts."""
        payload = {"live": live}
        result = await self._request("POST", "/Contract/available", json=payload)
        
        if result.is_error():
            return result
        
        data = result.unwrap()
        if not isinstance(data, dict):
            return error(f"Invalid response format: expected dict, got {type(data)}", status_code=502)
        
        # Check for success flag and error code according to ProjectX API format
        api_success = data.get("success", False)
        error_code = data.get("errorCode", 0)
        error_message = data.get("errorMessage")
        
        if not api_success or error_code != 0:
            logger.error(
                f"Contract/available API returned error: code={error_code}, "
                f"message={error_message}, response={data}"
            )
            return error(
                error_message or f"Failed to fetch contracts (errorCode={error_code})",
                status_code=502,
                error_code=error_code,
                details=data
            )
        
        # Extract contracts array
        contracts = data.get("contracts", [])
        if not isinstance(contracts, list):
            logger.warning(f"Contracts field is not a list: {type(contracts)}, value={contracts}")
            return error("Invalid contracts format in API response", status_code=502, details=data)
        
        logger.info(f"Successfully fetched {len(contracts)} contracts from ProjectX API")
        return success(contracts)

    async def search_contracts(
        self, search_text: str, live: bool = False
    ) -> Result[List[Dict[str, Any]]]:
        """Return contracts matching the search text."""
        payload = {"searchText": search_text, "live": live}
        result = await self._request("POST", "/Contract/search", json=payload)
        
        if result.is_error():
            return result
        
        data = result.unwrap()
        if not isinstance(data, dict):
            return error(f"Invalid response format: expected dict, got {type(data)}", status_code=502)
        
        # Check for success flag and error code according to ProjectX API format
        api_success = data.get("success", False)
        error_code = data.get("errorCode", 0)
        error_message = data.get("errorMessage")
        
        if not api_success or error_code != 0:
            logger.error(
                f"Contract/search API returned error: code={error_code}, "
                f"message={error_message}"
            )
            return error(
                error_message or f"Search failed (errorCode={error_code})",
                status_code=502,
                error_code=error_code,
                details=data
            )
        
        contracts = data.get("contracts", [])
        if not isinstance(contracts, list):
            logger.warning(f"Contracts field is not a list: {type(contracts)}")
            return error("Invalid contracts format in API response", status_code=502, details=data)
        
        return success(contracts)

    async def flatten_account(self, account_id: int) -> Result[Dict[str, Any]]:
        """Close all positions for an account."""
        payload = {"accountId": account_id}
        result = await self._request("POST", "/Account/flatten", json=payload)
        
        if result.is_error():
            return result
        
        data = result.unwrap()
        if isinstance(data, dict) and data.get("success"):
            return success(data)
        
        error_msg = data.get("errorMessage", "Flatten failed")
        return error(error_msg, status_code=502, details=data)

    async def place_order(
        self,
        account_id: int,
        symbol: str,
        side: str,
        order_type: str,
        quantity: int,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        stop_loss_ticks: Optional[int] = None,
        take_profit_ticks: Optional[int] = None,
    ) -> Result[Dict[str, Any]]:
        """Place an order."""
        payload = {
            "accountId": account_id,
            "symbol": symbol,
            "orderAction": side,
            "orderType": order_type,
            "quantity": quantity,
        }
        
        if price is not None:
            payload["limitPrice"] = price
        if stop_price is not None:
            payload["stopPrice"] = stop_price
        if stop_loss_ticks is not None:
            payload["stopLossTicks"] = stop_loss_ticks
        if take_profit_ticks is not None:
            payload["takeProfitTicks"] = take_profit_ticks
        
        result = await self._request("POST", "/Order/place", json=payload)
        
        if result.is_error():
            return result
        
        data = result.unwrap()
        if isinstance(data, dict) and data.get("success"):
            return success(data)
        
        error_msg = data.get("errorMessage", "Order placement failed")
        return error(error_msg, status_code=502, details=data)


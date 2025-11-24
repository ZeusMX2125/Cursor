"""TopstepX REST API client with rate limiting."""

import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import aiohttp
from loguru import logger

from api.auth_manager import AuthManager
from config.settings import Settings

ResponseData = Union[Dict[str, Any], List[Any]]


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


class TopstepXClient:
    """Client for TopstepX REST API with rate limiting and retry logic."""

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
    ) -> ResponseData:
        """Make an HTTP request with rate limiting and retry logic."""
        if not self.session:
            raise RuntimeError("Client not initialized")

        # Apply rate limiting
        if use_historical_limiter:
            await self.historical_limiter.acquire()
        else:
            await self.general_limiter.acquire()

        url = f"{self.settings.topstepx_base_url}{endpoint}"
        headers = await self.auth_manager.get_headers()

        # Log request details (sanitize sensitive data)
        logger.debug(f"API Request: {method} {endpoint}")
        if "json" in kwargs:
            # Log payload but sanitize sensitive fields
            payload = kwargs["json"].copy() if isinstance(kwargs["json"], dict) else kwargs["json"]
            logger.debug(f"Request payload: {payload}")
        
        for attempt in range(max_retries):
            try:
                async with self.session.request(
                    method, url, headers=headers, **kwargs
                ) as response:
                    # Log response status
                    logger.debug(f"API Response: {response.status} for {method} {endpoint}")
                    
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(
                            f"Rate limited, waiting {retry_after} seconds"
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status >= 500:  # Server error
                        error_text = await response.text()
                        logger.warning(
                            f"Server error {response.status} on {method} {endpoint}, "
                            f"retry {attempt + 1}/{max_retries}. Response: {error_text[:200]}"
                        )
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff
                            await asyncio.sleep(wait_time)
                            continue
                    
                    # Handle 4xx client errors
                    if 400 <= response.status < 500:
                        error_text = await response.text()
                        logger.error(
                            f"Client error {response.status} on {method} {endpoint}. "
                            f"Response: {error_text[:500]}"
                        )
                        # Try to parse JSON error response
                        try:
                            error_json = await response.json()
                            return error_json
                        except:
                            return {"success": False, "error": error_text, "status": response.status}

                    response.raise_for_status()
                    result = await response.json()
                    logger.debug(f"API Response data: {str(result)[:200]}...")
                    return result

            except aiohttp.ClientError as e:
                logger.error(
                    f"Request error on attempt {attempt + 1}/{max_retries} for {method} {endpoint}: {e}",
                    exc_info=True
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise RuntimeError(
                    f"API request failed after {max_retries} attempts: {str(e)}"
                ) from e
            except Exception as e:
                logger.error(
                    f"Unexpected error on attempt {attempt + 1}/{max_retries} for {method} {endpoint}: {e}",
                    exc_info=True
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise

        raise RuntimeError(f"Max retries ({max_retries}) exceeded for {method} {endpoint}")

    async def _resolve_account_id(self, account_id: Optional[int] = None) -> int:
        """Return a valid ProjectX account ID."""
        if account_id:
            return int(account_id)

        if self._default_account_id:
            return self._default_account_id

        account = await self.get_account_info()
        resolved = account.get("id") or account.get("accountId")
        if resolved is None:
            raise RuntimeError("Unable to resolve default account ID from ProjectX API")

        self._default_account_id = int(resolved)
        return self._default_account_id

    async def _get_instrument(self, symbol: str, live: bool = False) -> Dict[str, Any]:
        """Fetch instrument metadata for a symbol."""
        cache_key = f"{symbol.upper()}_{int(live)}"
        if cache_key in self._instrument_cache:
            return self._instrument_cache[cache_key]

        payload = {"searchText": symbol, "live": live}
        response = await self._request("POST", "/Contract/search", json=payload)
        if not isinstance(response, dict) or not response.get("success"):
            raise RuntimeError(f"Unable to find instrument for {symbol}")

        contracts = response.get("contracts", [])
        if not contracts:
            raise RuntimeError(f"No contracts returned for symbol {symbol}")

        instrument = contracts[0]
        self._instrument_cache[cache_key] = instrument
        return instrument

    @staticmethod
    def _timeframe_to_unit(timeframe: str) -> Dict[str, int]:
        """Convert timeframe strings (e.g., 1m) into ProjectX unit definitions."""
        tf = timeframe.strip().lower()
        if not tf:
            return {"unit": 2, "unit_number": 1}  # Default 1 minute

        suffix = tf[-1]
        value_str = tf[:-1] or "1"
        try:
            value = int(value_str)
        except ValueError:
            value = 1

        unit_map = {"s": 1, "m": 2, "h": 3, "d": 4}
        unit = unit_map.get(suffix, 2)
        return {"unit": unit, "unit_number": max(1, value)}

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        """Parse ISO timestamps while tolerating trailing Z."""
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    # Account Methods

    async def list_accounts(self, only_active: bool = True) -> List[Dict[str, Any]]:
        """List accounts available to the authenticated user."""
        payload = {"onlyActiveAccounts": only_active}
        response = await self._request("POST", "/Account/search", json=payload)
        if isinstance(response, dict) and response.get("success"):
            accounts = response.get("accounts", [])
            if accounts:
                first = accounts[0]
                resolved = first.get("id") or first.get("accountId")
                if resolved:
                    self._default_account_id = int(resolved)
            return accounts
        return []

    async def get_account_info(self, account_name: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve a single account record (defaults to the first active account)."""
        accounts = await self.list_accounts()
        if not accounts:
            raise RuntimeError("No accounts available for the authenticated user")

        if account_name:
            for account in accounts:
                if account.get("name", "").lower() == account_name.lower():
                    resolved = account.get("id") or account.get("accountId")
                    if resolved:
                        self._default_account_id = int(resolved)
                    return account

        selected = accounts[0]
        resolved = selected.get("id") or selected.get("accountId")
        if resolved:
            self._default_account_id = int(resolved)
        return selected

    async def get_risk_status(self) -> Dict[str, Any]:
        """Basic risk snapshot derived from account info."""
        account = await self.get_account_info()
        return {
            "account_id": account.get("id"),
            "balance": account.get("balance"),
            "can_trade": account.get("canTrade"),
            "simulated": account.get("simulated"),
        }

    # Order Methods

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: int,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        account_id: Optional[int] = None,
        stop_loss_ticks: Optional[int] = None,
        take_profit_ticks: Optional[int] = None,
        trail_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place an order using ProjectX endpoints."""
        resolved_account = await self._resolve_account_id(account_id)
        instrument = await self._get_instrument(symbol)
        contract_id = instrument.get("id")
        if not contract_id:
            raise RuntimeError(f"Instrument for {symbol} missing contract ID")

        side_map = {"BUY": 0, "SELL": 1}
        type_map = {
            "LIMIT": 1,
            "MARKET": 2,
            "STOP_LIMIT": 3,
            "STOP": 4,
            "TRAILING_STOP": 5,
        }

        payload: Dict[str, Any] = {
            "accountId": resolved_account,
            "contractId": contract_id,
            "type": type_map.get(order_type.upper(), 2),
            "side": side_map.get(side.upper(), 0),
            "size": quantity,
        }
        if price is not None:
            payload["limitPrice"] = price
        if stop_price is not None:
            payload["stopPrice"] = stop_price
        if trail_price is not None:
            payload["trailPrice"] = trail_price
        if stop_loss_ticks is not None:
            payload["stopLossBracket"] = {"ticks": stop_loss_ticks, "type": 2}
        if take_profit_ticks is not None:
            payload["takeProfitBracket"] = {"ticks": take_profit_ticks, "type": 1}

        logger.debug(f"Placing order: symbol={symbol}, side={side}, type={order_type}, qty={quantity}")
        response = await self._request("POST", "/Order/place", json=payload)
        logger.debug(f"Place order response: {response}")
        
        if isinstance(response, dict) and response.get("success"):
            return {
                "order_id": response.get("orderId"),
                "success": True,
                "raw": response,
            }
        return {"success": False, "error": response}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order by ID."""
        payload = {"orderId": order_id}
        response = await self._request("POST", "/Order/cancel", json=payload)
        return response if isinstance(response, dict) else {"success": False}

    async def modify_order(
        self, order_id: str, quantity: Optional[int] = None, price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Modify order size or price."""
        payload: Dict[str, Any] = {"orderId": order_id}
        if quantity is not None:
            payload["size"] = quantity
        if price is not None:
            payload["limitPrice"] = price

        response = await self._request("POST", "/Order/modify", json=payload)
        return response if isinstance(response, dict) else {"success": False}

    async def get_orders(
        self,
        account_id: Optional[int] = None,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for orders within a time window."""
        resolved_account = await self._resolve_account_id(account_id)
        payload: Dict[str, Any] = {"accountId": resolved_account}
        if start_timestamp:
            payload["startTimestamp"] = start_timestamp
        if end_timestamp:
            payload["endTimestamp"] = end_timestamp

        response = await self._request("POST", "/Order/search", json=payload)
        if isinstance(response, dict) and response.get("success"):
            return response.get("orders", [])
        return []

    async def get_open_orders(
        self, account_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Return currently open orders for an account."""
        resolved_account = await self._resolve_account_id(account_id)
        payload = {"accountId": resolved_account}
        response = await self._request("POST", "/Order/searchOpen", json=payload)
        if isinstance(response, dict) and response.get("success"):
            return response.get("orders", [])
        return []

    # Position Methods

    async def get_open_positions(
        self, account_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Return normalized open positions for dashboards and trackers."""
        resolved_account = await self._resolve_account_id(account_id)
        payload = {"accountId": resolved_account}
        response = await self._request("POST", "/Position/searchOpen", json=payload)

        if isinstance(response, list):
            raw_positions = response
        elif isinstance(response, dict):
            if not response.get("success", False):
                return []
            raw_positions = response.get("positions", [])
        else:
            raw_positions = []

        formatted = []
        for pos in raw_positions:
            position_id = pos.get("id") or pos.get("positionId")
            contract_id = pos.get("contractId", "")
            symbol = contract_id.split(".")[3] if "." in contract_id and len(contract_id.split(".")) >= 4 else contract_id
            direction = pos.get("type", 1)
            current_price = (
                pos.get("marketPrice")
                or pos.get("lastPrice")
                or pos.get("currentPrice")
                or pos.get("markPrice")
                or pos.get("averagePrice")
            )
            unrealized = (
                pos.get("profitAndLoss")
                or pos.get("unrealizedPnL")
                or pos.get("floatingProfitLoss")
                or pos.get("floatingPnL")
            )
            realized = pos.get("realizedPnL") or pos.get("realizedProfitLoss")
            entry_price = pos.get("averagePrice", 0.0)
            quantity = pos.get("size", 0)
            entry_value = entry_price * abs(quantity) if entry_price and quantity else 0.0
            current_value = current_price * abs(quantity) if current_price and quantity else 0.0
            
            formatted.append(
                {
                    "position_id": position_id,
                    "contract_id": contract_id,
                    "symbol": symbol,
                    "side": "LONG" if direction == 1 else "SHORT",
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "account_id": resolved_account,
                    "current_price": current_price,
                    "entry_value": entry_value,
                    "current_value": current_value,
                    "unrealized_pnl": unrealized if unrealized is not None else 0.0,
                    "realized_pnl": realized if realized is not None else 0.0,
                    "entry_time": pos.get("creationTimestamp") or pos.get("openTimestamp"),
                }
            )
        return formatted

    async def close_position(
        self, position_id: str, quantity: Optional[int] = None
    ) -> Dict[str, Any]:
        """Close an entire position or partially reduce it."""
        positions = await self.get_open_positions()
        # Try to find by position_id or id field
        target = next(
            (p for p in positions if str(p.get("position_id") or p.get("id") or "") == str(position_id)),
            None,
        )
        if not target:
            raise RuntimeError(f"Position {position_id} not found in open positions")

        contract_id = target.get("contract_id")
        account_id = target.get("account_id")
        if not contract_id or not account_id:
            raise RuntimeError("Missing contract/account data for position close")

        if quantity and quantity < target.get("quantity", 0):
            payload = {
                "accountId": account_id,
                "contractId": contract_id,
                "size": quantity,
            }
            endpoint = "/Position/partialCloseContract"
        else:
            payload = {"accountId": account_id, "contractId": contract_id}
            endpoint = "/Position/closeContract"

        response = await self._request("POST", endpoint, json=payload)
        return response if isinstance(response, dict) else {"success": False}

    # Market Data Methods

    async def retrieve_bars(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical bars (rate limited: 50 req/30s)."""
        instrument = await self._get_instrument(symbol)
        contract_id = instrument.get("id")
        if not contract_id:
            raise RuntimeError(f"Instrument for {symbol} missing contract ID")

        start_dt = self._parse_timestamp(start_date)
        end_dt = self._parse_timestamp(end_date)
        unit_info = self._timeframe_to_unit(timeframe)

        interval_seconds = unit_info["unit_number"]
        if unit_info["unit"] == 2:
            interval_seconds *= 60
        elif unit_info["unit"] == 3:
            interval_seconds *= 3600
        elif unit_info["unit"] == 4:
            interval_seconds *= 86400

        total_seconds = max(1, int((end_dt - start_dt).total_seconds()))
        limit = max(1, int(total_seconds / max(1, interval_seconds)))

        payload = {
            "contractId": contract_id,
            "live": False,
            "startTime": start_dt.isoformat(),
            "endTime": end_dt.isoformat(),
            "unit": unit_info["unit"],
            "unitNumber": unit_info["unit_number"],
            "limit": min(limit, 5000),
            "includePartialBar": False,
        }

        response = await self._request(
            "POST",
            "/History/retrieveBars",
            use_historical_limiter=True,
            json=payload,
        )

        bars: List[Dict[str, Any]] = []
        if isinstance(response, dict) and response.get("success"):
            for bar in response.get("bars", []):
                bars.append(
                    {
                        "time": bar.get("t"),
                        "open": bar.get("o"),
                        "high": bar.get("h"),
                        "low": bar.get("l"),
                        "close": bar.get("c"),
                        "volume": bar.get("v"),
                    }
                )
        return bars

    async def list_available_contracts(self, live: bool = True) -> List[Dict[str, Any]]:
        """Return the list of tradable contracts."""
        payload = {"live": live}
        response = await self._request("POST", "/Contract/available", json=payload)
        if isinstance(response, dict) and response.get("success"):
            return response.get("contracts", [])
        return []

    async def search_contracts(
        self, search_text: str, live: bool = False
    ) -> List[Dict[str, Any]]:
        """Return contracts matching the provided search text."""
        payload = {"searchText": search_text, "live": live}
        response = await self._request("POST", "/Contract/search", json=payload)
        if isinstance(response, dict) and response.get("success"):
            return response.get("contracts", [])
        return []

    async def get_contract_by_id(
        self, contract_id: str
    ) -> Optional[Dict[str, Any]]:
        """Search for a contract by its ID (ProjectX API: /Contract/searchById)."""
        payload = {"contractId": contract_id}
        response = await self._request("POST", "/Contract/searchById", json=payload)
        if isinstance(response, dict) and response.get("success"):
            return response.get("contract")
        return None

    async def get_trades(
        self,
        account_id: Optional[int] = None,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for trades for an account."""
        resolved_account = await self._resolve_account_id(account_id)
        payload: Dict[str, Any] = {"accountId": resolved_account}
        if start_timestamp:
            payload["startTimestamp"] = start_timestamp
        if end_timestamp:
            payload["endTimestamp"] = end_timestamp

        response = await self._request("POST", "/Trade/search", json=payload)
        if isinstance(response, dict) and response.get("success"):
            return response.get("trades", [])
        return []


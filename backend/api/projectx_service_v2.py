"""Refactored ProjectX service with Result-based error handling.

NOTE: This is the V2 service using Result-based error handling (topstepx_client_v2.py).
V1 service (projectx_service.py) uses exception-based error handling (topstepx_client.py).
V2 is used for contracts endpoint, V1 is primary for positions/P&L.
Both are currently active for compatibility.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from api.topstepx_client_v2 import TopstepXClientV2
from api.result import Result, Success, Error, success, error


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectXServiceV2:
    """Provides cached, high-level access to ProjectX REST resources with Result-based error handling."""

    ACCOUNTS_TTL_SECONDS = 60
    CONTRACTS_TTL_SECONDS = 300

    def __init__(self, client: TopstepXClientV2):
        self.client = client
        self._accounts_cache: Optional[List[Dict[str, Any]]] = None
        self._accounts_expiry: datetime = datetime.min.replace(tzinfo=timezone.utc)
        self._contracts_cache: Optional[List[Dict[str, Any]]] = None
        self._contracts_expiry: datetime = datetime.min.replace(tzinfo=timezone.utc)
        self._accounts_lock = asyncio.Lock()
        self._contracts_lock = asyncio.Lock()

    async def get_accounts(self, force_refresh: bool = False) -> Result[List[Dict[str, Any]]]:
        """Return cached account list."""
        async with self._accounts_lock:
            if (
                not force_refresh
                and self._accounts_cache is not None
                and _utc_now() < self._accounts_expiry
            ):
                return success(self._accounts_cache)

            result = await self.client.list_accounts()
            if result.is_error():
                # On error, return stale cache if available
                if self._accounts_cache is not None:
                    logger.warning(f"Using stale accounts cache due to error: {result.message}")
                    return success(self._accounts_cache)
                return result
            
            accounts = result.unwrap()
            self._accounts_cache = accounts
            self._accounts_expiry = _utc_now() + timedelta(seconds=self.ACCOUNTS_TTL_SECONDS)
            logger.debug(f"Loaded {len(accounts)} ProjectX accounts")
            return success(accounts)

    async def get_contracts(self, live: bool = True) -> Result[List[Dict[str, Any]]]:
        """Return cached contract metadata."""
        async with self._contracts_lock:
            # Only use cache if it's not empty and not expired
            if (
                self._contracts_cache is not None
                and len(self._contracts_cache) > 0
                and _utc_now() < self._contracts_expiry
            ):
                logger.debug(f"Returning {len(self._contracts_cache)} contracts from cache")
                return success(self._contracts_cache)

            logger.info(f"Fetching contracts from ProjectX API (live={live})")
            result = await self.client.list_available_contracts(live=live)
            if result.is_error():
                # On error, return stale cache if available and not empty
                if self._contracts_cache is not None and len(self._contracts_cache) > 0:
                    logger.warning(f"Using stale contracts cache ({len(self._contracts_cache)} contracts) due to error: {result.message}")
                    return success(self._contracts_cache)
                
                # If live=True failed and we have no cache, try live=False as fallback
                if live:
                    logger.warning(f"Live contracts failed, trying non-live contracts as fallback: {result.message}")
                    fallback_result = await self.client.list_available_contracts(live=False)
                    if not fallback_result.is_error():
                        fallback_contracts = fallback_result.unwrap()
                        if fallback_contracts and len(fallback_contracts) > 0:
                            logger.info(f"Found {len(fallback_contracts)} non-live contracts, using those")
                            self._contracts_cache = fallback_contracts
                            self._contracts_expiry = _utc_now() + timedelta(seconds=self.CONTRACTS_TTL_SECONDS)
                            return success(fallback_contracts)
                
                # No cache available and fallback failed - return error
                logger.error(f"Failed to load contracts: {result.message}")
                # Avoid hammering the API when failing - cache empty for short time
                self._contracts_cache = []
                self._contracts_expiry = _utc_now() + timedelta(seconds=30)
                return error(result.message, status_code=result.status_code, details=result.details)

            contracts = result.unwrap()
            if contracts is None:
                logger.warning("ProjectX returned null contracts")
                contracts = []

            # If live contracts are empty, try non-live as fallback
            if len(contracts) == 0 and live:
                logger.warning("No live contracts found, trying non-live contracts as fallback")
                fallback_result = await self.client.list_available_contracts(live=False)
                if not fallback_result.is_error():
                    fallback_contracts = fallback_result.unwrap()
                    if fallback_contracts and len(fallback_contracts) > 0:
                        logger.info(f"Found {len(fallback_contracts)} non-live contracts, using those")
                        contracts = fallback_contracts
                    else:
                        logger.warning(f"Non-live contracts also returned empty (or null)")
                else:
                    logger.warning(f"Fallback to non-live contracts failed: {fallback_result.message}")

            if len(contracts) == 0:
                logger.warning(f"ProjectX API returned 0 contracts (live={live}). This may indicate:")
                logger.warning("  - No contracts are currently available")
                logger.warning("  - Account may not have access to contracts")
                logger.warning("  - API authentication may be incomplete")
                logger.warning("  - Market may be closed")

            # Cache the results (even if empty, but with shorter expiry for empty)
            self._contracts_cache = contracts
            if len(contracts) > 0:
                self._contracts_expiry = _utc_now() + timedelta(seconds=self.CONTRACTS_TTL_SECONDS)
            else:
                # Cache empty results for shorter time to allow retry
                self._contracts_expiry = _utc_now() + timedelta(seconds=30)
            
            logger.info(f"Successfully loaded {len(contracts)} contracts from ProjectX API")
            return success(contracts)

    async def search_contracts(self, search_text: str, live: bool = False) -> Result[List[Dict[str, Any]]]:
        """Proxy to contract search endpoint."""
        return await self.client.search_contracts(search_text=search_text, live=live)

    async def flatten_account(self, account_id: int) -> Result[Dict[str, Any]]:
        """Close all positions for an account."""
        return await self.client.flatten_account(account_id=account_id)

    async def place_order(
        self,
        account_id: Optional[int],
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
        # If no account_id, get first account
        if account_id is None:
            accounts_result = await self.get_accounts()
            if accounts_result.is_error():
                return accounts_result
            accounts = accounts_result.unwrap()
            if not accounts:
                return error("No accounts available", status_code=404)
            account_id = accounts[0].get("id")
            if not account_id:
                return error("Invalid account data - no ID found", status_code=500)
        
        return await self.client.place_order(
            account_id=account_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            stop_loss_ticks=stop_loss_ticks,
            take_profit_ticks=take_profit_ticks,
        )


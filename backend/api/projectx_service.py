"""High-level ProjectX service that powers REST and WebSocket consumers."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from api.topstepx_client import TopstepXClient


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectXService:
    """Provides cached, high-level access to ProjectX REST resources."""

    ACCOUNTS_TTL_SECONDS = 60
    CONTRACTS_TTL_SECONDS = 300

    def __init__(self, client: TopstepXClient):
        self.client = client
        self._accounts_cache: Optional[List[Dict[str, Any]]] = None
        self._accounts_expiry: datetime = datetime.min.replace(tzinfo=timezone.utc)
        self._contracts_cache: Optional[List[Dict[str, Any]]] = None
        self._contracts_expiry: datetime = datetime.min.replace(tzinfo=timezone.utc)
        self._accounts_lock = asyncio.Lock()
        self._contracts_lock = asyncio.Lock()
        self._balance_high_water: Optional[float] = None

    async def get_accounts(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Return cached account list."""
        async with self._accounts_lock:
            if (
                not force_refresh
                and self._accounts_cache is not None
                and _utc_now() < self._accounts_expiry
            ):
                return self._accounts_cache

            accounts = await self.client.list_accounts()
            self._accounts_cache = accounts
            self._accounts_expiry = _utc_now() + timedelta(seconds=self.ACCOUNTS_TTL_SECONDS)
            logger.debug(f"Loaded {len(accounts)} ProjectX accounts")
            return accounts

    async def get_primary_account(self) -> Dict[str, Any]:
        """Return the first active ProjectX account."""
        accounts = await self.get_accounts()
        if not accounts:
            raise RuntimeError("No ProjectX accounts available for authenticated user")
        return accounts[0]

    async def get_account_balance(self, account_id: Optional[int] = None) -> float:
        """Return latest balance for an account."""
        account_info = await self.client.get_account_info()
        balance = float(account_info.get("balance", 0.0))
        if self._balance_high_water is None or balance > self._balance_high_water:
            self._balance_high_water = balance
        return balance

    async def get_positions(self, account_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return open positions for the resolved account enriched with P&L metrics."""
        positions = await self.client.get_open_positions(account_id=account_id)

        enriched: List[Dict[str, Any]] = []
        for pos in positions:
            quantity = float(pos.get("quantity") or 0)
            entry_price = float(pos.get("entry_price") or 0.0)
            current_price = float(pos.get("current_price") or entry_price or 0.0)
            side = (pos.get("side") or "LONG").upper()

            entry_value = entry_price * abs(quantity)
            current_value = current_price * abs(quantity)
            direction = 1 if side == "LONG" else -1

            unrealized = pos.get("unrealized_pnl")
            if unrealized is None:
                unrealized = (current_price - entry_price) * abs(quantity) * direction

            pnl_pct = (unrealized / entry_value * 100) if entry_value else 0.0

            enriched.append(
                {
                    **pos,
                    "current_price": current_price,
                    "entry_value": entry_value,
                    "current_value": current_value,
                    "unrealized_pnl": unrealized,
                    "pnl_percent": pnl_pct,
                }
            )
        return enriched

    async def get_orders(
        self,
        account_id: Optional[int] = None,
        hours: int = 24,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return open and recently closed orders."""
        end_ts = _utc_now()
        start_ts = end_ts - timedelta(hours=hours)
        open_orders, recent_orders = await asyncio.gather(
            self.client.get_open_orders(account_id=account_id),
            self.client.get_orders(
                account_id=account_id,
                start_timestamp=start_ts.isoformat(),
                end_timestamp=end_ts.isoformat(),
            ),
        )
        return {"open": open_orders, "recent": recent_orders}

    async def get_trades_summary(
        self, account_id: Optional[int] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """Return trade list and computed metrics for dashboard/stat cards."""
        end_ts = _utc_now()
        start_ts = end_ts - timedelta(hours=hours)
        trades = await self.client.get_trades(
            account_id=account_id,
            start_timestamp=start_ts.isoformat(),
            end_timestamp=end_ts.isoformat(),
        )

        pnl_values = [t.get("profitAndLoss") or 0.0 for t in trades if t.get("profitAndLoss") is not None]
        total_pnl = sum(pnl_values)
        total_trades = len(trades)
        wins = sum(1 for value in pnl_values if value > 0)
        win_rate = (wins / total_trades * 100) if total_trades else 0.0
        trades_today = total_trades

        drawdown = 0.0
        if self._balance_high_water is not None:
            current_balance = await self.get_account_balance(account_id=account_id)
            drawdown = current_balance - self._balance_high_water

        summary = {
            "trades": trades,
            "metrics": {
                "dailyPnl": round(total_pnl, 2),
                "winRate": round(win_rate, 2),
                "drawdown": round(drawdown, 2),
                "tradesToday": trades_today,
            },
        }
        return summary

    async def place_order(self, **kwargs) -> Dict[str, Any]:
        """Proxy for order placement."""
        return await self.client.place_order(**kwargs)

    async def flatten_account(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """Close all open positions for an account."""
        try:
            positions = await self.get_positions(account_id=account_id)
        except Exception as exc:
            logger.error(f"Unable to fetch positions before flatten: {exc}", exc_info=True)
            raise

        results: List[Dict[str, Any]] = []
        errors: List[str] = []
        for pos in positions or []:
            position_id = pos.get("position_id") or pos.get("id")
            if not position_id:
                continue
            try:
                result = await self.client.close_position(str(position_id), quantity=None)
                results.append(result)
            except Exception as exc:  # pragma: no cover - depends on live API
                error_msg = f"Failed to close position {position_id}: {exc}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

        return {
            "closed": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors or None,
        }

    async def get_contracts(self, live: bool = True) -> List[Dict[str, Any]]:
        """Return cached contract metadata."""
        async with self._contracts_lock:
            if (
                self._contracts_cache is not None
                and _utc_now() < self._contracts_expiry
            ):
                return self._contracts_cache

            try:
                contracts = await self.client.list_available_contracts(live=live)
            except Exception as exc:
                logger.error(f"Failed to load ProjectX contracts: {exc}", exc_info=True)
                # Avoid hammering the API when failing
                self._contracts_cache = []
                self._contracts_expiry = _utc_now() + timedelta(seconds=30)
                return []

            if contracts is None:
                logger.warning("ProjectX returned no contracts payload")
                contracts = []

            self._contracts_cache = contracts
            self._contracts_expiry = _utc_now() + timedelta(seconds=self.CONTRACTS_TTL_SECONDS)
            return contracts

    async def search_contracts(self, search_text: str, live: bool = False) -> List[Dict[str, Any]]:
        """Proxy to contract search endpoint."""
        return await self.client.search_contracts(search_text=search_text, live=live)

    async def get_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        """Return historical candles for charts."""
        return await self.client.retrieve_bars(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
        )


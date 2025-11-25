"""High-level ProjectX service that powers REST and WebSocket consumers.

NOTE: This is the V1 service using exception-based error handling (topstepx_client.py).
V2 service (projectx_service_v2.py) uses Result-based error handling (topstepx_client_v2.py).
V1 is the primary service for P&L calculations and position management.
Both are currently active for compatibility.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from api.topstepx_client import TopstepXClient


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _symbol_variants(symbol: Optional[str]) -> List[str]:
    if not symbol:
        return []
    variants: List[str] = []
    raw = symbol.upper()
    variants.append(raw)

    # Handle dot-separated formats (e.g., CON.F.US.MES.Z25 or F.US.MES)
    if "." in raw:
        parts = raw.split(".")
        if parts[-1]:
            variants.append(parts[-1])
        if len(parts) >= 4 and parts[0] == "CON":
            variants.append(parts[3])
        if len(parts) >= 3 and parts[0] == "F" and parts[1] == "US":
            variants.append(parts[2])

    # Strip numeric suffixes (MESZ5 -> MESZ, -> MES)
    variants.append(raw.rstrip("0123456789"))
    letters_only = "".join(ch for ch in raw if ch.isalpha())
    if letters_only:
        variants.append(letters_only)

    # Remove empties while preserving order
    seen = set()
    ordered: List[str] = []
    for variant in variants:
        cleaned = variant.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def _price_multipliers_from_meta(
    tick_size: Optional[float],
    tick_value: Optional[float],
    point_value: Optional[float],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Ensure internal consistency between tick/point values."""
    derived_point = point_value
    if not derived_point and tick_size and tick_value:
        if tick_size != 0:
            derived_point = tick_value / tick_size
    derived_tick_value = tick_value
    if not derived_tick_value and derived_point and tick_size:
        derived_tick_value = derived_point * tick_size
    return tick_size, derived_tick_value, derived_point


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
        self._contract_lookup_cache: Dict[str, Dict[str, Optional[float]]] = {}
        self._contract_lookup_expiry: datetime = datetime.min.replace(tzinfo=timezone.utc)

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

        contract_lookup = await self._ensure_contract_lookup()

        enriched: List[Dict[str, Any]] = []
        for pos in positions:
            quantity = float(pos.get("quantity") or 0)
            entry_price = float(pos.get("entry_price") or 0.0)
            side = (pos.get("side") or "LONG").upper()
            contract_id = pos.get("contract_id") or pos.get("contractId")
            symbol_candidate = pos.get("symbol") or contract_id
            symbol_keys = _symbol_variants(symbol_candidate)
            if contract_id:
                symbol_keys.extend(_symbol_variants(contract_id))

            meta = {}
            for key in symbol_keys:
                lookup = contract_lookup.get(key)
                if lookup:
                    meta = lookup
                    break

            tick_size = meta.get("tick_size") if meta else None
            tick_value = meta.get("tick_value") if meta else None
            point_value = meta.get("point_value") if meta else None
            tick_size, tick_value, point_value = _price_multipliers_from_meta(tick_size, tick_value, point_value)
            
            # Get current price - prefer from position, then from cached quotes, then fallback to entry
            current_price = pos.get("current_price")
            if current_price is None or current_price == entry_price:
                # Try to get from client's cached quotes
                symbol = pos.get("symbol", "")
                cached_price = self.client.get_cached_quote(symbol)
                if cached_price is not None:
                    current_price = cached_price
                else:
                    current_price = entry_price
            current_price = float(current_price)

            # Determine monetary multiplier per unit price movement
            price_multiplier = point_value or 1.0
            entry_value = entry_price * abs(quantity) * price_multiplier if entry_price and quantity else 0.0
            current_value = current_price * abs(quantity) * price_multiplier if current_price and quantity else 0.0
            direction = 1 if side == "LONG" else -1

            price_diff = current_price - entry_price
            unrealized: float
            if point_value:
                unrealized = price_diff * point_value * abs(quantity) * direction
            elif tick_value and tick_size:
                ticks = price_diff / tick_size if tick_size else 0.0
                unrealized = ticks * tick_value * abs(quantity) * direction
            else:
                # Fallback to whatever the API provided or naive calculation
                api_unrealized = pos.get("unrealized_pnl")
                if isinstance(api_unrealized, (int, float)):
                    unrealized = float(api_unrealized)
                elif entry_price > 0 and quantity != 0 and current_price != entry_price:
                    unrealized = price_diff * abs(quantity) * direction
                else:
                    unrealized = 0.0

            pnl_pct = (unrealized / entry_value * 100) if entry_value else 0.0

            enriched.append(
                {
                    **pos,
                    "current_price": current_price,
                    "entry_value": entry_value,
                    "current_value": current_value,
                    "unrealized_pnl": unrealized,
                    "pnl_percent": pnl_pct,
                    "tick_size": tick_size,
                    "tick_value": tick_value,
                    "point_value": point_value,
                    "account_id": account_id or pos.get("account_id"),  # Ensure account_id is included
                }
            )
        return enriched

    async def _ensure_contract_lookup(self) -> Dict[str, Dict[str, Optional[float]]]:
        """Ensure we have a cached contract lookup map for tick/tick-value metadata."""
        if (
            self._contract_lookup_cache
            and _utc_now() < self._contract_lookup_expiry
        ):
            return self._contract_lookup_cache

        if self._contracts_cache is None:
            try:
                await self.get_contracts()
            except Exception as exc:  # pragma: no cover
                logger.debug(f"Unable to refresh contracts cache for lookup: {exc}")

        if self._contracts_cache is not None:
            self._refresh_contract_lookup(self._contracts_cache)

        return self._contract_lookup_cache

    def _refresh_contract_lookup(self, contracts: Optional[List[Dict[str, Any]]]) -> None:
        """Build/update the lookup dict for contract multipliers."""
        lookup: Dict[str, Dict[str, Optional[float]]] = {}
        if not contracts:
            self._contract_lookup_cache = lookup
            self._contract_lookup_expiry = _utc_now() + timedelta(seconds=30)
            return

        for contract in contracts:
            tick_size = _safe_float(contract.get("tickSize") or contract.get("tick_size"))
            tick_value = _safe_float(contract.get("tickValue") or contract.get("tick_value"))
            point_value = _safe_float(contract.get("pointValue") or contract.get("point_value"))
            tick_size, tick_value, point_value = _price_multipliers_from_meta(tick_size, tick_value, point_value)

            meta = {
                "tick_size": tick_size,
                "tick_value": tick_value,
                "point_value": point_value,
            }

            keys: Set[str] = set()
            for field_name in ("symbol", "name", "baseSymbol", "symbolId", "id", "contractId"):
                keys.update(_symbol_variants(contract.get(field_name)))

            for key in keys:
                if key and key not in lookup:
                    lookup[key] = meta

        self._contract_lookup_cache = lookup
        self._contract_lookup_expiry = _utc_now() + timedelta(seconds=self.CONTRACTS_TTL_SECONDS)

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
        """Return trade list and computed metrics for dashboard/stat cards.
        
        Includes both completed trades and half-turn trades for accurate P&L calculation.
        Half-turn trades (profitAndLoss is null) are incomplete round-turns that need to be
        paired with their matching trades to calculate realized P&L correctly.
        """
        end_ts = _utc_now()
        start_ts = end_ts - timedelta(hours=hours)
        
        # Get all trades (half-turn trades are included, identified by profitAndLoss being null)
        all_trades = await self.client.get_trades(
            account_id=account_id,
            start_timestamp=start_ts.isoformat(),
            end_timestamp=end_ts.isoformat(),
        )
        
        # Get P&L values from trades (includes commissions from TopStep)
        # profitAndLoss field in trades already includes commissions
        # Half-turn trades have profitAndLoss as null, so we exclude them from P&L calculation
        # until they're paired with their matching trade
        pnl_values = [t.get("profitAndLoss") for t in all_trades if t.get("profitAndLoss") is not None]
        total_pnl = sum(float(pnl) for pnl in pnl_values)
        
        # Count completed round-turns (trades with profitAndLoss)
        completed_trades = [t for t in all_trades if t.get("profitAndLoss") is not None]
        total_trades = len(completed_trades)
        wins = sum(1 for pnl in pnl_values if float(pnl) > 0)
        win_rate = (wins / total_trades * 100) if total_trades else 0.0
        trades_today = total_trades

        drawdown = 0.0
        if self._balance_high_water is not None:
            current_balance = await self.get_account_balance(account_id=account_id)
            drawdown = current_balance - self._balance_high_water

        summary = {
            "trades": all_trades,  # Include all trades including half-turns
            "metrics": {
                "dailyPnl": round(total_pnl, 2),
                "winRate": round(win_rate, 2),
                "drawdown": round(drawdown, 2),
                "tradesToday": trades_today,
            },
        }
        return summary

    async def get_realized_pnl_for_positions(
        self, account_id: Optional[int] = None, hours: int = 24
    ) -> Dict[str, float]:
        """Get realized P&L per symbol from closed trades (includes commissions).
        
        Includes both completed trades and half-turn trades for accurate calculation.
        Only completed round-turns (with profitAndLoss) contribute to realized P&L.
        """
        end_ts = _utc_now()
        start_ts = end_ts - timedelta(hours=hours)
        
        # Get all trades (half-turn trades are included, identified by profitAndLoss being null)
        all_trades = await self.client.get_trades(
            account_id=account_id,
            start_timestamp=start_ts.isoformat(),
            end_timestamp=end_ts.isoformat(),
        )
        
        # Group realized P&L by symbol/contract
        # Only count completed round-turns (trades with profitAndLoss)
        realized_by_symbol: Dict[str, float] = {}
        for trade in all_trades:
            pnl = trade.get("profitAndLoss")
            if pnl is not None:  # Only completed round-turns have profitAndLoss
                contract_id = trade.get("contractId", "")
                symbol = contract_id.split(".")[3] if "." in contract_id and len(contract_id.split(".")) >= 4 else contract_id
                if symbol:
                    symbol = symbol.upper()
                    realized_by_symbol[symbol] = realized_by_symbol.get(symbol, 0.0) + float(pnl)
        
        return realized_by_symbol

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
                
                # If live contracts return empty, try non-live as fallback
                if isinstance(contracts, list) and len(contracts) == 0 and live:
                    logger.warning("No live contracts found, trying non-live contracts as fallback")
                    contracts = await self.client.list_available_contracts(live=False)
                
            except Exception as exc:
                logger.error(f"Failed to load ProjectX contracts: {exc}", exc_info=True)
                # Avoid hammering the API when failing
                self._contracts_cache = []
                self._contracts_expiry = _utc_now() + timedelta(seconds=30)
                return []

            if contracts is None:
                logger.warning("ProjectX returned no contracts payload")
                contracts = []

            if len(contracts) == 0:
                logger.warning(f"ProjectX API returned 0 contracts (live={live}). This may indicate:")
                logger.warning("  - No contracts are currently available")
                logger.warning("  - Account may not have access to contracts")
                logger.warning("  - API authentication may be incomplete")

            self._contracts_cache = contracts
            self._contracts_expiry = _utc_now() + timedelta(seconds=self.CONTRACTS_TTL_SECONDS)
            self._refresh_contract_lookup(contracts)
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


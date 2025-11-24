"""Position tracking and P&L calculation."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from api.topstepx_client import TopstepXClient
from config.settings import Settings


class Position:
    """Represents an open trading position."""

    def __init__(
        self,
        position_id: str,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
    ):
        self.position_id = position_id
        self.symbol = symbol
        self.side = side  # "LONG" or "SHORT"
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price: Optional[float] = None
        self.unrealized_pnl: float = 0.0
        self.realized_pnl: float = 0.0
        self.opened_at = datetime.now()
        self.updated_at = datetime.now()


class PositionTracker:
    """Tracks open positions and calculates P&L."""

    def __init__(self, settings: Settings, api_client: TopstepXClient):
        self.settings = settings
        self.api_client = api_client
        self.positions: Dict[str, Position] = {}
        self.running = False
        self._lock = asyncio.Lock()

        # Tick values per contract
        self.tick_values = {
            "MES": 5.0,  # $5 per tick
            "MNQ": 2.0,  # $2 per tick
            "MGC": 1.0,  # $1 per tick
        }

    async def start(self) -> None:
        """Start position tracking."""
        self.running = True
        asyncio.create_task(self._sync_loop())

    async def stop(self) -> None:
        """Stop position tracking."""
        self.running = False

    async def _sync_loop(self) -> None:
        """Periodically sync positions from API."""
        while self.running:
            try:
                await self.sync_positions()
                await asyncio.sleep(5)  # Sync every 5 seconds
            except Exception as e:
                logger.error(f"Error in position sync loop: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def sync_positions(self) -> None:
        """Sync positions from API."""
        try:
            api_positions = await self.api_client.get_open_positions()

            async with self._lock:
                # Update existing positions
                for api_pos in api_positions:
                    pos_id = api_pos.get("position_id")
                    if pos_id:
                        if pos_id in self.positions:
                            # Update existing
                            pos = self.positions[pos_id]
                            pos.current_price = api_pos.get("current_price")
                            pos.quantity = api_pos.get("quantity", pos.quantity)
                            pos.unrealized_pnl = api_pos.get("unrealized_pnl", 0.0)
                            pos.updated_at = datetime.now()
                        else:
                            # New position
                            pos = Position(
                                position_id=pos_id,
                                symbol=api_pos.get("symbol", ""),
                                side=api_pos.get("side", "LONG"),
                                quantity=api_pos.get("quantity", 0),
                                entry_price=api_pos.get("entry_price", 0.0),
                            )
                            pos.current_price = api_pos.get("current_price")
                            pos.unrealized_pnl = api_pos.get("unrealized_pnl", 0.0)
                            self.positions[pos_id] = pos

                # Remove closed positions
                api_pos_ids = {p.get("position_id") for p in api_positions if p.get("position_id")}
                closed_positions = [
                    pos_id for pos_id in self.positions.keys() if pos_id not in api_pos_ids
                ]
                for pos_id in closed_positions:
                    del self.positions[pos_id]

        except Exception as e:
            logger.error(f"Error syncing positions: {e}", exc_info=True)

    def update_price(self, symbol: str, price: float) -> None:
        """Update current price for positions."""
        for position in self.positions.values():
            if position.symbol == symbol:
                position.current_price = price
                position.unrealized_pnl = self._calculate_unrealized_pnl(position)
                position.updated_at = datetime.now()

    def _calculate_unrealized_pnl(self, position: Position) -> float:
        """Calculate unrealized P&L for a position."""
        if not position.current_price:
            return 0.0

        tick_value = self.tick_values.get(position.symbol, 1.0)
        price_diff = position.current_price - position.entry_price

        if position.side == "LONG":
            pnl = price_diff * tick_value * position.quantity
        else:  # SHORT
            pnl = -price_diff * tick_value * position.quantity

        return pnl

    async def get_open_positions(self) -> List[Dict]:
        """Get all open positions as dictionaries."""
        async with self._lock:
            return [
                {
                    "position_id": pos.position_id,
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                }
                for pos in self.positions.values()
            ]

    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized P&L across all positions."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())

    def get_total_realized_pnl(self) -> float:
        """Get total realized P&L."""
        return sum(pos.realized_pnl for pos in self.positions.values())


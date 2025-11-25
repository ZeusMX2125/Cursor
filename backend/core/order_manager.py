"""Order management and execution."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from api.topstepx_client import TopstepXClient
from config.settings import Settings
from core.position_tracker import PositionTracker
from risk.risk_manager import RiskManager
from ml.rl_agent import RLAgent


class Order:
    """Represents a trading order."""

    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: int,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side  # "BUY" or "SELL"
        self.order_type = order_type  # "MARKET", "LIMIT", "STOP_MARKET"
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.status = "PENDING"
        self.fill_price: Optional[float] = None
        self.filled_quantity = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class OrderManager:
    """Manages order lifecycle and execution."""

    def __init__(
        self,
        settings: Settings,
        api_client: TopstepXClient,
        risk_manager: RiskManager,
        position_tracker: PositionTracker,
        rl_agent: Optional[RLAgent] = None,
    ):
        self.settings = settings
        self.api_client = api_client
        self.risk_manager = risk_manager
        self.position_tracker = position_tracker
        self.rl_agent = rl_agent
        self.orders: Dict[str, Order] = {}
        self._lock = asyncio.Lock()

    async def execute_signal(self, signal: Dict, skip_risk_check: bool = False) -> Optional[str]:
        """Execute a trading signal."""
        try:
            # Check risk before executing
            if not skip_risk_check and not await self.risk_manager.check_trade_risk(signal):
                logger.warning(f"Signal rejected by risk manager: {signal}")
                return None

            # Calculate position size
            # Use RL agent if available
            rl_quantity = None
            if self.rl_agent and self.rl_agent.enabled:
                # Construct state from signal metadata if available or fetch
                # For now, we use a placeholder or signal confidence
                # In real implementation, we'd pass full market state
                pass
            
            # Default risk manager sizing
            quantity = await self.risk_manager.calculate_position_size(signal)
            
            if quantity <= 0:
                logger.warning(f"Invalid position size: {quantity}")
                return None

            # Determine order type
            order_type = signal.get("order_type", "MARKET")
            price = signal.get("entry_price")
            stop_price = signal.get("stop_loss")

            # Place order
            if self.settings.paper_trading_mode:
                logger.info(
                    f"[PAPER] Would place {order_type} {signal['side']} "
                    f"{quantity} {signal['symbol']} @ {price}"
                )
                # In paper trading, simulate order
                order_id = f"PAPER-{datetime.now().timestamp()}"
                order = Order(
                    order_id=order_id,
                    symbol=signal["symbol"],
                    side=signal["side"],
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                )
                order.status = "FILLED"
                order.fill_price = price or signal.get("current_price", 0)
                self.orders[order_id] = order
                return order_id
            else:
                # Live trading
                response = await self.api_client.place_order(
                    symbol=signal["symbol"],
                    side=signal["side"],
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                )

                order_id = response.get("order_id")
                if order_id:
                    order = Order(
                        order_id=order_id,
                        symbol=signal["symbol"],
                        side=signal["side"],
                        order_type=order_type,
                        quantity=quantity,
                        price=price,
                        stop_price=stop_price,
                    )
                    self.orders[order_id] = order
                    logger.info(f"Order placed: {order_id}")
                    return order_id

        except Exception as e:
            logger.error(f"Error executing signal: {e}", exc_info=True)
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            if order_id in self.orders:
                if not self.settings.paper_trading_mode:
                    await self.api_client.cancel_order(order_id)
                self.orders[order_id].status = "CANCELLED"
                self.orders[order_id].updated_at = datetime.now()
                logger.info(f"Order cancelled: {order_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}", exc_info=True)
            return False

    async def modify_order(
        self, order_id: str, quantity: Optional[int] = None, price: Optional[float] = None
    ) -> bool:
        """Modify an existing order."""
        try:
            if order_id not in self.orders:
                return False

            if not self.settings.paper_trading_mode:
                await self.api_client.modify_order(order_id, quantity, price)

            order = self.orders[order_id]
            if quantity:
                order.quantity = quantity
            if price:
                order.price = price
            order.updated_at = datetime.now()

            logger.info(f"Order modified: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error modifying order: {e}", exc_info=True)
            return False

    async def close_all_positions(self) -> None:
        """Close all open positions."""
        try:
            positions = await self.position_tracker.get_open_positions()
            for position in positions:
                position_id = position.get("position_id")
                if position_id:
                    if self.settings.paper_trading_mode:
                        logger.info(f"[PAPER] Would close position: {position_id}")
                    else:
                        await self.api_client.close_position(position_id)
                        logger.info(f"Position closed: {position_id}")
        except Exception as e:
            logger.error(f"Error closing positions: {e}", exc_info=True)

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        return self.orders.get(order_id)

    def get_all_orders(self) -> List[Order]:
        """Get all orders."""
        return list(self.orders.values())

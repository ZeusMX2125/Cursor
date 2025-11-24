"""
Main entry point for the TopstepX trading bot.
Orchestrates the asyncio event loop and coordinates all system components.
"""

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from loguru import logger

from api.auth_manager import AuthManager
from api.topstepx_client import TopstepXClient
from api.websocket_handler import WebSocketHandler
from core.data_manager import DataManager
from core.order_manager import OrderManager
from core.position_tracker import PositionTracker
from risk.account_risk_manager import AccountRiskManager
from strategies.strategy_selector import StrategySelector
from monitoring.performance_tracker import PerformanceTracker
from config.settings import Settings
from accounts.models import AccountConfig


class TradingBot:
    """Main trading bot orchestrator."""

    def __init__(self, settings: Settings, account_config: Optional[AccountConfig] = None):
        self.settings = settings
        self.account_config = account_config
        self.account_id = account_config.account_id if account_config else "default"
        self.running = False
        self.auth_manager = None
        self.api_client = None
        self.ws_handler = None
        self.data_manager = None
        self.order_manager = None
        self.position_tracker = None
        self.risk_manager = None
        self.strategy_selector = None
        self.performance_tracker = None

    async def initialize(self) -> None:
        """Initialize all system components."""
        logger.info("Initializing trading bot...")

        # Initialize authentication
        self.auth_manager = AuthManager(self.settings)
        await self.auth_manager.initialize()

        # Initialize API client
        self.api_client = TopstepXClient(
            self.settings, self.auth_manager
        )
        await self.api_client.initialize()

        # Initialize WebSocket handler
        self.ws_handler = WebSocketHandler(
            self.settings, self.auth_manager
        )

        # Initialize data manager
        self.data_manager = DataManager(self.settings)

        # Initialize position tracker
        self.position_tracker = PositionTracker(
            self.settings, self.api_client
        )

        # Initialize risk manager (per-account)
        if self.account_config:
            self.risk_manager = AccountRiskManager(
                self.account_id,
                self.settings,
                self.account_config.profile,
                self.position_tracker,
            )
        else:
            # Fallback to old singleton for backward compatibility
            from risk.risk_manager import RiskManager
            self.risk_manager = RiskManager(self.settings, self.position_tracker)

        # Initialize order manager
        self.order_manager = OrderManager(
            self.settings,
            self.api_client,
            self.risk_manager,
            self.position_tracker,
        )

        # Initialize strategy selector with account config
        self.strategy_selector = StrategySelector(
            self.settings,
            self.data_manager,
            self.risk_manager,
            self.account_config,
        )

        # Initialize performance tracker
        self.performance_tracker = PerformanceTracker(self.settings)

        logger.info("Trading bot initialized successfully")

    async def start(self) -> None:
        """Start the trading bot."""
        if self.running:
            logger.warning("Bot is already running")
            return

        logger.info("Starting trading bot...")
        self.running = True

        # Connect WebSocket
        await self.ws_handler.connect()

        # Start data manager
        await self.data_manager.start()

        # Start position tracker
        await self.position_tracker.start()

        # Start strategy selector
        await self.strategy_selector.start()

        # Start main trading loop
        await self._trading_loop()

    async def stop(self) -> None:
        """Stop the trading bot gracefully."""
        if not self.running:
            return

        logger.info("Stopping trading bot...")
        self.running = False

        # Stop strategy selector
        if self.strategy_selector:
            await self.strategy_selector.stop()

        # Close all positions if required
        if self.order_manager:
            await self.order_manager.close_all_positions()

        # Stop position tracker
        if self.position_tracker:
            await self.position_tracker.stop()

        # Stop data manager
        if self.data_manager:
            await self.data_manager.stop()

        # Disconnect WebSocket
        if self.ws_handler:
            await self.ws_handler.disconnect()

        logger.info("Trading bot stopped")

    async def _trading_loop(self) -> None:
        """Main trading event loop."""
        logger.info("Starting main trading loop...")

        while self.running:
            try:
                # Check if trading hours
                if not self._is_trading_hours():
                    await asyncio.sleep(60)  # Check every minute
                    continue

                # Check risk limits
                if not await self.risk_manager.can_trade():
                    logger.warning("Trading halted by risk manager")
                    await asyncio.sleep(10)
                    continue

                # Get market data updates
                # (Handled by WebSocket callbacks)

                # Get strategy signals
                signals = await self.strategy_selector.get_signals()

                # Process signals
                for signal in signals:
                    if await self.risk_manager.check_trade_risk(signal):
                        await self.order_manager.execute_signal(signal)

                # Update performance metrics
                await self.performance_tracker.update()

                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        from datetime import datetime
        import pytz

        ct = pytz.timezone("America/Chicago")
        now = datetime.now(ct)
        hour = now.hour
        minute = now.minute

        # Trading hours: 5:00 PM CT (previous day) to 3:10 PM CT (current day)
        # This is 17:00 to 15:10 in 24-hour format
        if hour >= 17 or hour < 15:
            return True
        if hour == 15 and minute <= 10:
            return True
        return False


@asynccontextmanager
async def lifespan(app: object) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager."""
    settings = Settings()
    bot = TradingBot(settings)

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.initialize()
        await bot.start()
        yield
    finally:
        await bot.stop()


async def main() -> None:
    """Main entry point."""
    settings = Settings()
    bot = TradingBot(settings)

    try:
        await bot.initialize()
        await bot.start()

        # Keep running until interrupted
        while bot.running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())


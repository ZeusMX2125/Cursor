"""Main application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional

from fastapi import FastAPI
from loguru import logger

from api.auth_manager import AuthManager
from api.projectx_service import ProjectXService
from api.topstepx_client import TopstepXClient
from api.websocket_handler import WebSocketHandler
from config.settings import Settings
from core.data_manager import DataManager
from core.order_manager import OrderManager
from core.position_tracker import PositionTracker
from monitoring.performance_tracker import PerformanceTracker
from risk.risk_manager import RiskManager
from strategies.strategy_selector import StrategySelector

# ML Components
from ml.rl_agent import RLAgent
from ml.signal_validator import SignalValidator
from ml.price_predictor import PricePredictor

class TradingBot:
    """Main trading bot orchestrator."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        account_config: Optional[Any] = None,
        activity_logger: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ):
        """
        Initialize trading bot.
        
        Args:
            settings: Optional Settings instance. If not provided, creates default Settings.
            account_config: Optional AccountConfig for multi-account support.
        """
        self.settings = settings or Settings()
        self.account_config = account_config
        self.running = False
        self.activity_logger = activity_logger
        
        # Initialize Auth Manager first (needed for API Client)
        self.auth_manager = AuthManager(self.settings)
        
        # Initialize API Client (requires settings and auth_manager)
        self.api_client = TopstepXClient(self.settings, self.auth_manager)
        self.projectx_service = ProjectXService(self.api_client)
        
        # Initialize Core Components
        self.data_manager = DataManager(self.settings)
        self.position_tracker = PositionTracker(self.settings, self.api_client)
        self.risk_manager = RiskManager(self.settings, self.position_tracker)
        
        # Initialize ML Components
        self.rl_agent = RLAgent()
        self.signal_validator = SignalValidator()
        self.price_predictor = PricePredictor()
        
        # Load Models
        # Non-blocking loading or async if possible, but simple for now
        try:
            self.rl_agent.load_model()
            self.signal_validator.load_model()
            self.price_predictor.load_model()
        except Exception as e:
            logger.warning(f"Failed to load some ML models: {e}")

        # Initialize Order Manager with RL Agent
        self.order_manager = OrderManager(
            self.settings, 
            self.api_client, 
            self.risk_manager, 
            self.position_tracker,
            rl_agent=self.rl_agent
        )
        
        self.performance_tracker = PerformanceTracker(self.settings)
        
        # Initialize Strategies
        self.strategy_selector = StrategySelector(
            self.settings, 
            self.data_manager, 
            self.risk_manager
        )
        
        # WebSocket Handler
        self.ws_handler = WebSocketHandler(
            self.settings, 
            self.auth_manager, 
            self.api_client
        )

    async def start(self) -> None:
        """Start the trading bot."""
        logger.info("Starting ALGOX Trading Bot...")
        self.running = True
        
        # Login
        await self.auth_manager.login()
        
        # Start WebSocket
        await self.ws_handler.connect()
        
        # Start loops
        asyncio.create_task(self._trading_loop())
        asyncio.create_task(self._data_loop())
        
        logger.info("Bot started successfully.")
        await self._log_activity(
            {
                "type": "bot_initialized",
                "message": "Trading bot authenticated and websocket connected.",
            }
        )

    async def stop(self) -> None:
        """Stop the trading bot."""
        self.running = False
        await self.ws_handler.disconnect()
        logger.info("Trading bot stopped")
        await self._log_activity({"type": "bot_stopped", "message": "Bot stopped via API."})

    async def _log_activity(self, activity: Dict[str, Any]) -> None:
        """Forward bot activity details to the account manager (if available)."""
        if not self.activity_logger:
            return
        try:
            payload = dict(activity)
            payload.setdefault("timestamp", datetime.utcnow().isoformat())
            await self.activity_logger(payload)
        except Exception as exc:
            logger.debug(f"Unable to emit bot activity: {exc}")

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
                    signal_payload = signal.to_dict() if hasattr(signal, "to_dict") else dict(signal)
                    market_features = {}
                    if hasattr(signal, "metadata") and "market_features" in signal.metadata:
                        market_features = signal.metadata["market_features"]
                    
                    is_valid, conf = self.signal_validator.validate_signal(signal_payload, market_features)
                    if not is_valid:
                        logger.info(f"Signal rejected by ML Validator: {signal_payload.get('symbol')} {signal_payload.get('side')} ({conf:.2f})")
                        await self._log_activity(
                            {
                                "type": "signal_rejected_ml",
                                "symbol": signal_payload.get("symbol"),
                                "side": signal_payload.get("side"),
                                "confidence": conf,
                            }
                        )
                        continue
                    
                    if not await self.risk_manager.check_trade_risk(signal_payload):
                        await self._log_activity(
                            {
                                "type": "signal_rejected_risk",
                                "symbol": signal_payload.get("symbol"),
                                "side": signal_payload.get("side"),
                            }
                        )
                        continue

                    order_id = await self.order_manager.execute_signal(signal_payload, skip_risk_check=True)
                    if order_id:
                        await self._log_activity(
                            {
                                "type": "order_submitted",
                                "symbol": signal_payload.get("symbol"),
                                "side": signal_payload.get("side"),
                                "order_id": order_id,
                                "quantity": signal_payload.get("quantity"),
                            }
                        )
                    else:
                        await self._log_activity(
                            {
                                "type": "order_failed",
                                "symbol": signal_payload.get("symbol"),
                                "side": signal_payload.get("side"),
                                "message": "Order execution returned no ID",
                            }
                        )

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
    # Startup
    bot = TradingBot()
    # Store bot instance in app state or global variable
    # For now, we rely on app.py to initialize its own services or import this bot
    # Ideally, app.py should import `bot` from here or main.py should launch app.
    
    # Since app.py is the entry point for uvicorn in the current setup, 
    # we should ensure app.py initializes these components.
    
    # This main.py seems to be a standalone runner or alternative entry point.
    # I will assume app.py is the main web server and this is the background worker logic.
    
    yield
    
    # Shutdown
    await bot.stop()

if __name__ == "__main__":
    import uvicorn
    # This entry point starts the bot process directly, not via app.py
    # But typically we want one process.
    bot = TradingBot()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.start())
    loop.run_forever()

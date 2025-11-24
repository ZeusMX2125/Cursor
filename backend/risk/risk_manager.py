"""Central risk manager (Singleton) for enforcing Topstep rules."""

import asyncio
from datetime import datetime, time
from typing import Dict, Optional

import pytz
from loguru import logger

from config.settings import Settings
from core.position_tracker import PositionTracker


class RiskManager:
    """
    Central Risk Manager (Singleton).

    Enforces:
    - Daily Loss Limit (DLL)
    - Trailing Max Drawdown (MLL)
    - Consistency Rule
    - Time-based restrictions
    - Position sizing
    """

    _instance: Optional["RiskManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls, settings: Settings, position_tracker: PositionTracker):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: Settings, position_tracker: PositionTracker):
        if hasattr(self, "_initialized"):
            return

        self.settings = settings
        self.position_tracker = position_tracker
        self.ct_tz = pytz.timezone(settings.timezone)

        # Risk tracking
        self.high_water_mark: float = settings.account_size
        self.daily_pnl: float = 0.0
        self.total_pnl: float = 0.0
        self.best_day_profit: float = 0.0
        self.consecutive_losses: int = 0
        self.trading_halted: bool = False
        self.trading_halted_reason: str = ""

        # Daily tracking
        self.current_date: Optional[datetime] = None
        self.daily_start_balance: float = settings.account_size

        self._initialized = True
        logger.info("Risk Manager initialized")

    async def can_trade(self) -> bool:
        """Check if trading is allowed."""
        # Check if trading is halted
        if self.trading_halted:
            return False

        # Check trading hours
        if not self._is_trading_hours():
            return False

        # Check daily loss limit (95% threshold)
        if abs(self.daily_pnl) >= self.settings.daily_loss_limit * 0.95:
            await self._halt_trading("Approaching daily loss limit")
            return False

        # Check trailing max drawdown (95% threshold)
        current_balance = self.settings.account_size + self.total_pnl
        max_allowed_loss = self.high_water_mark - self.settings.max_drawdown_limit

        if current_balance <= max_allowed_loss * 1.05:  # 5% buffer
            await self._halt_trading("Approaching trailing max drawdown")
            return False

        # Check consecutive losses
        if self.consecutive_losses >= 3:
            await self._halt_trading("3 consecutive losses - circuit breaker")
            return False

        return True

    async def check_trade_risk(self, signal: Dict) -> bool:
        """Check if a trade signal passes risk checks."""
        if not await self.can_trade():
            return False

        # Check position size limits
        quantity = await self.calculate_position_size(signal)
        if quantity <= 0:
            return False

        # Check if we're too close to market close
        if self._is_near_market_close():
            return False

        return True

    async def calculate_position_size(self, signal: Dict) -> int:
        """Calculate position size based on risk parameters."""
        try:
            # Get current account balance
            current_balance = (
                self.settings.account_size
                + self.total_pnl
                + self.position_tracker.get_total_unrealized_pnl()
            )

            # Calculate risk per trade (1.5% of balance)
            risk_per_trade = current_balance * (
                self.settings.risk_per_trade_percent / 100
            )

            # Calculate stop distance
            entry_price = signal.get("entry_price", 0)
            stop_loss = signal.get("stop_loss", 0)
            stop_distance = abs(entry_price - stop_loss)

            if stop_distance == 0:
                return 0

            # Get tick value for symbol
            symbol = signal.get("symbol", "")
            tick_value = self._get_tick_value(symbol)

            # Calculate risk per contract
            risk_per_contract = stop_distance * tick_value

            if risk_per_contract == 0:
                return 0

            # Calculate number of contracts
            contracts = int(risk_per_trade / risk_per_contract)

            # Apply scaling plan limits
            max_contracts = self._get_max_contracts_for_balance(current_balance)
            contracts = min(contracts, max_contracts, self.settings.max_position_size)
            contracts = max(contracts, self.settings.min_position_size)

            # Check daily loss limit remaining
            remaining_daily_risk = (
                self.settings.daily_loss_limit - abs(self.daily_pnl)
            ) * 0.8  # 80% buffer

            if risk_per_contract * contracts > remaining_daily_risk:
                contracts = int(remaining_daily_risk / risk_per_contract)
                contracts = max(contracts, 0)

            return contracts

        except Exception as e:
            logger.error(f"Error calculating position size: {e}", exc_info=True)
            return 0

    def _get_tick_value(self, symbol: str) -> float:
        """Get tick value for a symbol."""
        tick_values = {
            "MES": 5.0,  # $5 per tick
            "MNQ": 2.0,  # $2 per tick
            "MGC": 1.0,  # $1 per tick
        }
        return tick_values.get(symbol, 1.0)

    def _get_max_contracts_for_balance(self, balance: float) -> int:
        """Get max contracts based on scaling plan."""
        # $50K Combine scaling plan
        if balance < 1500:
            return 2
        elif balance < 3000:
            return 3
        elif balance < 5000:
            return 4
        else:
            return 5

    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        now = datetime.now(self.ct_tz)
        hour = now.hour
        minute = now.minute

        # Trading hours: 5:00 PM CT (previous day) to 3:10 PM CT (current day)
        if hour >= 17 or hour < 15:
            return True
        if hour == 15 and minute <= 10:
            return True
        return False

    def _is_near_market_close(self) -> bool:
        """Check if we're too close to market close (3:05 PM CT)."""
        now = datetime.now(self.ct_tz)
        close_time = time(15, 5)  # 3:05 PM CT

        if now.time() >= close_time:
            return True

        # Don't allow new trades after 2:45 PM CT
        if now.hour == 14 and now.minute >= 45:
            return True

        return False

    async def update_pnl(self, realized_pnl: float) -> None:
        """Update P&L tracking."""
        self.total_pnl += realized_pnl
        self.daily_pnl += realized_pnl

        # Update high water mark
        current_balance = self.settings.account_size + self.total_pnl
        if current_balance > self.high_water_mark:
            self.high_water_mark = current_balance

        # Track best day profit
        if self.daily_pnl > self.best_day_profit:
            self.best_day_profit = self.daily_pnl

        # Track consecutive losses
        if realized_pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Check consistency rule
        if self.total_pnl > 0:
            consistency_ratio = self.best_day_profit / self.total_pnl
            if consistency_ratio > self.settings.consistency_threshold:
                logger.warning(
                    f"Consistency rule approaching: {consistency_ratio:.2%}"
                )

    async def reset_daily_tracking(self) -> None:
        """Reset daily tracking at start of new trading day."""
        today = datetime.now(self.ct_tz).date()

        if self.current_date != today:
            self.current_date = today
            self.daily_pnl = 0.0
            self.daily_start_balance = (
                self.settings.account_size + self.total_pnl
            )
            self.consecutive_losses = 0
            self.trading_halted = False
            self.trading_halted_reason = ""
            logger.info("Daily tracking reset")

    async def _halt_trading(self, reason: str) -> None:
        """Halt trading with a reason."""
        if not self.trading_halted:
            self.trading_halted = True
            self.trading_halted_reason = reason
            logger.critical(f"Trading halted: {reason}")

    async def liquidate_all_positions(self) -> None:
        """Force liquidate all positions (emergency)."""
        logger.critical("EMERGENCY: Liquidating all positions")
        # This will be called by order manager
        await self._halt_trading("Emergency liquidation")


"""Opening Range Breakout (ORB) strategy implementation."""

from datetime import datetime, time
from typing import Optional

import polars as pl
import pytz
from loguru import logger

from strategies.base_strategy import BaseStrategy, TradingSignal


class OpeningRangeBreakoutStrategy(BaseStrategy):
    """
    Opening Range Breakout Strategy.

    Time Window: 9:30-9:45 AM ET (8:30-8:45 AM CT)
    Logic:
    1. Identify 15-minute opening range
    2. Breakout above/below range → trade in direction
    3. Stop: Just beyond range boundaries
    4. Target: 1:1 or 1.5:1 R:R
    Best For: MES, MNQ morning session
    """

    def __init__(self, symbols: list):
        super().__init__("Opening Range Breakout", symbols)
        self.ct_tz = pytz.timezone("America/Chicago")
        self.range_start = time(8, 30)  # 8:30 AM CT
        self.range_end = time(8, 45)  # 8:45 AM CT
        self.trading_end = time(10, 0)  # Stop trading after 10 AM CT
        self.opening_ranges: dict = {}  # Store opening range per symbol

    def is_in_trading_window(self) -> bool:
        """Check if current time is within trading window."""
        now = datetime.now(self.ct_tz).time()
        return self.range_start <= now <= self.trading_end

    async def analyze(
        self, symbol: str, bars: pl.DataFrame
    ) -> Optional[TradingSignal]:
        """Analyze market data for ORB setup."""
        if not self.enabled or not self.is_in_trading_window():
            return None

        if bars.is_empty():
            return None

        try:
            now = datetime.now(self.ct_tz).time()

            # Define opening range during 8:30-8:45 AM CT
            if self.range_start <= now <= self.range_end:
                # Calculate opening range
                range_bars = bars.filter(
                    (pl.col("timestamp").dt.hour() == 8)
                    & (pl.col("timestamp").dt.minute() >= 30)
                    & (pl.col("timestamp").dt.minute() <= 45)
                )

                if not range_bars.is_empty():
                    range_high = range_bars["high"].max()
                    range_low = range_bars["low"].min()
                    self.opening_ranges[symbol] = {
                        "high": range_high,
                        "low": range_low,
                    }
                return None  # Wait for breakout after range is established

            # After range is established, look for breakouts
            if symbol not in self.opening_ranges:
                return None

            range_high = self.opening_ranges[symbol]["high"]
            range_low = self.opening_ranges[symbol]["low"]
            current_price = bars["close"].tail(1).item()

            # Calculate range size for stop placement
            range_size = range_high - range_low

            # Bullish breakout
            if current_price > range_high:
                entry_price = current_price
                stop_loss = range_low - range_size * 0.1  # Slightly below range
                take_profit = entry_price + 1.5 * (entry_price - stop_loss)  # 1.5:1 R:R

                return TradingSignal(
                    symbol=symbol,
                    side="BUY",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_type="MARKET",
                    confidence=0.75,
                    strategy_name=self.name,
                )

            # Bearish breakout
            elif current_price < range_low:
                entry_price = current_price
                stop_loss = range_high + range_size * 0.1  # Slightly above range
                take_profit = entry_price - 1.5 * (stop_loss - entry_price)  # 1.5:1 R:R

                return TradingSignal(
                    symbol=symbol,
                    side="SELL",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_type="MARKET",
                    confidence=0.75,
                    strategy_name=self.name,
                )

        except Exception as e:
            logger.error(f"Error in ORB analysis: {e}", exc_info=True)

        return None


"""ICT Silver Bullet strategy implementation."""

from datetime import datetime, time
from typing import Optional

import polars as pl
import pytz
from loguru import logger

from strategies.base_strategy import BaseStrategy, TradingSignal


class ICTSilverBulletStrategy(BaseStrategy):
    """
    ICT Silver Bullet Strategy.

    Time Window: 10:00 AM - 11:00 AM EST (9:00-10:00 AM CT)
    Logic:
    1. Detect Liquidity Sweep (break of 60m high/low)
    2. Detect Displacement (3+ consecutive candles in same direction)
    3. Detect Fair Value Gap (FVG) in 3-candle sequence
    4. Entry: Limit order at FVG start
    5. Stop: Beyond liquidity sweep
    6. Target: 2:1 R:R minimum
    """

    def __init__(self, symbols: list):
        super().__init__("ICT Silver Bullet", symbols)
        self.ct_tz = pytz.timezone("America/Chicago")
        self.window_start = time(9, 0)  # 9:00 AM CT
        self.window_end = time(10, 0)  # 10:00 AM CT

    def is_in_trading_window(self) -> bool:
        """Check if current time is within 9-10 AM CT window."""
        now = datetime.now(self.ct_tz).time()
        return self.window_start <= now <= self.window_end

    async def analyze(
        self, symbol: str, bars: pl.DataFrame
    ) -> Optional[TradingSignal]:
        """Analyze market data for ICT Silver Bullet setup."""
        if not self.enabled or not self.is_in_trading_window():
            return None

        if bars.is_empty() or len(bars) < 60:
            return None

        try:
            # Get 60-minute high/low for liquidity sweep detection
            recent_60m = bars.tail(60)
            high_60m = recent_60m["high"].max()
            low_60m = recent_60m["low"].min()

            # Get latest price
            current_price = bars["close"].tail(1).item()

            # Detect liquidity sweep
            liquidity_swept_high = current_price > high_60m
            liquidity_swept_low = current_price < low_60m

            if not (liquidity_swept_high or liquidity_swept_low):
                return None

            # Detect displacement (3+ consecutive candles in same direction)
            recent_5 = bars.tail(5)
            displacement_up = all(
                recent_5["close"].tail(3) > recent_5["close"].shift(1).tail(3)
            )
            displacement_down = all(
                recent_5["close"].tail(3) < recent_5["close"].shift(1).tail(3)
            )

            if not (displacement_up or displacement_down):
                return None

            # Detect Fair Value Gap (FVG)
            fvg = self._detect_fvg(bars.tail(10))
            if not fvg:
                return None

            # Determine direction
            if liquidity_swept_low and displacement_up and fvg["direction"] == "up":
                # Bullish setup
                entry_price = fvg["start"]
                stop_loss = low_60m - 5  # 5 ticks below liquidity sweep
                take_profit = entry_price + 2 * (entry_price - stop_loss)  # 2:1 R:R

                return TradingSignal(
                    symbol=symbol,
                    side="BUY",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_type="LIMIT",
                    confidence=0.8,
                    strategy_name=self.name,
                )

            elif liquidity_swept_high and displacement_down and fvg["direction"] == "down":
                # Bearish setup
                entry_price = fvg["start"]
                stop_loss = high_60m + 5  # 5 ticks above liquidity sweep
                take_profit = entry_price - 2 * (stop_loss - entry_price)  # 2:1 R:R

                return TradingSignal(
                    symbol=symbol,
                    side="SELL",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_type="LIMIT",
                    confidence=0.8,
                    strategy_name=self.name,
                )

        except Exception as e:
            logger.error(f"Error in ICT Silver Bullet analysis: {e}", exc_info=True)

        return None

    def _detect_fvg(self, bars: pl.DataFrame) -> Optional[dict]:
        """Detect Fair Value Gap in 3-candle sequence."""
        if len(bars) < 3:
            return None

        # Get last 3 candles
        c1 = bars.tail(3).head(1)
        c2 = bars.tail(2).head(1)
        c3 = bars.tail(1)

        c1_high = c1["high"].item()
        c1_low = c1["low"].item()
        c2_high = c2["high"].item()
        c2_low = c2["low"].item()
        c3_high = c3["high"].item()
        c3_low = c3["low"].item()

        # Bullish FVG: c1 high < c3 low (gap between c1 and c3)
        if c1_high < c3_low:
            return {
                "direction": "up",
                "start": c1_high,
                "end": c3_low,
            }

        # Bearish FVG: c1 low > c3 high (gap between c1 and c3)
        if c1_low > c3_high:
            return {
                "direction": "down",
                "start": c1_low,
                "end": c3_high,
            }

        return None


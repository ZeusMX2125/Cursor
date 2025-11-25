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
            # Check if 3 most recent candles closed higher than previous 3 (simplistic displacement)
            # Better check: consecutive bullish/bearish candles with large bodies
            
            closes = recent_5["close"]
            opens = recent_5["open"]
            
            # Last 3 candles
            c1 = closes[-1] > opens[-1]
            c2 = closes[-2] > opens[-2]
            c3 = closes[-3] > opens[-3]
            
            displacement_up = c1 and c2 and c3
            
            c1_down = closes[-1] < opens[-1]
            c2_down = closes[-2] < opens[-2]
            c3_down = closes[-3] < opens[-3]
            
            displacement_down = c1_down and c2_down and c3_down

            if not (displacement_up or displacement_down):
                return None

            # Detect Fair Value Gap (FVG)
            fvg = self._detect_fvg(bars.tail(10))
            if not fvg:
                return None

            signal = None
            
            # Determine direction
            if liquidity_swept_low and displacement_up and fvg["direction"] == "up":
                # Bullish setup
                entry_price = fvg["start"]
                stop_loss = low_60m - 0.25 * 4 * 5 # 5 ticks below liquidity sweep (assuming 0.25 tick)
                take_profit = entry_price + 2 * (entry_price - stop_loss)  # 2:1 R:R

                signal = TradingSignal(
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
                stop_loss = high_60m + 0.25 * 4 * 5 # 5 ticks above liquidity sweep
                take_profit = entry_price - 2 * (stop_loss - entry_price)  # 2:1 R:R

                signal = TradingSignal(
                    symbol=symbol,
                    side="SELL",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_type="LIMIT",
                    confidence=0.8,
                    strategy_name=self.name,
                )
                
            if signal:
                return self.enrich_signal(signal, bars)

        except Exception as e:
            logger.error(f"Error in ICT Silver Bullet analysis: {e}", exc_info=True)

        return None

    def _detect_fvg(self, bars: pl.DataFrame) -> Optional[dict]:
        """Detect Fair Value Gap in 3-candle sequence."""
        if len(bars) < 3:
            return None

        # Get last 3 candles
        # c1 is 3rd to last (index -3), c2 is 2nd to last (index -2), c3 is last (index -1)
        
        # Need to ensure we are looking at the candles causing displacement
        # Usually FVG is formed by the big move.
        
        c1_high = bars["high"][-3]
        c1_low = bars["low"][-3]
        c3_high = bars["high"][-1]
        c3_low = bars["low"][-1]

        # Bullish FVG: c1 high < c3 low (gap between c1 and c3)
        if c1_high < c3_low:
            return {
                "direction": "up",
                "start": c1_high, # Entry at top of c1? No, usually entry is at retest of FVG which is between c1_high and c3_low.
                # Standard ICT entry is at the "start" of the gap relative to price coming back?
                # Price moves UP. Gap is c1_high to c3_low. Retest comes DOWN.
                # So entry is c3_low (top of gap) or c1_high (bottom of gap)?
                # Usually entry limit is placed at the "beginning" of the gap which is c3_low? No, that's immediate.
                # Usually we wait for retracement into the gap.
                # Limit entry at c3_low or even deeper (50%).
                # Let's simplify: Limit at c3_low (top of gap) for aggressive, or c1_high + (c3_low-c1_high)/2 for conservative.
                # Let's use Top of Gap (c3_low) to ensure fill if it touches.
                "end": c3_low, # Actually start/end terminology is tricky.
                "start": c3_low, # Limit Price
            }

        # Bearish FVG: c1 low > c3 high (gap between c1 and c3)
        if c1_low > c3_high:
            return {
                "direction": "down",
                "start": c3_high, # Limit Price (bottom of gap)
                "end": c1_low,
            }

        return None

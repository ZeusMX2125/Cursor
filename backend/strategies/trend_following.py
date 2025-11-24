"""Trend Following strategy implementation."""

from typing import Optional

import polars as pl
from loguru import logger

from strategies.base_strategy import BaseStrategy, TradingSignal


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy.

    Logic:
    1. Multi-timeframe EMA alignment (10/20/50/200)
    2. Trade pullbacks in trend direction
    3. Stop: Below pullback low (uptrend) or above pullback high (downtrend)
    4. Target: New high/low extension
    Best For: All contracts during strong directional moves
    """

    def __init__(self, symbols: list):
        super().__init__("Trend Following", symbols)

    def is_in_trading_window(self) -> bool:
        """Trend following can trade throughout the day."""
        return True

    async def analyze(
        self, symbol: str, bars: pl.DataFrame
    ) -> Optional[TradingSignal]:
        """Analyze market data for trend following setup."""
        if not self.enabled:
            return None

        if bars.is_empty() or len(bars) < 200:
            return None

        try:
            # Calculate EMAs
            ema_10 = bars["close"].ewm_mean(span=10)
            ema_20 = bars["close"].ewm_mean(span=20)
            ema_50 = bars["close"].ewm_mean(span=50)
            ema_200 = bars["close"].ewm_mean(span=200)

            # Get latest values
            current_price = bars["close"].tail(1).item()
            ema_10_val = ema_10.tail(1).item()
            ema_20_val = ema_20.tail(1).item()
            ema_50_val = ema_50.tail(1).item()
            ema_200_val = ema_200.tail(1).item()

            # Calculate ATR for stop placement
            atr = self._calculate_atr(bars, period=14)
            if atr is None:
                return None

            # Check for uptrend (all EMAs aligned upward)
            uptrend = (
                current_price > ema_10_val
                and ema_10_val > ema_20_val
                and ema_20_val > ema_50_val
                and ema_50_val > ema_200_val
            )

            # Check for downtrend (all EMAs aligned downward)
            downtrend = (
                current_price < ema_10_val
                and ema_10_val < ema_20_val
                and ema_20_val < ema_50_val
                and ema_50_val < ema_200_val
            )

            # Look for pullback in uptrend
            if uptrend:
                # Check if price pulled back to EMA 20 or 50
                recent_low = bars["low"].tail(10).min()
                pullback_to_ema20 = abs(current_price - ema_20_val) / ema_20_val < 0.002
                pullback_to_ema50 = abs(current_price - ema_50_val) / ema_50_val < 0.002

                if pullback_to_ema20 or pullback_to_ema50:
                    entry_price = current_price
                    stop_loss = recent_low - atr * 0.5
                    take_profit = entry_price + 2 * (entry_price - stop_loss)  # 2:1 R:R

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

            # Look for pullback in downtrend
            elif downtrend:
                # Check if price pulled back to EMA 20 or 50
                recent_high = bars["high"].tail(10).max()
                pullback_to_ema20 = abs(current_price - ema_20_val) / ema_20_val < 0.002
                pullback_to_ema50 = abs(current_price - ema_50_val) / ema_50_val < 0.002

                if pullback_to_ema20 or pullback_to_ema50:
                    entry_price = current_price
                    stop_loss = recent_high + atr * 0.5
                    take_profit = entry_price - 2 * (stop_loss - entry_price)  # 2:1 R:R

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
            logger.error(f"Error in Trend Following analysis: {e}", exc_info=True)

        return None

    def _calculate_atr(self, bars: pl.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate Average True Range."""
        if len(bars) < period + 1:
            return None

        high_low = bars["high"] - bars["low"]
        high_close = (bars["high"] - bars["close"].shift(1)).abs()
        low_close = (bars["low"] - bars["close"].shift(1)).abs()

        tr = pl.concat([high_low, high_close, low_close], how="horizontal").max(axis=1)
        atr = tr.rolling_mean(period).tail(1).item()

        return atr


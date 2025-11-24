"""VWAP Mean Reversion strategy implementation."""

from typing import Optional

import polars as pl
from loguru import logger

from strategies.base_strategy import BaseStrategy, TradingSignal


class VWAPMeanReversionStrategy(BaseStrategy):
    """
    VWAP Mean Reversion Strategy.

    Logic:
    1. Calculate intraday VWAP
    2. Entry: Pullback to VWAP + RSI(14) confirmation
    3. Stop: 1.5x ATR below/above VWAP
    4. Target: 1.5:1 R:R
    Best For: MNQ, MES during consolidation
    """

    def __init__(self, symbols: list):
        super().__init__("VWAP Mean Reversion", symbols)

    def is_in_trading_window(self) -> bool:
        """VWAP strategy can trade throughout the day."""
        return True

    async def analyze(
        self, symbol: str, bars: pl.DataFrame
    ) -> Optional[TradingSignal]:
        """Analyze market data for VWAP mean reversion setup."""
        if not self.enabled:
            return None

        if bars.is_empty() or len(bars) < 20:
            return None

        try:
            # Calculate VWAP (Volume Weighted Average Price)
            vwap = self._calculate_vwap(bars)

            # Calculate RSI(14)
            rsi = self._calculate_rsi(bars["close"], period=14)

            # Calculate ATR(14)
            atr = self._calculate_atr(bars, period=14)

            if vwap is None or rsi is None or atr is None:
                return None

            current_price = bars["close"].tail(1).item()
            current_rsi = rsi.tail(1).item()

            # Check for pullback to VWAP
            price_diff_pct = abs(current_price - vwap) / vwap * 100

            # Long setup: Price near VWAP from above, RSI oversold
            if (
                current_price <= vwap * 1.001  # Within 0.1% of VWAP
                and current_rsi < 40  # Oversold
                and price_diff_pct < 0.2  # Close to VWAP
            ):
                entry_price = current_price
                stop_loss = entry_price - 1.5 * atr
                take_profit = entry_price + 1.5 * (entry_price - stop_loss)  # 1.5:1 R:R

                return TradingSignal(
                    symbol=symbol,
                    side="BUY",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_type="MARKET",
                    confidence=0.7,
                    strategy_name=self.name,
                )

            # Short setup: Price near VWAP from below, RSI overbought
            elif (
                current_price >= vwap * 0.999  # Within 0.1% of VWAP
                and current_rsi > 60  # Overbought
                and price_diff_pct < 0.2  # Close to VWAP
            ):
                entry_price = current_price
                stop_loss = entry_price + 1.5 * atr
                take_profit = entry_price - 1.5 * (stop_loss - entry_price)  # 1.5:1 R:R

                return TradingSignal(
                    symbol=symbol,
                    side="SELL",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_type="MARKET",
                    confidence=0.7,
                    strategy_name=self.name,
                )

        except Exception as e:
            logger.error(f"Error in VWAP Mean Reversion analysis: {e}", exc_info=True)

        return None

    def _calculate_vwap(self, bars: pl.DataFrame) -> Optional[float]:
        """Calculate Volume Weighted Average Price."""
        if "volume" not in bars.columns:
            return None

        typical_price = (bars["high"] + bars["low"] + bars["close"]) / 3
        vwap = (typical_price * bars["volume"]).sum() / bars["volume"].sum()
        return vwap.item()

    def _calculate_rsi(self, prices: pl.Series, period: int = 14) -> Optional[pl.Series]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return None

        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling_mean(period)
        avg_loss = loss.rolling_mean(period)

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

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


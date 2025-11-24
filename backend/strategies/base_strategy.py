"""Base strategy class for all trading strategies."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import polars as pl


class TradingSignal:
    """Represents a trading signal."""

    def __init__(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        order_type: str = "MARKET",
        confidence: float = 1.0,
        strategy_name: str = "",
    ):
        self.symbol = symbol
        self.side = side  # "BUY" or "SELL"
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.order_type = order_type
        self.confidence = confidence
        self.strategy_name = strategy_name

    def to_dict(self) -> Dict:
        """Convert signal to dictionary."""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "order_type": self.order_type,
            "confidence": self.confidence,
            "strategy_name": self.strategy_name,
        }


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, name: str, symbols: List[str]):
        self.name = name
        self.symbols = symbols
        self.enabled = True

    @abstractmethod
    async def analyze(
        self, symbol: str, bars: pl.DataFrame
    ) -> Optional[TradingSignal]:
        """
        Analyze market data and generate trading signals.

        Args:
            symbol: Trading symbol (MNQ, MES, MGC)
            bars: DataFrame with OHLCV data

        Returns:
            TradingSignal if a setup is found, None otherwise
        """
        pass

    @abstractmethod
    def is_in_trading_window(self) -> bool:
        """Check if current time is within strategy's trading window."""
        pass

    def enable(self) -> None:
        """Enable the strategy."""
        self.enabled = True

    def disable(self) -> None:
        """Disable the strategy."""
        self.enabled = False


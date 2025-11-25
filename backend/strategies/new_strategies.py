"""Statistical Arbitrage Strategy."""

from typing import Optional, Dict, List
import polars as pl
import numpy as np
from loguru import logger
from strategies.base_strategy import BaseStrategy, TradingSignal

class StatisticalArbitrageStrategy(BaseStrategy):
    """
    Statistical Arbitrage (Mean Reversion of Spread).
    
    Logic:
    1. Track correlation and spread between two symbols (e.g. NQ and ES).
    2. Calculate Z-score of the spread (Spread - Mean) / StdDev.
    3. If Z-score > 2, Short Spread (Short A, Long B).
    4. If Z-score < -2, Long Spread (Long A, Short B).
    5. Exit when Z-score returns to near 0.
    """

    def __init__(self, symbols: List[str], symbol_a: str = "NQ", symbol_b: str = "ES", lookback: int = 20):
        super().__init__("Statistical Arbitrage", symbols)
        self.symbol_a = symbol_a
        self.symbol_b = symbol_b
        self.lookback = lookback
        self.z_score_threshold = 2.0
        self.positions = {} # Track spread positions

    def is_in_trading_window(self) -> bool:
        return True # Always active

    async def analyze(
        self, symbol: str, bars: pl.DataFrame
    ) -> Optional[TradingSignal]:
        # We need data for BOTH symbols to make a decision.
        # This `analyze` is called per symbol. 
        # We need a way to access the OTHER symbol's data.
        # Currently BaseStrategy only gets `bars` for the current symbol.
        # We'll need to rely on DataManager or cache.
        # For this implementation, we'll assume we can't easily access cross-symbol data here directly
        # without refactoring StrategySelector to pass multiple dataframes.
        
        # Placeholder for complex cross-symbol logic:
        # We would check if we have data for both A and B.
        # Since we are limited by the current architecture, we'll implement a simplified version
        # or mark as requiring architecture change.
        
        return None 

    # For the purpose of this plan, let's implement a single-asset Mean Reversion which is a component of StatArb
    # Or implemented Pairs Trading properly if we had access to both.
    
    # Alternative: This strategy is special and needs access to DataManager.
    # StrategySelector passes DataManager to constructor.
    # We can fetch data there.
    pass

class PairsTradingStrategy(BaseStrategy):
    """
    Pairs Trading Strategy (Placeholder).
    Requires multi-asset data access.
    """
    def __init__(self, symbols: List[str]):
        super().__init__("Pairs Trading", symbols)

    def is_in_trading_window(self) -> bool:
        return True

    async def analyze(self, symbol: str, bars: pl.DataFrame) -> Optional[TradingSignal]:
        return None

# Since we can't easily implement multi-asset strategies without major refactoring of `analyze` signature 
# or data access, let's implement "Enhanced Mean Reversion" (single asset) and "Momentum" as requested.

class EnhancedMeanReversionStrategy(BaseStrategy):
    """
    Enhanced Mean Reversion using Bollinger Bands + RSI + ML.
    """
    
    def __init__(self, symbols: List[str]):
        super().__init__("Enhanced Mean Reversion", symbols)
        
    def is_in_trading_window(self) -> bool:
        return True
        
    async def analyze(self, symbol: str, bars: pl.DataFrame) -> Optional[TradingSignal]:
        if not self.enabled or len(bars) < 20:
            return None
            
        try:
            # Calculate indicators
            df = self.feature_engineer.calculate_indicators(bars)
            latest = df.tail(1)
            
            close = latest["close"][0]
            bb_lower = latest["bb_lower"][0]
            bb_upper = latest["bb_upper"][0]
            rsi = latest["rsi_14"][0]
            
            # Logic:
            # Long: Price < Lower BB AND RSI < 30
            # Short: Price > Upper BB AND RSI > 70
            
            if close < bb_lower and rsi < 30:
                signal = TradingSignal(
                    symbol=symbol,
                    side="BUY",
                    entry_price=close,
                    stop_loss=close * 0.99,
                    take_profit=close * 1.02,
                    strategy_name=self.name,
                    confidence=0.7 # Base confidence
                )
                return self.enrich_signal(signal, bars)
                
            if close > bb_upper and rsi > 70:
                signal = TradingSignal(
                    symbol=symbol,
                    side="SELL",
                    entry_price=close,
                    stop_loss=close * 1.01,
                    take_profit=close * 0.98,
                    strategy_name=self.name,
                    confidence=0.7
                )
                return self.enrich_signal(signal, bars)
                
        except Exception as e:
            logger.error(f"Mean Reversion Error: {e}")
            
        return None

class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy using ROC and SMA.
    """
    def __init__(self, symbols: List[str]):
        super().__init__("Momentum", symbols)
        
    def is_in_trading_window(self) -> bool:
        return True
        
    async def analyze(self, symbol: str, bars: pl.DataFrame) -> Optional[TradingSignal]:
        if not self.enabled or len(bars) < 50:
            return None
            
        try:
            df = self.feature_engineer.calculate_indicators(bars)
            latest = df.tail(1)
            
            close = latest["close"][0]
            sma_50 = latest["sma_50"][0]
            roc_10 = latest["roc_10"][0]
            
            # Logic:
            # Long: Price > SMA 50 AND ROC(10) > 0.001 (positive momentum)
            # Short: Price < SMA 50 AND ROC(10) < -0.001
            
            if close > sma_50 and roc_10 > 0.001:
                signal = TradingSignal(
                    symbol=symbol,
                    side="BUY",
                    entry_price=close,
                    stop_loss=close * 0.995,
                    take_profit=close * 1.015,
                    strategy_name=self.name
                )
                return self.enrich_signal(signal, bars)
                
            if close < sma_50 and roc_10 < -0.001:
                signal = TradingSignal(
                    symbol=symbol,
                    side="SELL",
                    entry_price=close,
                    stop_loss=close * 1.005,
                    take_profit=close * 0.985,
                    strategy_name=self.name
                )
                return self.enrich_signal(signal, bars)
                
        except Exception as e:
            logger.error(f"Momentum Error: {e}")
            
        return None


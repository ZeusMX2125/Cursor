"""Strategy Framework Enhancements."""

from typing import Dict, List
import numpy as np
from loguru import logger
from strategies.base_strategy import BaseStrategy, TradingSignal

class StrategyEnsemble:
    """
    Manages multiple strategies and combines their signals.
    """
    
    def __init__(self, strategies: List[BaseStrategy]):
        self.strategies = strategies
        self.weights = {s.name: 1.0 for s in strategies}
        self.performance_history = {s.name: [] for s in strategies}
        
    def update_performance(self, strategy_name: str, pnl: float):
        """Update performance history for a strategy."""
        if strategy_name in self.performance_history:
            self.performance_history[strategy_name].append(pnl)
            self._rebalance_weights()
            
    def _rebalance_weights(self):
        """Adjust weights based on recent performance (Sharpe/WinRate)."""
        # Simple logic: Increase weight if last 5 trades net positive
        for name, history in self.performance_history.items():
            if not history:
                continue
            
            recent = history[-5:]
            if sum(recent) > 0:
                self.weights[name] = min(2.0, self.weights[name] * 1.1)
            else:
                self.weights[name] = max(0.5, self.weights[name] * 0.9)
                
        logger.info(f"Rebalanced strategy weights: {self.weights}")

    def combine_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """
        Filter or combine signals based on weights and correlation.
        """
        if not signals:
            return []
            
        # For now, just apply weight to position size or confidence
        final_signals = []
        for signal in signals:
            weight = self.weights.get(signal.strategy_name, 1.0)
            
            # If weight is too low, drop signal
            if weight < 0.6:
                continue
                
            # Adjust confidence based on weight
            signal.confidence *= weight
            
            final_signals.append(signal)
            
        return final_signals


"""AI agent router for per-account AI strategy control."""

from typing import Dict, List, Optional

from loguru import logger

from strategies.base_strategy import TradingSignal
from ml.signal_validator import SignalValidator
from ml.rl_agent import RLAgent
from accounts.models import AccountConfig


class AIAgentRouter:
    """Routes trading signals through different AI agents based on account config."""

    def __init__(self, account_config: AccountConfig):
        self.account_config = account_config
        self.agent_type = account_config.ai_agent_type
        self.signal_validator = None
        self.rl_agent = None

        # Initialize AI agents based on type
        if self.agent_type == "ml_confirmation":
            self.signal_validator = SignalValidator()
            self.signal_validator.load_model()
        elif self.agent_type == "rl_agent":
            self.rl_agent = RLAgent()
            self.rl_agent.load_model()
            self.rl_agent.enabled = True

    async def process_signals(
        self, signals: List[TradingSignal]
    ) -> List[TradingSignal]:
        """
        Process signals through the configured AI agent.

        Args:
            signals: List of trading signals

        Returns:
            Filtered/enhanced signals
        """
        if self.agent_type == "rule_based":
            # No AI filtering, return all signals
            return signals

        elif self.agent_type == "ml_confirmation":
            # Use ML to validate signals
            if not self.signal_validator:
                return signals

            validated_signals = []
            for signal in signals:
                # Get market features (simplified - would need actual market data)
                market_features = self._extract_market_features(signal)

                is_valid, confidence = self.signal_validator.validate_signal(
                    signal.to_dict(), market_features
                )

                if is_valid:
                    signal.confidence = confidence  # Update confidence
                    validated_signals.append(signal)

            return validated_signals

        elif self.agent_type == "rl_agent":
            # Use RL agent for position sizing and exit timing
            if not self.rl_agent or not self.rl_agent.enabled:
                return signals

            enhanced_signals = []
            for signal in signals:
                # Get state for RL agent
                state = self._extract_state(signal)

                # Get action from RL agent
                action = self.rl_agent.get_action(state)

                # Enhance signal with RL recommendations
                signal_dict = signal.to_dict()
                signal_dict["quantity"] = action.get("position_size", signal_dict.get("quantity", 1))
                signal_dict["stop_distance_multiplier"] = action.get("stop_distance_multiplier", 1.5)
                signal_dict["take_profit_ratio"] = action.get("take_profit_ratio", 2.0)

                # Recreate signal with enhanced parameters
                enhanced_signal = TradingSignal(
                    symbol=signal.symbol,
                    side=signal.side,
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    order_type=signal.order_type,
                    confidence=signal.confidence,
                    strategy_name=signal.strategy_name,
                )
                enhanced_signals.append(enhanced_signal)

            return enhanced_signals

        return signals

    def _extract_market_features(self, signal: TradingSignal) -> Dict:
        """Extract market features for ML validation."""
        # Simplified - would need actual market data
        return {
            "current_price": signal.entry_price,
            "sma_10": signal.entry_price * 0.99,
            "sma_20": signal.entry_price * 0.98,
            "rsi_14": 50.0,
            "macd": 0.0,
        }

    def _extract_state(self, signal: TradingSignal) -> Dict:
        """Extract state for RL agent."""
        # Simplified - would need actual account/market state
        return {
            "current_price": signal.entry_price,
            "signal_confidence": signal.confidence,
            "strategy_name": signal.strategy_name,
        }


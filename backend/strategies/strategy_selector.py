"""Strategy selector that coordinates multiple strategies."""

import asyncio
from typing import Dict, List, Optional

from loguru import logger

from core.data_manager import DataManager
from strategies.base_strategy import TradingSignal
from strategies.ict_silver_bullet import ICTSilverBulletStrategy
from strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from strategies.trend_following import TrendFollowingStrategy
from strategies.vwap_mean_reversion import VWAPMeanReversionStrategy
from strategies.ai_agent_router import AIAgentRouter
from config.settings import Settings
from accounts.models import AccountConfig
from typing import Optional


class StrategySelector:
    """Selects and coordinates trading strategies."""

    def __init__(
        self,
        settings: Settings,
        data_manager: DataManager,
        risk_manager,
        account_config: Optional[AccountConfig] = None,
    ):
        self.settings = settings
        self.data_manager = data_manager
        self.risk_manager = risk_manager
        self.account_config = account_config
        self.running = False

        # Initialize all available strategies
        all_strategies = {
            "ict_silver_bullet": ICTSilverBulletStrategy(settings.symbols),
            "vwap_mean_reversion": VWAPMeanReversionStrategy(settings.symbols),
            "opening_range_breakout": OpeningRangeBreakoutStrategy(settings.symbols),
            "trend_following": TrendFollowingStrategy(settings.symbols),
        }

        # Enable only strategies specified in account config
        if account_config and account_config.enabled_strategies:
            self.strategies = [
                all_strategies[strategy_name]
                for strategy_name in account_config.enabled_strategies
                if strategy_name in all_strategies
            ]
        else:
            # Default: enable all strategies
            self.strategies = list(all_strategies.values())

        # Initialize AI agent router if account config provided
        self.ai_router = None
        if account_config:
            self.ai_router = AIAgentRouter(account_config)

        # Enable/disable based on settings
        if not settings.enable_long_entries:
            for strategy in self.strategies:
                # Strategies handle this internally
                pass

        if not settings.enable_short_entries:
            for strategy in self.strategies:
                # Strategies handle this internally
                pass

    async def start(self) -> None:
        """Start the strategy selector."""
        self.running = True
        logger.info("Strategy selector started")

    async def stop(self) -> None:
        """Stop the strategy selector."""
        self.running = False
        logger.info("Strategy selector stopped")

    async def get_signals(self) -> List[TradingSignal]:
        """Get trading signals from all enabled strategies."""
        signals = []

        if not self.running:
            return signals

        try:
            for symbol in self.settings.symbols:
                # Get bars for different timeframes
                bars_1m = await self.data_manager.get_bars(symbol, "1m", limit=200)
                bars_5m = await self.data_manager.get_bars(symbol, "5m", limit=200)

                # Run each strategy
                for strategy in self.strategies:
                    if not strategy.enabled:
                        continue

                    try:
                        # Use 5m bars for most strategies, 1m for scalping
                        bars = bars_5m if len(bars_5m) > len(bars_1m) else bars_1m

                        signal = await strategy.analyze(symbol, bars)
                        if signal:
                            signals.append(signal)
                            logger.info(
                                f"Signal generated: {strategy.name} - {symbol} {signal.side}"
                            )

                    except Exception as e:
                        logger.error(
                            f"Error in strategy {strategy.name}: {e}", exc_info=True
                        )

            # Process through AI agent if configured
            if self.ai_router:
                signals = await self.ai_router.process_signals(signals)

            # Filter signals by confidence and risk
            filtered_signals = await self._filter_signals(signals)

            return filtered_signals

        except Exception as e:
            logger.error(f"Error getting signals: {e}", exc_info=True)
            return []

    async def _filter_signals(
        self, signals: List[TradingSignal]
    ) -> List[TradingSignal]:
        """Filter signals based on confidence and risk."""
        if not signals:
            return []

        # Sort by confidence (highest first)
        signals.sort(key=lambda s: s.confidence, reverse=True)

        # Take only the best signal per symbol
        filtered = []
        symbols_seen = set()

        for signal in signals:
            if signal.symbol not in symbols_seen:
                # Check risk before adding
                signal_dict = signal.to_dict()
                if await self.risk_manager.check_trade_risk(signal_dict):
                    filtered.append(signal)
                    symbols_seen.add(signal.symbol)

        return filtered


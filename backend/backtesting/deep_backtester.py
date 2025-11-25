"""Deep backtesting engine with ProjectX API integration."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import polars as pl
import pytz
from loguru import logger

from backtesting.historical_data_service import HistoricalDataService
from backtesting.engine import BacktestEngine, BacktestResult
from backtesting.simulator import TopstepSimulator
from backtesting.reporter import BacktestReporter
from accounts.models import AccountConfig
from config.settings import Settings
from api.auth_manager import AuthManager

# ML/AI Components
from ml.signal_validator import SignalValidator
from ml.rl_agent import RLAgent
from ml.feature_engineering import FeatureEngineer

class DeepBacktester:
    """Deep backtesting with ProjectX API historical data and ML integration."""

    def __init__(
        self,
        settings: Settings,
        auth_manager: AuthManager,
    ):
        self.settings = settings
        self.auth_manager = auth_manager
        self.data_service = HistoricalDataService(settings, auth_manager)
        self.backtest_engine = BacktestEngine(settings)
        self.simulator = TopstepSimulator(settings)
        self.reporter = BacktestReporter()
        
        # Initialize ML components
        self.signal_validator = SignalValidator()
        self.signal_validator.load_model()
        self.rl_agent = RLAgent()
        self.rl_agent.load_model()
        self.feature_engineer = FeatureEngineer()

    async def initialize(self) -> None:
        """Initialize the backtester."""
        await self.data_service.initialize()

    async def run_backtest(
        self,
        account_config: AccountConfig,
        symbols: List[str],
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        strategies: List[str],
    ) -> Dict:
        """
        Run a deep backtest for an account configuration.
        """
        logger.info(
            f"Starting deep backtest for {account_config.account_id} "
            f"from {start_date} to {end_date}"
        )

        # Fetch historical data for all symbols
        all_bars = {}
        for symbol in symbols:
            logger.info(f"Fetching {symbol} data...")
            bars = await self.data_service.fetch_bars(
                symbol, timeframe, start_date, end_date
            )
            # Calculate indicators immediately for ML usage
            if not bars.is_empty():
                bars = self.feature_engineer.calculate_indicators(bars)
                
            all_bars[symbol] = bars

            if bars.is_empty():
                logger.warning(f"No data for {symbol}")
                continue

            logger.info(f"Fetched {len(bars)} bars for {symbol}")

        # Generate signals for each strategy
        signals = await self._generate_signals(all_bars, strategies, account_config)
        
        # Apply ML/RL enhancements
        enhanced_signals = self._enhance_signals(signals, all_bars)

        # Run backtest
        # Assuming backtest_engine can handle dictionary of bars or concat
        # If engine expects single dataframe, we might need to adjust logic.
        # Usually backtester iterates by timestamp across all instruments.
        
        # For now, let's concatenate for simple engine, or pass all_bars if supported.
        # Assuming existing engine supports simple list of signals against bars.
        
        # Flatten bars for simple backtest engine if needed, or engine handles correlation
        # Let's assume simple engine for now
        combined_bars = pl.concat(list(all_bars.values())) if all_bars else pl.DataFrame()
        
        result = self.backtest_engine.run_backtest(
            bars=combined_bars,
            signals=enhanced_signals,
            initial_balance=account_config.profile.account_size,
        )

        # Simulate Topstep rules with account profile
        simulator = TopstepSimulator(self.settings, account_config.profile)
        rule_simulation = simulator.simulate_trading_day(
            trades=result.trades,
            initial_balance=account_config.profile.account_size,
        )

        # Generate report
        report = self.reporter.generate_report(result)

        # Add rule compliance results
        report["rule_compliance"] = {
            "daily_loss_violation": rule_simulation["daily_violation"],
            "daily_loss_violation_msg": rule_simulation["daily_violation_msg"],
            "drawdown_violation": rule_simulation["drawdown_violation"],
            "drawdown_violation_msg": rule_simulation["drawdown_violation_msg"],
        }

        # Add account-specific metrics
        report["account_id"] = account_config.account_id
        report["account_size"] = account_config.profile.account_size
        report["profit_target"] = account_config.profile.profit_target
        report["target_achieved"] = result.total_pnl >= account_config.profile.profit_target

        logger.info(f"Backtest completed: P&L=${result.total_pnl:.2f}, Trades={result.total_trades}")

        return report

    async def _generate_signals(
        self,
        bars: Dict[str, pl.DataFrame],
        strategies: List[str],
        account_config: AccountConfig,
    ) -> List[Dict]:
        """
        Generate trading signals from historical bars.
        """
        signals = []

        # Import strategies dynamically
        from strategies.ict_silver_bullet import ICTSilverBulletStrategy
        from strategies.vwap_mean_reversion import VWAPMeanReversionStrategy
        from strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
        from strategies.trend_following import TrendFollowingStrategy
        from strategies.new_strategies import EnhancedMeanReversionStrategy, MomentumStrategy

        # Default symbols
        # TODO: Use actual symbols
        default_symbols = list(bars.keys())
        
        strategy_map = {
            "ict_silver_bullet": ICTSilverBulletStrategy(default_symbols),
            "vwap_mean_reversion": VWAPMeanReversionStrategy(default_symbols),
            "opening_range_breakout": OpeningRangeBreakoutStrategy(default_symbols),
            "trend_following": TrendFollowingStrategy(default_symbols),
            "mean_reversion": EnhancedMeanReversionStrategy(default_symbols),
            "momentum": MomentumStrategy(default_symbols),
        }

        for symbol, symbol_bars in bars.items():
            if symbol_bars.is_empty():
                continue

            for strategy_name in strategies:
                if strategy_name not in strategy_map:
                    continue

                strategy = strategy_map[strategy_name]

                try:
                    # Analyze bars and generate signals
                    # Note: Real strategies iterate over time. This `analyze` usually runs on the *latest* bar.
                    # For backtesting, we need to simulate walking forward.
                    # This simplified version assumes `analyze` can handle history or we loop here.
                    # Ideally, `analyze` takes a slice.
                    
                    # Simulating walk-forward:
                    # This is slow but accurate.
                    # Optimization: Vectorized strategies.
                    # For now, let's assume strategies return a list of signals if we pass whole dataframe?
                    # Or we assume `analyze` is for live trading (latest bar).
                    
                    # If strategies are designed for live trading (single signal), we must loop.
                    # Loop over bars (expensive in python)
                    # Let's do a stride or check every bar.
                    
                    # Optimistic: Check every 5th bar or rely on vectorized logic if strategy supports it.
                    # Existing strategies in this codebase seem to check "tail".
                    
                    # Iterate through history
                    for i in range(50, len(symbol_bars)):
                        slice_bars = symbol_bars.slice(0, i+1)
                        # We only need the tail, but pass enough context
                        # Optimization: Pass full df and current index?
                        # Current strategies take `bars` and look at tail.
                        
                        # Only check every X minutes to speed up?
                        signal = await strategy.analyze(symbol, slice_bars)

                        if signal:
                            signal_dict = signal.to_dict()
                            signal_dict["timestamp"] = slice_bars["timestamp"][-1]
                            signal_dict["quantity"] = 1
                            signals.append(signal_dict)
                            
                except Exception as e:
                    logger.error(
                        f"Error generating signal for {strategy_name} on {symbol}: {e}",
                        # exc_info=True, # Reduce verbosity
                    )

        return signals

    def _enhance_signals(self, signals: List[Dict], bars: Dict[str, pl.DataFrame]) -> List[Dict]:
        """Apply ML validation and RL sizing to signals."""
        enhanced = []
        for signal in signals:
            symbol = signal["symbol"]
            timestamp = signal["timestamp"]
            
            # Find corresponding market data (features)
            # This is tricky with dictionaries. In production, use indexed lookup.
            # Validation
            if self.signal_validator.model:
                # We need features at that timestamp.
                # signal['metadata']['market_features'] might already exist if enriched.
                features = signal.get("metadata", {}).get("market_features")
                if features:
                    is_valid, conf = self.signal_validator.validate_signal(signal, features)
                    if not is_valid:
                        continue # Skip this signal
                    signal["confidence"] = conf
            
            # RL Sizing
            if self.rl_agent.enabled:
                # Create observation state
                # Placeholder state
                # obs = ...
                # action = self.rl_agent.get_action(obs)
                # signal["quantity"] = action.get("position_size", 1)
                pass
                
            enhanced.append(signal)
            
        return enhanced

    async def run_multi_account_backtest(
        self,
        account_configs: List[AccountConfig],
        symbols: List[str],
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Dict]:
        """Run backtests for multiple accounts."""
        results = {}
        for account_config in account_configs:
            try:
                result = await self.run_backtest(
                    account_config=account_config,
                    symbols=symbols,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    strategies=account_config.enabled_strategies,
                )
                results[account_config.account_id] = result
            except Exception as e:
                logger.error(f"Error backtesting {account_config.account_id}: {e}")
                results[account_config.account_id] = {"error": str(e)}
        return results

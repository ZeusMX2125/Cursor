"""Deep backtesting engine with ProjectX API integration."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

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


class DeepBacktester:
    """Deep backtesting with ProjectX API historical data."""

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

        Args:
            account_config: Account configuration with profile
            symbols: List of symbols to backtest
            timeframe: Bar timeframe (1m, 5m, 15m, 1h)
            start_date: Start date for backtest
            end_date: End date for backtest
            strategies: List of strategy names to test

        Returns:
            Dictionary with backtest results
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
            all_bars[symbol] = bars

            if bars.is_empty():
                logger.warning(f"No data for {symbol}")
                continue

            logger.info(f"Fetched {len(bars)} bars for {symbol}")

        # Generate signals for each strategy
        # (This would integrate with actual strategy implementations)
        signals = await self._generate_signals(all_bars, strategies, account_config)

        # Run backtest
        result = self.backtest_engine.run_backtest(
            bars=pl.concat(list(all_bars.values())),
            signals=signals,
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

        This is a simplified version - in production, this would
        use the actual strategy implementations.
        """
        signals = []

        # Import strategies dynamically
        from strategies.ict_silver_bullet import ICTSilverBulletStrategy
        from strategies.vwap_mean_reversion import VWAPMeanReversionStrategy
        from strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
        from strategies.trend_following import TrendFollowingStrategy

        # Default symbols
        symbols = ["MNQ", "MES", "MGC"]
        
        strategy_map = {
            "ict_silver_bullet": ICTSilverBulletStrategy(symbols),
            "vwap_mean_reversion": VWAPMeanReversionStrategy(symbols),
            "opening_range_breakout": OpeningRangeBreakoutStrategy(symbols),
            "trend_following": TrendFollowingStrategy(symbols),
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
                    signal = await strategy.analyze(symbol, symbol_bars)

                    if signal:
                        signal_dict = signal.to_dict()
                        signal_dict["timestamp"] = symbol_bars["timestamp"].tail(1).item()
                        signal_dict["quantity"] = 1  # Default quantity
                        signals.append(signal_dict)

                except Exception as e:
                    logger.error(
                        f"Error generating signal for {strategy_name} on {symbol}: {e}",
                        exc_info=True,
                    )

        return signals

    async def run_multi_account_backtest(
        self,
        account_configs: List[AccountConfig],
        symbols: List[str],
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Dict]:
        """
        Run backtests for multiple accounts.

        Returns:
            Dictionary mapping account_id to backtest results
        """
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
                logger.error(
                    f"Error backtesting {account_config.account_id}: {e}",
                    exc_info=True,
                )
                results[account_config.account_id] = {"error": str(e)}

        return results


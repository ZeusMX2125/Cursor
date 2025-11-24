"""Vectorized backtesting engine using polars."""

from datetime import datetime
from typing import Dict, List, Optional

import polars as pl
from loguru import logger

from config.settings import Settings


class BacktestResult:
    """Backtest results container."""

    def __init__(self):
        self.trades: List[Dict] = []
        self.total_pnl: float = 0.0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.max_drawdown: float = 0.0
        self.sharpe_ratio: float = 0.0
        self.profit_factor: float = 0.0
        self.win_rate: float = 0.0


class BacktestEngine:
    """Vectorized backtesting engine."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.slippage_per_contract = settings.backtest_slippage_per_contract
        self.commission_per_contract = settings.backtest_commission_per_contract

    def run_backtest(
        self,
        bars: pl.DataFrame,
        signals: List[Dict],
        initial_balance: float = 50000.0,
    ) -> BacktestResult:
        """
        Run a backtest on historical data.

        Args:
            bars: Historical OHLCV bars
            signals: List of trading signals
            initial_balance: Starting account balance

        Returns:
            BacktestResult with performance metrics
        """
        result = BacktestResult()
        current_balance = initial_balance
        equity_curve = [initial_balance]
        positions: List[Dict] = []

        # Tick values
        tick_values = {"MES": 5.0, "MNQ": 2.0, "MGC": 1.0}

        # Process signals in chronological order
        signals_sorted = sorted(signals, key=lambda s: s.get("timestamp", datetime.min))

        for signal in signals_sorted:
            symbol = signal.get("symbol", "")
            side = signal.get("side", "BUY")
            entry_price = signal.get("entry_price", 0.0)
            stop_loss = signal.get("stop_loss", 0.0)
            take_profit = signal.get("take_profit", 0.0)
            quantity = signal.get("quantity", 1)

            # Calculate entry with slippage
            if side == "BUY":
                fill_price = entry_price + (self.slippage_per_contract / tick_values.get(symbol, 1.0))
            else:
                fill_price = entry_price - (self.slippage_per_contract / tick_values.get(symbol, 1.0))

            # Calculate commission
            commission = self.commission_per_contract * quantity * 2  # Entry + exit

            # Check for stop loss or take profit
            # (Simplified - in reality, need to check each bar)
            exit_price = None
            exit_reason = None

            # Find exit bar (simplified logic)
            signal_time = signal.get("timestamp")
            if signal_time:
                future_bars = bars.filter(pl.col("timestamp") > signal_time)

                for _, bar in future_bars.iter_rows(named=True):
                    if side == "BUY":
                        if bar["low"] <= stop_loss:
                            exit_price = stop_loss
                            exit_reason = "STOP_LOSS"
                            break
                        elif bar["high"] >= take_profit:
                            exit_price = take_profit
                            exit_reason = "TAKE_PROFIT"
                            break
                    else:  # SELL
                        if bar["high"] >= stop_loss:
                            exit_price = stop_loss
                            exit_reason = "STOP_LOSS"
                            break
                        elif bar["low"] <= take_profit:
                            exit_price = take_profit
                            exit_reason = "TAKE_PROFIT"
                            break

            if exit_price:
                # Calculate P&L
                tick_value = tick_values.get(symbol, 1.0)
                price_diff = abs(exit_price - fill_price)

                if side == "BUY":
                    pnl = (exit_price - fill_price) * tick_value * quantity
                else:
                    pnl = (fill_price - exit_price) * tick_value * quantity

                pnl -= commission  # Subtract commission

                # Record trade
                trade = {
                    "symbol": symbol,
                    "side": side,
                    "entry_price": fill_price,
                    "exit_price": exit_price,
                    "quantity": quantity,
                    "pnl": pnl,
                    "exit_reason": exit_reason,
                }

                result.trades.append(trade)
                result.total_pnl += pnl
                result.total_trades += 1

                if pnl > 0:
                    result.winning_trades += 1
                else:
                    result.losing_trades += 1

                current_balance += pnl
                equity_curve.append(current_balance)

        # Calculate metrics
        result.win_rate = (
            result.winning_trades / result.total_trades
            if result.total_trades > 0
            else 0.0
        )

        gross_profit = sum(t["pnl"] for t in result.trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in result.trades if t["pnl"] < 0))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        # Calculate max drawdown
        if equity_curve:
            peak = equity_curve[0]
            max_dd = 0.0
            for balance in equity_curve:
                if balance > peak:
                    peak = balance
                dd = (peak - balance) / peak
                if dd > max_dd:
                    max_dd = dd
            result.max_drawdown = max_dd

        # Calculate Sharpe ratio (simplified)
        if len(equity_curve) > 1:
            returns = [
                (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                for i in range(1, len(equity_curve))
            ]
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = (
                    sum((r - avg_return) ** 2 for r in returns) / len(returns)
                ) ** 0.5
                result.sharpe_ratio = (
                    avg_return / std_return * (252 ** 0.5) if std_return > 0 else 0.0
                )

        return result


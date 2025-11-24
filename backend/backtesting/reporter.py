"""Backtest performance reporting."""

from typing import Dict

from backtesting.engine import BacktestResult


class BacktestReporter:
    """Generates performance reports from backtest results."""

    @staticmethod
    def generate_report(result: BacktestResult) -> Dict:
        """Generate a comprehensive performance report."""
        return {
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": result.win_rate,
            "total_pnl": result.total_pnl,
            "profit_factor": result.profit_factor,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "average_win": (
                sum(t["pnl"] for t in result.trades if t["pnl"] > 0)
                / result.winning_trades
                if result.winning_trades > 0
                else 0.0
            ),
            "average_loss": (
                abs(
                    sum(t["pnl"] for t in result.trades if t["pnl"] < 0)
                    / result.losing_trades
                )
                if result.losing_trades > 0
                else 0.0
            ),
        }

    @staticmethod
    def print_report(result: BacktestResult) -> None:
        """Print a formatted performance report."""
        report = BacktestReporter.generate_report(result)

        print("\n" + "=" * 50)
        print("BACKTEST PERFORMANCE REPORT")
        print("=" * 50)
        print(f"Total Trades: {report['total_trades']}")
        print(f"Winning Trades: {report['winning_trades']}")
        print(f"Losing Trades: {report['losing_trades']}")
        print(f"Win Rate: {report['win_rate']:.2%}")
        print(f"Total P&L: ${report['total_pnl']:.2f}")
        print(f"Profit Factor: {report['profit_factor']:.2f}")
        print(f"Max Drawdown: {report['max_drawdown']:.2%}")
        print(f"Sharpe Ratio: {report['sharpe_ratio']:.2f}")
        print(f"Average Win: ${report['average_win']:.2f}")
        print(f"Average Loss: ${report['average_loss']:.2f}")
        print("=" * 50 + "\n")


"""Performance tracking and metrics calculation."""

from datetime import datetime
from typing import Dict, List

from loguru import logger

from config.settings import Settings


class PerformanceTracker:
    """Tracks trading performance metrics."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.trades: List[Dict] = []
        self.daily_stats: Dict[str, Dict] = {}

    async def update(self) -> None:
        """Update performance metrics."""
        # This will be called periodically to update metrics
        pass

    def record_trade(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        pnl: float,
        strategy_name: str,
    ) -> None:
        """Record a completed trade."""
        trade = {
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "pnl": pnl,
            "strategy_name": strategy_name,
            "timestamp": datetime.now(),
        }

        self.trades.append(trade)

        # Update daily stats
        today = datetime.now().date().isoformat()
        if today not in self.daily_stats:
            self.daily_stats[today] = {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
            }

        stats = self.daily_stats[today]
        stats["trades"] += 1
        stats["total_pnl"] += pnl

        if pnl > 0:
            stats["wins"] += 1
        else:
            stats["losses"] += 1

    def get_win_rate(self, period_days: int = 30) -> float:
        """Calculate win rate over a period."""
        if not self.trades:
            return 0.0

        recent_trades = self.trades[-period_days:] if len(self.trades) > period_days else self.trades
        wins = sum(1 for t in recent_trades if t["pnl"] > 0)
        total = len(recent_trades)

        return wins / total if total > 0 else 0.0

    def get_profit_factor(self, period_days: int = 30) -> float:
        """Calculate profit factor over a period."""
        if not self.trades:
            return 0.0

        recent_trades = self.trades[-period_days:] if len(self.trades) > period_days else self.trades

        gross_profit = sum(t["pnl"] for t in recent_trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in recent_trades if t["pnl"] < 0))

        return gross_profit / gross_loss if gross_loss > 0 else 0.0

    def get_daily_pnl(self) -> float:
        """Get today's P&L."""
        today = datetime.now().date().isoformat()
        return self.daily_stats.get(today, {}).get("total_pnl", 0.0)

    def get_trades_today(self) -> int:
        """Get number of trades today."""
        today = datetime.now().date().isoformat()
        return self.daily_stats.get(today, {}).get("trades", 0)

    def get_metrics(self) -> Dict:
        """Get all performance metrics."""
        return {
            "win_rate": self.get_win_rate(),
            "profit_factor": self.get_profit_factor(),
            "daily_pnl": self.get_daily_pnl(),
            "trades_today": self.get_trades_today(),
            "total_trades": len(self.trades),
        }


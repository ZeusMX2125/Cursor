"""Topstep rule simulator for backtesting."""

from typing import Dict, List, Optional

from loguru import logger

from config.settings import Settings
from accounts.models import AccountProfile


class TopstepSimulator:
    """Simulates Topstep rules in backtesting."""

    def __init__(self, settings: Settings, profile: Optional[AccountProfile] = None):
        self.settings = settings
        if profile:
            self.daily_loss_limit = profile.daily_loss_limit
            self.max_drawdown_limit = profile.max_drawdown_limit
            self.consistency_threshold = profile.consistency_threshold
        else:
            self.daily_loss_limit = settings.daily_loss_limit
            self.max_drawdown_limit = settings.max_drawdown_limit
            self.consistency_threshold = settings.consistency_threshold

    def check_daily_loss_limit(
        self, daily_pnl: float, trades_today: List[Dict]
    ) -> tuple[bool, str]:
        """
        Check if daily loss limit would be violated.

        Returns:
            (would_violate, message)
        """
        if abs(daily_pnl) >= self.daily_loss_limit * 0.95:
            return True, f"Daily loss limit would be violated: ${abs(daily_pnl):.2f}"

        return False, ""

    def check_trailing_drawdown(
        self, current_balance: float, high_water_mark: float
    ) -> tuple[bool, str]:
        """
        Check if trailing max drawdown would be violated.

        Returns:
            (would_violate, message)
        """
        max_allowed_loss = high_water_mark - self.max_drawdown_limit
        distance_to_limit = current_balance - max_allowed_loss

        if distance_to_limit <= 0:
            return True, f"Trailing drawdown would be violated: ${distance_to_limit:.2f}"

        return False, ""

    def check_consistency_rule(
        self, best_day_profit: float, total_profit: float
    ) -> tuple[bool, str]:
        """
        Check if consistency rule would be violated.

        Returns:
            (would_violate, message)
        """
        if total_profit <= 0:
            return False, ""

        consistency_ratio = best_day_profit / total_profit

        if consistency_ratio > self.consistency_threshold:
            return (
                True,
                f"Consistency rule would be violated: {consistency_ratio:.2%}",
            )

        return False, ""

    def simulate_trading_day(
        self, trades: List[Dict], initial_balance: float
    ) -> Dict:
        """
        Simulate a trading day with Topstep rules.

        Returns:
            Dictionary with simulation results
        """
        daily_pnl = sum(t.get("pnl", 0.0) for t in trades)
        current_balance = initial_balance + daily_pnl

        # Check rules
        daily_violation, daily_msg = self.check_daily_loss_limit(daily_pnl, trades)
        drawdown_violation, drawdown_msg = self.check_trailing_drawdown(
            current_balance, initial_balance
        )

        return {
            "daily_pnl": daily_pnl,
            "current_balance": current_balance,
            "daily_violation": daily_violation,
            "daily_violation_msg": daily_msg,
            "drawdown_violation": drawdown_violation,
            "drawdown_violation_msg": drawdown_msg,
            "trades_count": len(trades),
        }


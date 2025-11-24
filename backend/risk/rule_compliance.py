"""Topstep rule compliance checker."""

from datetime import datetime, time
from typing import Dict

import pytz
from loguru import logger


class RuleCompliance:
    """Checks compliance with Topstep trading rules."""

    def __init__(self, settings):
        self.settings = settings
        self.ct_tz = pytz.timezone(settings.timezone)

    def check_daily_loss_limit(
        self, daily_pnl: float, daily_loss_limit: float
    ) -> tuple[bool, str]:
        """
        Check if daily loss limit is being approached.

        Returns:
            (is_violated, message)
        """
        if abs(daily_pnl) >= daily_loss_limit * 0.95:
            return True, f"Daily loss limit approaching: ${abs(daily_pnl):.2f}"

        return False, ""

    def check_trailing_drawdown(
        self, current_balance: float, high_water_mark: float, max_drawdown: float
    ) -> tuple[bool, str]:
        """
        Check if trailing max drawdown is being approached.

        Returns:
            (is_violated, message)
        """
        max_allowed_loss = high_water_mark - max_drawdown
        distance_to_limit = current_balance - max_allowed_loss

        if distance_to_limit <= max_drawdown * 0.05:  # 5% buffer
            return True, f"Trailing drawdown approaching: ${distance_to_limit:.2f} remaining"

        return False, ""

    def check_consistency_rule(
        self, best_day_profit: float, total_profit: float
    ) -> tuple[bool, str]:
        """
        Check consistency rule (best day < 50% of total profit).

        Returns:
            (is_violated, message)
        """
        if total_profit <= 0:
            return False, ""

        consistency_ratio = best_day_profit / total_profit

        if consistency_ratio > 0.45:  # 45% threshold (approaching 50%)
            return True, f"Consistency rule approaching: {consistency_ratio:.2%}"

        return False, ""

    def check_time_restriction(self) -> tuple[bool, str]:
        """
        Check if current time allows trading.

        Returns:
            (is_violated, message)
        """
        now = datetime.now(self.ct_tz)
        current_time = now.time()

        # Hard close at 3:05 PM CT
        if current_time >= time(15, 5):
            return True, "Market closed - hard close time (3:05 PM CT)"

        # No new trades after 2:45 PM CT
        if now.hour == 14 and now.minute >= 45:
            return True, "No new trades allowed after 2:45 PM CT"

        # Check trading hours (5:00 PM CT to 3:10 PM CT)
        if not (now.hour >= 17 or now.hour < 15 or (now.hour == 15 and now.minute <= 10)):
            return True, "Outside trading hours"

        return False, ""

    def check_scaling_plan(
        self, balance: float, position_size: int, scaling_plan: Optional[Dict] = None
    ) -> tuple[bool, str]:
        """
        Check if position size complies with scaling plan.

        Args:
            balance: Current account balance
            position_size: Proposed position size
            scaling_plan: Optional scaling plan dict (from AccountProfile)

        Returns:
            (is_violated, message)
        """
        if scaling_plan:
            # Use provided scaling plan
            max_contracts = self._get_max_contracts_from_plan(balance, scaling_plan)
        else:
            # Default $50K Combine scaling plan
            if balance < 1500:
                max_contracts = 2
            elif balance < 3000:
                max_contracts = 3
            elif balance < 5000:
                max_contracts = 4
            else:
                max_contracts = 5

        if position_size > max_contracts:
            return True, f"Position size {position_size} exceeds scaling plan limit {max_contracts}"

        return False, ""

    def _get_max_contracts_from_plan(self, balance: float, scaling_plan: Dict) -> int:
        """Get max contracts from scaling plan."""
        for threshold_range, max_contracts in scaling_plan.items():
            if "-" in threshold_range:
                parts = threshold_range.split("-")
                min_val = float(parts[0])
                max_val = float(parts[1])
                if min_val <= balance < max_val:
                    return max_contracts
            elif threshold_range.endswith("+"):
                min_val = float(threshold_range.replace("+", ""))
                if balance >= min_val:
                    return max_contracts

        return min(scaling_plan.values()) if scaling_plan else 2

    def validate_trade(self, trade_data: Dict) -> tuple[bool, str]:
        """
        Validate a trade against all rules.

        Returns:
            (is_valid, message)
        """
        # Check time restriction
        is_violated, message = self.check_time_restriction()
        if is_violated:
            return False, message

        # Check scaling plan
        balance = trade_data.get("account_balance", 0)
        position_size = trade_data.get("position_size", 0)
        is_violated, message = self.check_scaling_plan(balance, position_size)
        if is_violated:
            return False, message

        return True, "Trade validated"


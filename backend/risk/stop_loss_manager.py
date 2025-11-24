"""Stop loss and take profit management."""

from typing import Dict, Optional

from loguru import logger


class StopLossManager:
    """Manages stop loss and take profit orders."""

    @staticmethod
    def calculate_atr_stop(
        entry_price: float,
        atr: float,
        side: str,
        multiplier: float = 1.5,
    ) -> float:
        """
        Calculate stop loss based on ATR.

        Args:
            entry_price: Entry price
            atr: Average True Range value
            side: "BUY" or "SELL"
            multiplier: ATR multiplier (default 1.5)

        Returns:
            Stop loss price
        """
        stop_distance = atr * multiplier

        if side == "BUY":
            return entry_price - stop_distance
        else:  # SELL
            return entry_price + stop_distance

    @staticmethod
    def calculate_trailing_stop(
        current_price: float,
        highest_price: float,
        lowest_price: float,
        side: str,
        atr: float,
        multiplier: float = 1.0,
    ) -> float:
        """
        Calculate trailing stop loss.

        Args:
            current_price: Current market price
            highest_price: Highest price since entry (for longs)
            lowest_price: Lowest price since entry (for shorts)
            side: "LONG" or "SHORT"
            atr: Average True Range value
            multiplier: ATR multiplier

        Returns:
            Trailing stop price
        """
        trailing_distance = atr * multiplier

        if side == "LONG":
            return highest_price - trailing_distance
        else:  # SHORT
            return lowest_price + trailing_distance

    @staticmethod
    def calculate_take_profit(
        entry_price: float,
        stop_loss: float,
        side: str,
        risk_reward_ratio: float = 2.0,
    ) -> float:
        """
        Calculate take profit based on risk/reward ratio.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: "BUY" or "SELL"
            risk_reward_ratio: Desired R:R ratio (default 2.0)

        Returns:
            Take profit price
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * risk_reward_ratio

        if side == "BUY":
            return entry_price + reward
        else:  # SELL
            return entry_price - reward

    @staticmethod
    def should_trail_stop(
        current_price: float,
        entry_price: float,
        stop_loss: float,
        side: str,
        profit_threshold: float = 1.5,
    ) -> bool:
        """
        Determine if stop should be trailed.

        Args:
            current_price: Current market price
            entry_price: Entry price
            stop_loss: Current stop loss
            side: "BUY" or "SELL"
            profit_threshold: Profit threshold in R multiples (default 1.5)

        Returns:
            True if stop should be trailed
        """
        risk = abs(entry_price - stop_loss)

        if side == "BUY":
            profit = current_price - entry_price
        else:  # SELL
            profit = entry_price - current_price

        r_multiple = profit / risk if risk > 0 else 0

        return r_multiple >= profit_threshold


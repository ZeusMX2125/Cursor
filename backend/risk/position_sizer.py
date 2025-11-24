"""Position sizing algorithms (Kelly Criterion, Fixed Fractional)."""

from typing import Dict

from loguru import logger


class PositionSizer:
    """Calculates optimal position sizes using various methods."""

    @staticmethod
    def kelly_criterion(
        win_rate: float, avg_win: float, avg_loss: float
    ) -> float:
        """
        Calculate Kelly Criterion percentage.

        Args:
            win_rate: Win rate (0.0 to 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)

        Returns:
            Kelly percentage (0.0 to 1.0)
        """
        if avg_loss == 0:
            return 0.0

        win_loss_ratio = avg_win / avg_loss
        kelly = (win_rate * (win_loss_ratio + 1) - 1) / win_loss_ratio

        # Cap at 25% for safety (quarter Kelly)
        return min(max(kelly, 0.0), 0.25)

    @staticmethod
    def fixed_fractional(
        account_balance: float, risk_percent: float, risk_amount: float
    ) -> int:
        """
        Calculate position size using fixed fractional method.

        Args:
            account_balance: Current account balance
            risk_percent: Risk percentage per trade (e.g., 0.015 for 1.5%)
            risk_amount: Dollar amount at risk per contract

        Returns:
            Number of contracts
        """
        if risk_amount <= 0:
            return 0

        risk_dollars = account_balance * risk_percent
        contracts = int(risk_dollars / risk_amount)

        return max(contracts, 1)  # Minimum 1 contract

    @staticmethod
    def calculate_from_signal(
        signal: Dict, account_balance: float, risk_percent: float = 0.015
    ) -> int:
        """
        Calculate position size from a trading signal.

        Args:
            signal: Trading signal dictionary
            account_balance: Current account balance
            risk_percent: Risk percentage per trade (default 1.5%)

        Returns:
            Number of contracts
        """
        entry_price = signal.get("entry_price", 0)
        stop_loss = signal.get("stop_loss", 0)
        symbol = signal.get("symbol", "")

        if entry_price == 0 or stop_loss == 0:
            return 0

        # Get tick value
        tick_values = {
            "MES": 5.0,
            "MNQ": 2.0,
            "MGC": 1.0,
        }
        tick_value = tick_values.get(symbol, 1.0)

        # Calculate stop distance in ticks
        stop_distance = abs(entry_price - stop_loss)
        risk_per_contract = stop_distance * tick_value

        if risk_per_contract == 0:
            return 0

        # Use fixed fractional
        return PositionSizer.fixed_fractional(
            account_balance, risk_percent, risk_per_contract
        )


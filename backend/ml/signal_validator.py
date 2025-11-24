"""ML-based signal validator using XGBoost."""

from typing import Dict, Optional

import numpy as np
from loguru import logger

from ml.feature_engineering import FeatureEngineer


class SignalValidator:
    """Validates trading signals using ML model."""

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path
        self.feature_engineer = FeatureEngineer()

    def load_model(self) -> None:
        """Load trained XGBoost model."""
        # TODO: Implement model loading
        # For now, return True for all signals (no ML filtering)
        logger.info("Signal validator initialized (no model loaded)")

    def validate_signal(
        self, signal: Dict, market_features: Dict
    ) -> tuple[bool, float]:
        """
        Validate a trading signal using ML model.

        Returns:
            (is_valid, confidence_score)
        """
        if self.model is None:
            # No model loaded, accept all signals
            return True, signal.get("confidence", 0.5)

        try:
            # Extract features
            features = self._prepare_features(signal, market_features)

            # Predict
            prediction = self.model.predict_proba([features])[0]
            confidence = float(prediction[1])  # Probability of profitable trade

            # Accept if confidence > 0.6
            is_valid = confidence > 0.6

            return is_valid, confidence

        except Exception as e:
            logger.error(f"Error validating signal: {e}", exc_info=True)
            return True, 0.5  # Default to accepting if error

    def _prepare_features(self, signal: Dict, market_features: Dict) -> list:
        """Prepare features for model input."""
        # Combine signal and market features
        features = [
            market_features.get("current_price", 0),
            market_features.get("sma_10", 0),
            market_features.get("sma_20", 0),
            market_features.get("sma_50", 0),
            market_features.get("rsi_14", 50),
            market_features.get("macd", 0),
            signal.get("entry_price", 0),
            signal.get("stop_loss", 0),
            signal.get("take_profit", 0),
        ]

        return features


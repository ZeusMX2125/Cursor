"""ML-based signal validator using XGBoost/LightGBM."""

from typing import Dict, Optional, Any
import os
import joblib
import numpy as np
from loguru import logger

from ml.feature_engineering import FeatureEngineer

class SignalValidator:
    """Validates trading signals using ML model."""

    def __init__(self, model_path: Optional[str] = "models/signal_validator.pkl"):
        self.model = None
        self.model_path = model_path
        self.feature_names = None
        self.feature_engineer = FeatureEngineer()

    def load_model(self) -> None:
        """Load trained ML model."""
        if not self.model_path or not os.path.exists(self.model_path):
            logger.info("No trained model found. Signal validator running in pass-through mode.")
            return

        try:
            loaded_data = joblib.load(self.model_path)
            if isinstance(loaded_data, dict):
                self.model = loaded_data.get("model")
                self.feature_names = loaded_data.get("feature_names")
            else:
                self.model = loaded_data
                
            logger.info(f"Signal validator model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)

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
            # Ensure features are in 2D array [samples, features]
            features_array = np.array(features).reshape(1, -1)
            
            if hasattr(self.model, "predict_proba"):
                prediction = self.model.predict_proba(features_array)[0]
                confidence = float(prediction[1])  # Probability of class 1 (profitable)
            else:
                # Fallback for models without probability
                prediction = self.model.predict(features_array)[0]
                confidence = 0.8 if prediction == 1 else 0.2

            # Threshold for acceptance
            # TODO: Make threshold configurable via Settings
            is_valid = confidence > 0.6

            return is_valid, confidence

        except Exception as e:
            logger.error(f"Error validating signal: {e}", exc_info=True)
            return True, 0.5  # Default to accepting if error

    def _prepare_features(self, signal: Dict, market_features: Dict) -> list:
        """
        Prepare features for model input.
        Must match the features used during training.
        """
        # Combine signal and market features
        # Note: Order matters! Must align with training.
        
        # 1. Market Features (from FeatureEngineer)
        # We rely on feature_names if available, otherwise assume fixed order
        
        # Default features list if metadata missing
        default_features = [
            "current_price", 
            "sma_10_dist", "sma_20_dist", "sma_50_dist", "sma_200_dist",
            "rsi_14", "macd", "macd_signal", "macd_hist",
            "atr_14", "bb_width", "bb_percent_b",
            "vwap_dist", "obv", "volume_ratio",
            "body_size_norm", "upper_shadow_norm", "lower_shadow_norm"
        ]
        
        feature_keys = self.feature_names if self.feature_names else default_features
        
        # Build feature vector
        vector = []
        for key in feature_keys:
            if key in market_features:
                vector.append(market_features[key])
            elif key == "side":
                # Encode side: BUY=1, SELL=-1
                side = signal.get("side", "BUY").upper()
                vector.append(1.0 if side == "BUY" else -1.0)
            elif key == "entry_dist":
                # Distance from current price to entry (limit orders)
                cp = market_features.get("current_price", 0)
                ep = signal.get("entry_price", cp)
                vector.append((cp - ep) / (cp + 1e-9))
            else:
                # Signal-specific features or fallback
                # e.g., stop_loss_dist, take_profit_dist relative to entry
                if key == "sl_dist":
                    ep = signal.get("entry_price", 0)
                    sl = signal.get("stop_loss", 0)
                    vector.append(abs(ep - sl) / (ep + 1e-9))
                elif key == "tp_dist":
                    ep = signal.get("entry_price", 0)
                    tp = signal.get("take_profit", 0)
                    vector.append(abs(ep - tp) / (ep + 1e-9))
                else:
                    vector.append(0.0)
        
        return vector

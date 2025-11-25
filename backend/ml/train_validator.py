"""Training pipeline for Signal Validator model."""

import pandas as pd
import numpy as np
import joblib
import os
from typing import List, Dict
from loguru import logger
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
import xgboost as xgb

from ml.feature_engineering import FeatureEngineer

class SignalValidatorTrainer:
    """Trains the Signal Validator XGBoost model."""

    def __init__(self, data_path: str = "data/historical/trades.csv", model_output: str = "models/signal_validator.pkl"):
        self.data_path = data_path
        self.model_output = model_output
        self.feature_engineer = FeatureEngineer()

    def load_data(self) -> pd.DataFrame:
        """Load and preprocess historical trade data."""
        # Check if data exists
        if not os.path.exists(self.data_path):
            logger.warning(f"Data file {self.data_path} not found. Creating dummy data for structure validation.")
            return self._create_dummy_data()
            
        df = pd.read_csv(self.data_path)
        return df

    def _create_dummy_data(self) -> pd.DataFrame:
        """Create dummy data for testing the pipeline."""
        # Create synthetic data resembling market features + labels
        n_samples = 100
        data = {
            "current_price": np.random.uniform(4000, 5000, n_samples),
            "sma_10_dist": np.random.normal(0, 0.01, n_samples),
            "sma_20_dist": np.random.normal(0, 0.02, n_samples),
            "rsi_14": np.random.uniform(30, 70, n_samples),
            "macd": np.random.normal(0, 5, n_samples),
            "atr_14": np.random.uniform(10, 50, n_samples),
            "volume_ratio": np.random.uniform(0.5, 2.0, n_samples),
            "side": np.random.choice(["BUY", "SELL"], n_samples),
            "profitable": np.random.choice([0, 1], n_samples)  # Target
        }
        return pd.DataFrame(data)

    def train(self):
        """Train the model."""
        logger.info("Starting model training...")
        
        df = self.load_data()
        
        # Define features and target
        # Simplified feature set for the example
        feature_cols = [col for col in df.columns if col not in ["profitable", "timestamp", "trade_id"]]
        target_col = "profitable"

        X = df[feature_cols]
        # Encode categorical 'side' if present
        if "side" in X.columns:
             X["side"] = X["side"].apply(lambda x: 1 if x == "BUY" else -1)
             
        y = df[target_col]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Initialize XGBoost Classifier
        model = xgb.XGBClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            objective="binary:logistic",
            eval_metric="logloss",
            use_label_encoder=False
        )

        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        logger.info(f"Model Accuracy: {acc:.4f}")

        # Save model and feature names
        os.makedirs(os.path.dirname(self.model_output), exist_ok=True)
        
        model_data = {
            "model": model,
            "feature_names": feature_cols
        }
        
        joblib.dump(model_data, self.model_output)
        logger.info(f"Model saved to {self.model_output}")

if __name__ == "__main__":
    trainer = SignalValidatorTrainer()
    trainer.train()

